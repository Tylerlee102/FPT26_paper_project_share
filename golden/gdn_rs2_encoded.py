"""Encoded-integer oracle for the two-term native-MXFP4 write-log GDN."""

from __future__ import annotations

import numpy as np

from .gdn_e2m0_encoded import (
    COEFFICIENT_ONE,
    EncodedE2M0StepResult,
    EncodedE2M0Token,
    EncodedE2M0WriteLogGDN,
    EncodedMXFP4Stack,
    _decode_stack_integer,
    _quantize_stack_exact,
    _stack_from_float,
    _validate_stack,
    decode_stack,
    encode_e2m0_token,
)
from .gdn_mxfp4_encoded import E8M0_BIAS, ArithmeticCounters


EncodedRS2State = EncodedMXFP4Stack
EncodedRS2Token = EncodedE2M0Token
EncodedRS2StepResult = EncodedE2M0StepResult


def encode_rs2_state(values: object, *, block_size: int) -> EncodedRS2State:
    source = np.asarray(values, dtype=np.float32)
    if source.ndim != 3 or not np.all(np.isfinite(source)):
        raise ValueError("state must be a finite [value_heads,key_dim,value_dim] array")
    return _stack_from_float(source, block_size=block_size, depth=2)


def decode_rs2_state(state: EncodedRS2State) -> np.ndarray:
    return decode_stack(state)


def encode_rs2_token(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    *,
    block_size: int,
) -> EncodedRS2Token:
    return encode_e2m0_token(
        q,
        k,
        v,
        alpha,
        beta,
        block_size=block_size,
    )


class EncodedRS2WriteLogGDN(EncodedE2M0WriteLogGDN):
    """Fixed-capacity encoded GDN with two E2M1 terms everywhere."""

    def __init__(
        self,
        initial_state: EncodedRS2State,
        *,
        num_qk_heads: int,
        capacity: int = 2,
    ) -> None:
        elements, scales = _validate_stack("state", initial_state)
        if elements.ndim != 4 or elements.shape[0] != 2:
            raise ValueError(
                "state must contain two [value_heads,key_dim,value_dim] terms"
            )
        self.num_value_heads, self.key_dim, self.value_dim = elements.shape[1:]
        if num_qk_heads <= 0 or self.num_value_heads % num_qk_heads:
            raise ValueError("value heads must be divisible by q/k heads")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.num_qk_heads = num_qk_heads
        self.heads_per_qk = self.num_value_heads // num_qk_heads
        self.capacity = capacity
        self.block_size = initial_state.block_size
        self.base = EncodedMXFP4Stack(
            elements.copy(), scales.copy(), self.block_size
        )
        blocks_k = (self.key_dim + self.block_size - 1) // self.block_size
        blocks_v = (self.value_dim + self.block_size - 1) // self.block_size
        self.key_elements = np.zeros(
            (capacity, 2, num_qk_heads, self.key_dim), dtype=np.uint8
        )
        self.key_scales = np.full(
            (capacity, 2, num_qk_heads, blocks_k), E8M0_BIAS, dtype=np.uint8
        )
        self.update_elements = np.zeros(
            (capacity, 2, self.num_value_heads, self.value_dim), dtype=np.uint8
        )
        self.update_scales = np.full(
            (capacity, 2, self.num_value_heads, blocks_v),
            E8M0_BIAS,
            dtype=np.uint8,
        )
        self.gamma_codes = np.full(
            self.num_value_heads, COEFFICIENT_ONE, dtype=np.uint16
        )
        self.lambda_codes = np.zeros(
            (capacity, self.num_value_heads), dtype=np.uint16
        )
        self.live_entries = 0

    def _decode_base(self) -> tuple[np.ndarray, np.ndarray]:
        return _decode_stack_integer("state", self.base)

    def _new_counters(self) -> ArithmeticCounters:
        return ArithmeticCounters()

    def _quantize_base_exact(
        self,
        mantissas: np.ndarray,
        exponents: np.ndarray,
        counters: ArithmeticCounters,
    ) -> EncodedRS2State:
        return _quantize_stack_exact(
            mantissas,
            exponents,
            block_size=self.block_size,
            counters=counters,
        )

    def _base_scale_change_count(self, replacement: EncodedRS2State) -> int:
        return int(np.count_nonzero(replacement.scales != self.base.scales))

    def materialize_state_fp32(self) -> np.ndarray:
        state = decode_stack(self.base) * (
            self.gamma_codes.astype(np.float32) / np.float32(COEFFICIENT_ONE)
        )[:, np.newaxis, np.newaxis]
        for entry in range(self.live_entries):
            key = decode_stack(
                EncodedMXFP4Stack(
                    self.key_elements[entry],
                    self.key_scales[entry],
                    self.block_size,
                )
            )
            update = decode_stack(
                EncodedMXFP4Stack(
                    self.update_elements[entry],
                    self.update_scales[entry],
                    self.block_size,
                )
            )
            keys_per_head = np.repeat(key, self.heads_per_qk, axis=0)
            coefficient = self.lambda_codes[entry].astype(np.float32) / np.float32(
                COEFFICIENT_ONE
            )
            state = (
                state
                + coefficient[:, np.newaxis, np.newaxis]
                * keys_per_head[:, :, np.newaxis]
                * update[:, np.newaxis, :]
            ).astype(np.float32)
        return np.asarray(state, dtype=np.float32)

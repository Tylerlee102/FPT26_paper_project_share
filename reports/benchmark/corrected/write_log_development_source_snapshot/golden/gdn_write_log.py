"""Lazy MXFP4 base with a bounded higher-precision rank-one write log.

The official recurrence is

    S_t = alpha_t S_(t-1) + k_t u_t^T,
    u_t = beta_t (v_t - k_t^T alpha_t S_(t-1)).

Therefore a log using the stated definition of ``u`` must add, rather than
subtract, its rank-one writes. Exact mode is used to prove equivalence before
any quantization is introduced. Quantized mode keeps an MXFP4 base, MXFP4
token inputs, and a configurable higher-precision log.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

from .gdn_fp32 import L2_EPS, normalize_qk
from .gdn_mxfp4 import quantize_activation, quantize_state
from .gdn_mxfp4_encoded import decode_q1_15, encode_q1_15


Array = np.ndarray
VALID_MODES = {"exact", "mxfp4"}
VALID_LOG_PRECISIONS = {"fp32", "bf16", "fp16", "mxfp8_e4m3"}
VALID_FOLD_POLICIES = {"fixed", "decay_threshold"}


@dataclass(frozen=True)
class WriteLogConfiguration:
    capacity: int
    mode: str = "mxfp4"
    activation_block_size: int = 32
    base_block_size: int = 32
    log_block_size: int = 32
    log_precision: str = "mxfp8_e4m3"
    activation_stack_depth: int = 1
    base_stack_depth: int = 1
    fold_policy: str = "fixed"
    adaptive_min_entries: int = 1
    fold_decay_threshold: float = 0.85

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("write-log capacity must be positive")
        if self.mode not in VALID_MODES:
            raise ValueError(f"unknown write-log mode: {self.mode}")
        if self.log_precision not in VALID_LOG_PRECISIONS:
            raise ValueError(f"unknown log precision: {self.log_precision}")
        for name, value in (
            ("activation_block_size", self.activation_block_size),
            ("base_block_size", self.base_block_size),
            ("log_block_size", self.log_block_size),
        ):
            if value not in (16, 32):
                raise ValueError(f"{name} must be 16 or 32")
        if self.activation_stack_depth <= 0 or self.base_stack_depth <= 0:
            raise ValueError("residual-stack depths must be positive")
        if self.fold_policy not in VALID_FOLD_POLICIES:
            raise ValueError(f"unknown fold policy: {self.fold_policy}")
        if not 1 <= self.adaptive_min_entries <= self.capacity:
            raise ValueError("adaptive_min_entries must be in 1..capacity")
        if not 0.0 <= self.fold_decay_threshold <= 1.0:
            raise ValueError("fold_decay_threshold must be in [0, 1]")


@dataclass
class WriteLogCounters:
    appended_entries: int = 0
    folds: int = 0
    coefficient_rebases: int = 0
    dropped_entries: int = 0
    max_live_entries: int = 0


def roundtrip_bf16(values: object) -> Array:
    """Round finite values to BF16 with round-to-nearest-even."""

    array = np.asarray(values, dtype=np.float32)
    if not np.all(np.isfinite(array)):
        raise ValueError("BF16 values must be finite")
    bits = array.view(np.uint32)
    rounded = bits + np.uint32(0x7FFF) + ((bits >> np.uint32(16)) & np.uint32(1))
    return (rounded & np.uint32(0xFFFF0000)).view(np.float32)


def _as_finite(name: str, values: object, dtype: np.dtype) -> Array:
    array = np.asarray(values, dtype=dtype)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains NaN or Inf")
    return array


def _normalize_qk_fp64(q: object, k: object, eps: float) -> Tuple[Array, Array]:
    q_array = _as_finite("q", q, np.dtype(np.float64))
    k_array = _as_finite("k", k, np.dtype(np.float64))
    if q_array.ndim != 2 or k_array.shape != q_array.shape:
        raise ValueError("q and k must have matching [qk_heads, key_dim] shapes")
    if not np.isfinite(eps) or eps <= 0.0:
        raise ValueError("eps must be finite and positive")
    q_norm = np.sqrt(np.sum(q_array * q_array, axis=-1, keepdims=True) + eps)
    k_norm = np.sqrt(np.sum(k_array * k_array, axis=-1, keepdims=True) + eps)
    query_scale = 1.0 / np.sqrt(float(q_array.shape[-1]))
    return q_array / q_norm * query_scale, k_array / k_norm


def _quantize_log(values: Array, config: WriteLogConfiguration) -> Array:
    if config.mode == "exact" or config.log_precision == "fp32":
        return np.asarray(values, dtype=np.float64 if config.mode == "exact" else np.float32)
    if config.log_precision == "bf16":
        return roundtrip_bf16(values)
    if config.log_precision == "fp16":
        return np.asarray(values, dtype=np.float16).astype(np.float32)
    return quantize_state(
        values,
        block_size=config.log_block_size,
        precision="mxfp8_e4m3",
    )


def quantize_mxfp4_stack(
    values: object,
    *,
    block_size: int,
    depth: int,
) -> Array:
    """Reconstruct values as a sum of independently scaled MXFP4 blocks."""

    if depth <= 0:
        raise ValueError("residual-stack depth must be positive")
    source = _as_finite("values", values, np.dtype(np.float32))
    reconstruction = np.zeros_like(source)
    residual = source.copy()
    for _ in range(depth):
        term = quantize_activation(residual, block_size=block_size)
        reconstruction = (reconstruction + term).astype(np.float32)
        residual = (source - reconstruction).astype(np.float32)
    return reconstruction


class LazyWriteLogGDN:
    """Stateful recurrence core with an atomic bounded write log.

    Fixed-capacity operation folds every live entry after the token that fills
    the log. The current output is evaluated before that fold, matching the
    existing recurrence boundary where output precedes resident-state
    requantization. A fold commits only after the complete replacement base has
    been formed and quantized.
    """

    def __init__(
        self,
        initial_state: object,
        *,
        num_qk_heads: int,
        config: WriteLogConfiguration,
    ) -> None:
        self.config = config
        dtype = np.dtype(np.float64 if config.mode == "exact" else np.float32)
        state = _as_finite("initial_state", initial_state, dtype)
        if state.ndim != 3:
            raise ValueError("initial_state must have shape [value_heads, key_dim, value_dim]")
        self.num_value_heads, self.key_dim, self.value_dim = state.shape
        if num_qk_heads <= 0 or self.num_value_heads % num_qk_heads != 0:
            raise ValueError("value heads must be divisible by positive qk heads")
        self.num_qk_heads = num_qk_heads
        self.heads_per_qk = self.num_value_heads // num_qk_heads
        self.dtype = dtype

        self.base = (
            state.copy()
            if config.mode == "exact"
            else quantize_mxfp4_stack(
                state,
                block_size=config.base_block_size,
                depth=config.base_stack_depth,
            )
        )
        self.gamma = np.ones(self.num_value_heads, dtype=dtype)
        self.keys = np.zeros(
            (config.capacity, num_qk_heads, self.key_dim), dtype=dtype
        )
        self.updates = np.zeros(
            (config.capacity, self.num_value_heads, self.value_dim), dtype=dtype
        )
        self.lambdas = np.zeros(
            (config.capacity, self.num_value_heads), dtype=dtype
        )
        self.live_entries = 0
        self.counters = WriteLogCounters()

    def _validate_core_inputs(
        self,
        q_scaled: object,
        k_normalized: object,
        v: object,
        alpha: object,
        beta: object,
    ) -> tuple[Array, Array, Array, Array, Array]:
        q_array = _as_finite("q_scaled", q_scaled, self.dtype)
        k_array = _as_finite("k_normalized", k_normalized, self.dtype)
        v_array = _as_finite("v", v, self.dtype)
        alpha_array = _as_finite("alpha", alpha, self.dtype)
        beta_array = _as_finite("beta", beta, self.dtype)
        expected_qk = (self.num_qk_heads, self.key_dim)
        if q_array.shape != expected_qk or k_array.shape != expected_qk:
            raise ValueError(f"q_scaled and k_normalized must have shape {expected_qk}")
        if v_array.shape != (self.num_value_heads, self.value_dim):
            raise ValueError("v has the wrong shape")
        if alpha_array.shape != (self.num_value_heads,) or beta_array.shape != (
            self.num_value_heads,
        ):
            raise ValueError("alpha and beta have the wrong shape")
        if np.any(alpha_array < 0) or np.any(alpha_array > 1):
            raise ValueError("alpha must be in [0, 1]")
        if np.any(beta_array < 0) or np.any(beta_array > 1):
            raise ValueError("beta must be in [0, 1]")
        return q_array, k_array, v_array, alpha_array, beta_array

    def _per_value_head(self, qk_values: Array) -> Array:
        return np.repeat(qk_values, self.heads_per_qk, axis=0)

    def _left_action(self, vectors: Array) -> Array:
        per_head = self._per_value_head(vectors)
        result = np.einsum("hk,hkv->hv", per_head, self.base)
        result = result * self.gamma[:, None]
        if self.live_entries:
            key_dots = np.einsum(
                "qk,iqk->iq", vectors, self.keys[: self.live_entries]
            )
            dots_per_head = np.repeat(key_dots, self.heads_per_qk, axis=1)
            result = result + np.einsum(
                "ih,ih,ihv->hv",
                dots_per_head,
                self.lambdas[: self.live_entries],
                self.updates[: self.live_entries],
            )
        return np.asarray(result, dtype=self.dtype)

    def materialize_state(self) -> Array:
        state = self.base * self.gamma[:, None, None]
        if self.live_entries:
            keys_per_head = np.repeat(
                self.keys[: self.live_entries], self.heads_per_qk, axis=1
            )
            state = state + np.einsum(
                "ih,ihk,ihv->hkv",
                self.lambdas[: self.live_entries],
                keys_per_head,
                self.updates[: self.live_entries],
            )
        return np.asarray(state, dtype=self.dtype)

    def _fold(self, *, rebase: bool = False) -> None:
        effective = self.materialize_state()
        replacement = (
            effective.copy()
            if self.config.mode == "exact"
            else quantize_mxfp4_stack(
                effective,
                block_size=self.config.base_block_size,
                depth=self.config.base_stack_depth,
            )
        )
        self.base = np.asarray(replacement, dtype=self.dtype)
        self.gamma.fill(1)
        self.keys[: self.live_entries].fill(0)
        self.updates[: self.live_entries].fill(0)
        self.lambdas[: self.live_entries].fill(0)
        self.live_entries = 0
        self.counters.folds += 1
        if rebase:
            self.counters.coefficient_rebases += 1

    def _decay_coefficients(self, alpha: Array) -> None:
        if self.config.mode != "exact":
            gamma_product = self.gamma * alpha
            lambda_product = self.lambdas[: self.live_entries] * alpha[None, :]
            gamma_underflow = (self.gamma != 0) & (alpha != 0) & (gamma_product == 0)
            lambda_underflow = (
                (self.lambdas[: self.live_entries] != 0)
                & (alpha[None, :] != 0)
                & (lambda_product == 0)
            )
            if np.any(gamma_underflow) or np.any(lambda_underflow):
                self._fold(rebase=True)
        self.gamma *= alpha
        if self.live_entries:
            self.lambdas[: self.live_entries] *= alpha[None, :]

    def _should_fold(self) -> bool:
        if self.live_entries == self.config.capacity:
            return True
        if self.config.fold_policy == "fixed":
            return False
        return (
            self.live_entries >= self.config.adaptive_min_entries
            and float(np.mean(self.gamma, dtype=np.float64))
            <= self.config.fold_decay_threshold
        )

    def step_core(
        self,
        q_scaled: object,
        k_normalized: object,
        v: object,
        alpha: object,
        beta: object,
    ) -> Tuple[Array, Array]:
        q_array, k_array, v_array, alpha_array, beta_array = self._validate_core_inputs(
            q_scaled, k_normalized, v, alpha, beta
        )
        if self.live_entries >= self.config.capacity:
            raise RuntimeError("write log is full before accepting a token")

        self._decay_coefficients(alpha_array)
        prediction = self._left_action(k_array)
        update = beta_array[:, None] * (v_array - prediction)

        slot = self.live_entries
        self.keys[slot] = np.asarray(_quantize_log(k_array, self.config), dtype=self.dtype)
        self.updates[slot] = np.asarray(_quantize_log(update, self.config), dtype=self.dtype)
        self.lambdas[slot].fill(1)
        self.live_entries += 1
        self.counters.appended_entries += 1
        self.counters.max_live_entries = max(
            self.counters.max_live_entries, self.live_entries
        )

        output = self._left_action(q_array)
        if self._should_fold():
            self._fold()
        resident_state = self.materialize_state()
        return np.asarray(output, dtype=self.dtype), resident_state

    def step(
        self,
        q: object,
        k: object,
        v: object,
        alpha: object,
        beta: object,
        *,
        eps: float = L2_EPS,
    ) -> Tuple[Array, Array]:
        if self.config.mode == "exact":
            q_scaled, k_normalized = _normalize_qk_fp64(q, k, eps)
            return self.step_core(q_scaled, k_normalized, v, alpha, beta)

        q_scaled, k_normalized = normalize_qk(q, k, eps=eps)
        q_quantized = quantize_mxfp4_stack(
            q_scaled,
            block_size=self.config.activation_block_size,
            depth=self.config.activation_stack_depth,
        )
        k_quantized = quantize_mxfp4_stack(
            k_normalized,
            block_size=self.config.activation_block_size,
            depth=self.config.activation_stack_depth,
        )
        v_quantized = quantize_mxfp4_stack(
            v,
            block_size=self.config.activation_block_size,
            depth=self.config.activation_stack_depth,
        )
        alpha_quantized = decode_q1_15(encode_q1_15(alpha))
        beta_quantized = decode_q1_15(encode_q1_15(beta))
        return self.step_core(
            q_quantized,
            k_quantized,
            v_quantized,
            alpha_quantized,
            beta_quantized,
        )

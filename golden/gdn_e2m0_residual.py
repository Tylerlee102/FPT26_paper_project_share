"""MXFP4 base with a dense E2M0-style fold-residual correction.

The first stack term is ordinary E2M1/E8M0 MXFP4. Each later term uses a
three-bit signed element with magnitudes ``[0, 0.5, 1, 2]`` and one E8M0 scale
per block. For each residual block, the quantizer evaluates the overflow-free
scale and the adjacent scale one power of two lower, then selects the candidate
with lower squared reconstruction error. Ties keep the overflow-free scale.

This module is separate from ``gdn_write_log`` so the frozen write-log evidence
continues to identify the exact source that produced it.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from .gdn_mxfp4 import quantize_activation
from .gdn_write_log import (
    Array,
    LazyWriteLogGDN,
    WriteLogConfiguration,
    _as_finite,
    _quantize_log,
    quantize_mxfp4_stack,
)
from .mx_format import E8M0_BIAS, decode_e8m0_scale


E2M0_RESIDUAL_VALUES = np.array([0.0, 0.5, 1.0, 2.0], dtype=np.float32)
E2M0_RESIDUAL_MAX = float(E2M0_RESIDUAL_VALUES[-1])
E2M0_RESIDUAL_BITS = 3
E2M0_SCALE_POLICY = "min_sse_adjacent_e8m0"
VALID_LOG_MODES = {"mxfp8_e4m3", "mxfp4_rs2"}


def _block_view(values: Array, block_size: int) -> Tuple[Array, int]:
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    length = values.shape[-1]
    blocks = (length + block_size - 1) // block_size
    padded_length = blocks * block_size
    if padded_length == length:
        padded = values
    else:
        pad_width = [(0, 0)] * values.ndim
        pad_width[-1] = (0, padded_length - length)
        padded = np.pad(values, pad_width, mode="constant")
    return padded.reshape(*padded.shape[:-1], blocks, block_size), length


def _restore_blocks(blocks: Array, length: int) -> Array:
    flattened = blocks.reshape(
        *blocks.shape[:-2], blocks.shape[-2] * blocks.shape[-1]
    )
    return flattened[..., :length].astype(np.float32)


def _round_e2m0_magnitude(values: Array) -> Array:
    """Round nonnegative scaled values to the four-value table with RNE ties."""

    clipped = np.clip(values, 0.0, E2M0_RESIDUAL_MAX)
    upper = np.searchsorted(E2M0_RESIDUAL_VALUES, clipped, side="left")
    upper = np.clip(upper, 0, E2M0_RESIDUAL_VALUES.size - 1)
    lower = np.maximum(upper - 1, 0)
    lower_distance = np.abs(clipped - E2M0_RESIDUAL_VALUES[lower])
    upper_distance = np.abs(E2M0_RESIDUAL_VALUES[upper] - clipped)
    tied = lower_distance == upper_distance
    choose_upper = (upper_distance < lower_distance) | (
        tied & ((upper & 1) == 0) & ((lower & 1) != 0)
    )
    indices = np.where(choose_upper, upper, lower)
    return E2M0_RESIDUAL_VALUES[indices]


def _quantize_at_scale(blocks: Array, scale_codes: Array) -> Array:
    scales = decode_e8m0_scale(scale_codes)
    scaled = blocks / scales[..., None]
    magnitudes = _round_e2m0_magnitude(np.abs(scaled))
    signed = np.where(np.signbit(scaled), -magnitudes, magnitudes)
    return (signed * scales[..., None]).astype(np.float32)


def quantize_e2m0_residual(
    values: object,
    *,
    block_size: int,
) -> Array:
    """Quantize a dense residual with an error-selected E2M0/E8M0 block scale."""

    source = _as_finite("values", values, np.dtype(np.float32))
    blocks, length = _block_view(source, block_size)
    max_abs = np.max(np.abs(blocks), axis=-1)
    safe_max = np.maximum(max_abs, np.float32(np.finfo(np.float32).tiny))
    unbiased = np.where(
        max_abs == 0.0,
        0.0,
        np.ceil(np.log2(safe_max / E2M0_RESIDUAL_MAX)),
    ).astype(np.int32)
    overflow_free_codes = np.clip(unbiased + E8M0_BIAS, 0, 254).astype(np.uint8)
    lower_codes = np.maximum(
        overflow_free_codes.astype(np.int16) - 1, 0
    ).astype(np.uint8)

    overflow_free = _quantize_at_scale(blocks, overflow_free_codes)
    lower = _quantize_at_scale(blocks, lower_codes)
    overflow_error = np.sum(
        (overflow_free.astype(np.float64) - blocks.astype(np.float64)) ** 2,
        axis=-1,
    )
    lower_error = np.sum(
        (lower.astype(np.float64) - blocks.astype(np.float64)) ** 2,
        axis=-1,
    )
    choose_lower = lower_error < overflow_error
    selected = np.where(choose_lower[..., None], lower, overflow_free)
    return _restore_blocks(selected, length)


def quantize_mxfp4_e2m0_stack(
    values: object,
    *,
    block_size: int,
    depth: int,
) -> Array:
    """Reconstruct values as one MXFP4 term plus dense E2M0 residual terms."""

    if depth <= 0:
        raise ValueError("residual-stack depth must be positive")
    source = _as_finite("values", values, np.dtype(np.float32))
    reconstruction = np.zeros_like(source)
    residual = source.copy()
    for stack_index in range(depth):
        term = (
            quantize_activation(residual, block_size=block_size)
            if stack_index == 0
            else quantize_e2m0_residual(residual, block_size=block_size)
        )
        reconstruction = (reconstruction + term).astype(np.float32)
        residual = (source - reconstruction).astype(np.float32)
    return reconstruction


class E2M0ResidualWriteLogGDN(LazyWriteLogGDN):
    """Lazy write-log recurrence with E2M0-corrected MXFP4 base folds."""

    def __init__(
        self,
        initial_state: object,
        *,
        num_qk_heads: int,
        config: WriteLogConfiguration,
        log_mode: str = "mxfp4_rs2",
    ) -> None:
        if log_mode not in VALID_LOG_MODES:
            raise ValueError(f"unknown E2M0 write-log mode: {log_mode}")
        self.log_mode = log_mode
        super().__init__(initial_state, num_qk_heads=num_qk_heads, config=config)
        if config.mode != "exact":
            self.base = quantize_mxfp4_e2m0_stack(
                initial_state,
                block_size=config.base_block_size,
                depth=config.base_stack_depth,
            )

    def _quantize_log_values(self, values: Array) -> Array:
        if self.log_mode == "mxfp4_rs2" and self.config.mode != "exact":
            return quantize_mxfp4_stack(
                values,
                block_size=self.config.log_block_size,
                depth=2,
            )
        return _quantize_log(values, self.config)

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
        self.keys[slot] = np.asarray(
            self._quantize_log_values(k_array), dtype=self.dtype
        )
        self.updates[slot] = np.asarray(
            self._quantize_log_values(update), dtype=self.dtype
        )
        self.lambdas[slot].fill(1)
        self.live_entries += 1
        self.counters.appended_entries += 1
        self.counters.max_live_entries = max(
            self.counters.max_live_entries, self.live_entries
        )

        output = self._left_action(q_array)
        if self._should_fold():
            self._fold()
        return np.asarray(output, dtype=self.dtype), self.materialize_state()

    def _fold(self, *, rebase: bool = False) -> None:
        effective = self.materialize_state()
        replacement = (
            effective.copy()
            if self.config.mode == "exact"
            else quantize_mxfp4_e2m0_stack(
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

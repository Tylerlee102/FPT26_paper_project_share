"""State-scale refresh policies for floating MXFP4 Q/DQ diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .mx_format import (
    decode_e8m0_scale,
    from_mxfp4,
    to_mxfp4,
    to_mxfp4_with_scales,
)


@dataclass(frozen=True)
class StateQuantizationResult:
    resident_state: np.ndarray
    elements: np.ndarray
    scales: np.ndarray
    element_saturations: int
    scale_refreshes: int
    state_scale_changes: int


def _validate_state(state: object, block_size: int) -> np.ndarray:
    array = np.asarray(state, dtype=np.float32)
    if array.ndim != 3:
        raise ValueError("state must have shape [value_heads, key_dim, value_dim]")
    if block_size not in (16, 32):
        raise ValueError("block_size must be 16 or 32")
    if not np.all(np.isfinite(array)):
        raise ValueError("state must be finite")
    return array


def _state_blocks(state: np.ndarray, block_size: int) -> np.ndarray:
    value_dim = state.shape[-1]
    blocks = (value_dim + block_size - 1) // block_size
    padded = blocks * block_size
    if padded != value_dim:
        state = np.pad(state, ((0, 0), (0, 0), (0, padded - value_dim)))
    return state.reshape(*state.shape[:-1], blocks, block_size)


def initialize_mxfp4_state(
    state: object,
    *,
    block_size: int = 32,
) -> StateQuantizationResult:
    """Calibrate initial state scales and return the resident Q/DQ state."""

    array = _validate_state(state, block_size)
    elements, scales = to_mxfp4(array, block_size=block_size, axis=-1)
    elements, saturations = to_mxfp4_with_scales(
        array,
        scales,
        block_size=block_size,
        axis=-1,
    )
    resident = from_mxfp4(elements, scales, block_size=block_size, axis=-1)
    return StateQuantizationResult(
        resident_state=resident,
        elements=elements,
        scales=scales,
        element_saturations=saturations,
        scale_refreshes=int(scales.size),
        state_scale_changes=0,
    )


def quantize_mxfp4_state_with_policy(
    state: object,
    previous_scales: object,
    *,
    token_index: int,
    policy: str,
    block_size: int = 32,
    refresh_interval: int | None = None,
    threshold_low: float = 0.75,
    threshold_high: float = 5.5,
) -> StateQuantizationResult:
    """Quantize one updated state using a frozen scale-refresh policy."""

    array = _validate_state(state, block_size)
    if token_index < 1:
        raise ValueError("token_index must start at one")
    scales = np.asarray(previous_scales)
    if not np.issubdtype(scales.dtype, np.integer):
        raise ValueError("previous scales must be integer E8M0 codes")
    scales = scales.astype(np.int64)
    expected_blocks = (array.shape[-1] + block_size - 1) // block_size
    expected_shape = (*array.shape[:-1], expected_blocks)
    if scales.shape != expected_shape:
        raise ValueError(f"previous scales must have shape {expected_shape}")
    if np.any(scales < 0) or np.any(scales > 254):
        raise ValueError("previous E8M0 scale codes must be in 0..254")
    scales = scales.astype(np.uint8)

    refresh_mask = np.zeros(scales.shape, dtype=bool)
    if policy == "every_token":
        refresh_mask[...] = True
    elif policy == "fixed":
        pass
    elif policy == "periodic":
        if refresh_interval is None or refresh_interval <= 0:
            raise ValueError("periodic policy requires a positive refresh_interval")
        if token_index % refresh_interval == 0:
            refresh_mask[...] = True
    elif policy == "threshold":
        if not (0.0 <= threshold_low < threshold_high):
            raise ValueError("thresholds must satisfy 0 <= low < high")
        blocks = _state_blocks(array, block_size)
        scale_values = decode_e8m0_scale(scales)
        normalized_max = np.max(
            np.abs(blocks) / scale_values[..., None], axis=-1
        )
        refresh_mask = (normalized_max > threshold_high) | (
            (normalized_max > 0.0) & (normalized_max < threshold_low)
        )
    else:
        raise ValueError(f"unknown scale policy: {policy}")

    selected_scales = scales.copy()
    if np.any(refresh_mask):
        _, candidate_scales = to_mxfp4(array, block_size=block_size, axis=-1)
        selected_scales[refresh_mask] = candidate_scales[refresh_mask]

    elements, saturations = to_mxfp4_with_scales(
        array,
        selected_scales,
        block_size=block_size,
        axis=-1,
    )
    resident = from_mxfp4(
        elements,
        selected_scales,
        block_size=block_size,
        axis=-1,
    )
    return StateQuantizationResult(
        resident_state=resident,
        elements=elements,
        scales=selected_scales,
        element_saturations=saturations,
        scale_refreshes=int(np.count_nonzero(refresh_mask)),
        state_scale_changes=int(np.count_nonzero(selected_scales != scales)),
    )

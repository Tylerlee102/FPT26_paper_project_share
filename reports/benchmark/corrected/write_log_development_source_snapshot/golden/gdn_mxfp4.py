"""Diagnostic MX Q/DQ model around the corrected GDN recurrence.

This module is deliberately not the encoded-integer oracle. It quantizes and
dequantizes tensors, then executes FP32 arithmetic. Results from this module are
software diagnostics only and cannot establish HLS bit parity.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from .gdn_fp32 import gdn_recurrence_core_step, normalize_qk
from .gdn_mxfp4_encoded import decode_q1_15, encode_q1_15
from .mx_format import from_mxfp4, from_mxfp8, to_mxfp4, to_mxfp8


def _mxfp4_roundtrip(x: object, *, block_size: int, axis: int) -> np.ndarray:
    elements, scales = to_mxfp4(x, block_size=block_size, axis=axis)
    return from_mxfp4(elements, scales, block_size=block_size, axis=axis)


def _mxfp8_roundtrip(x: object, *, block_size: int, axis: int) -> np.ndarray:
    elements, scales = to_mxfp8(x, block_size=block_size, axis=axis)
    return from_mxfp8(elements, scales, block_size=block_size, axis=axis)


def quantize_activation(x: object, *, block_size: int = 32) -> np.ndarray:
    return _mxfp4_roundtrip(x, block_size=block_size, axis=-1)


def quantize_state(x: object, *, block_size: int = 32, precision: str = "mxfp4") -> np.ndarray:
    if precision == "mxfp4":
        return _mxfp4_roundtrip(x, block_size=block_size, axis=-1)
    if precision == "mxfp8_e4m3":
        return _mxfp8_roundtrip(x, block_size=block_size, axis=-1)
    raise ValueError(f"unknown state precision: {precision}")


def gdn_decode_step(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
    *,
    block_size: int = 32,
    state_block_size: int = 32,
    state_precision: str = "mxfp4",
) -> Tuple[np.ndarray, np.ndarray]:
    """Run one corrected token after MX quantize/dequantize boundaries."""

    q_scaled, k_normalized = normalize_qk(q, k)
    q_q = quantize_activation(q_scaled, block_size=block_size)
    k_q = quantize_activation(k_normalized, block_size=block_size)
    v_q = quantize_activation(v, block_size=block_size)
    state_q = quantize_state(state_in, block_size=state_block_size, precision=state_precision)
    alpha_q = decode_q1_15(encode_q1_15(alpha))
    beta_q = decode_q1_15(encode_q1_15(beta))
    output, updated_state = gdn_recurrence_core_step(
        q_q,
        k_q,
        v_q,
        alpha_q,
        beta_q,
        state_q,
    )
    resident_state = quantize_state(
        updated_state,
        block_size=state_block_size,
        precision=state_precision,
    )
    return output, resident_state


def gdn_decode_step_ablation(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
    *,
    quantized_tensors: set[str],
    block_size: int = 32,
    state_block_size: int = 32,
    state_precision: str = "mxfp4",
) -> Tuple[np.ndarray, np.ndarray]:
    """Quantize selected tensors and execute the corrected FP32 recurrence."""

    valid = {"q", "k", "v", "state"}
    unknown = quantized_tensors - valid
    if unknown:
        raise ValueError(f"unknown ablation tensors: {sorted(unknown)}")

    q_scaled, k_normalized = normalize_qk(q, k)
    q_input = (
        quantize_activation(q_scaled, block_size=block_size)
        if "q" in quantized_tensors
        else q_scaled
    )
    k_input = (
        quantize_activation(k_normalized, block_size=block_size)
        if "k" in quantized_tensors
        else k_normalized
    )
    v_input = quantize_activation(v, block_size=block_size) if "v" in quantized_tensors else v
    state_input = (
        quantize_state(state_in, block_size=state_block_size, precision=state_precision)
        if "state" in quantized_tensors
        else state_in
    )
    output, updated_state = gdn_recurrence_core_step(
        np.asarray(q_input, dtype=np.float32),
        np.asarray(k_input, dtype=np.float32),
        np.asarray(v_input, dtype=np.float32),
        decode_q1_15(encode_q1_15(alpha)),
        decode_q1_15(encode_q1_15(beta)),
        np.asarray(state_input, dtype=np.float32),
    )
    if "state" in quantized_tensors:
        updated_state = quantize_state(
            updated_state,
            block_size=state_block_size,
            precision=state_precision,
        )
    return output, updated_state

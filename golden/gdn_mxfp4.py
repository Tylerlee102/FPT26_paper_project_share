"""MXFP4 GDN reference model.

This model exercises the same quantize/dequantize boundary that the HLS kernel
will consume: E2M1 elements plus E8M0 block scales. The arithmetic body reuses
the FP32 recurrence until the integer HLS datapath lands, so this file is a
functional golden reference rather than a timing model.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from .gdn_fp32 import gdn_decode_step as gdn_decode_step_fp32
from .mx_format import from_mxfp4, from_mxfp8, to_mxfp4, to_mxfp8


def _mxfp4_roundtrip(x: object, *, block_size: int, axis: int) -> np.ndarray:
    elements, scales = to_mxfp4(x, block_size=block_size, axis=axis)
    return from_mxfp4(elements, scales, block_size=block_size, axis=axis)


def _mxfp8_roundtrip(x: object, *, block_size: int, axis: int) -> np.ndarray:
    elements, scales = to_mxfp8(x, block_size=block_size, axis=axis)
    return from_mxfp8(elements, scales, block_size=block_size, axis=axis)


def quantize_activation(x: object, *, block_size: int = 32) -> np.ndarray:
    return _mxfp4_roundtrip(x, block_size=block_size, axis=-1)


def quantize_state(x: object, *, block_size: int = 16, precision: str = "mxfp4") -> np.ndarray:
    if precision == "mxfp4":
        return _mxfp4_roundtrip(x, block_size=block_size, axis=-1)
    if precision == "mxfp8":
        return _mxfp8_roundtrip(x, block_size=block_size, axis=-1)
    raise ValueError(f"unknown state precision: {precision}")


def gdn_decode_step(
    q: object,
    k: object,
    v: object,
    beta: object,
    gate: object,
    state_in: object,
    *,
    block_size: int = 32,
    state_block_size: int = 16,
    state_precision: str = "mxfp4",
) -> Tuple[np.ndarray, np.ndarray]:
    """Run one decode step after MXFP4 quantizing activations and state."""

    q_q = quantize_activation(q, block_size=block_size)
    k_q = quantize_activation(k, block_size=block_size)
    v_q = quantize_activation(v, block_size=block_size)
    gate_q = quantize_activation(gate, block_size=block_size)
    state_q = quantize_state(state_in, block_size=state_block_size, precision=state_precision)
    beta_q = np.asarray(beta, dtype=np.float32)
    return gdn_decode_step_fp32(q_q, k_q, v_q, beta_q, gate_q, state_q)


def gdn_decode_step_ablation(
    q: object,
    k: object,
    v: object,
    beta: object,
    gate: object,
    state_in: object,
    *,
    quantized_tensors: set[str],
    block_size: int = 32,
    state_block_size: int = 16,
    state_precision: str = "mxfp4",
) -> Tuple[np.ndarray, np.ndarray]:
    """Quantize only selected tensors and run the FP32 recurrence."""

    valid = {"q", "k", "v", "gate", "state"}
    unknown = quantized_tensors - valid
    if unknown:
        raise ValueError(f"unknown ablation tensors: {sorted(unknown)}")

    q_i = quantize_activation(q, block_size=block_size) if "q" in quantized_tensors else np.asarray(q, dtype=np.float32)
    k_i = quantize_activation(k, block_size=block_size) if "k" in quantized_tensors else np.asarray(k, dtype=np.float32)
    v_i = quantize_activation(v, block_size=block_size) if "v" in quantized_tensors else np.asarray(v, dtype=np.float32)
    gate_i = (
        quantize_activation(gate, block_size=block_size)
        if "gate" in quantized_tensors
        else np.asarray(gate, dtype=np.float32)
    )
    state_i = (
        quantize_state(state_in, block_size=state_block_size, precision=state_precision)
        if "state" in quantized_tensors
        else np.asarray(state_in, dtype=np.float32)
    )
    return gdn_decode_step_fp32(q_i, k_i, v_i, np.asarray(beta, dtype=np.float32), gate_i, state_i)

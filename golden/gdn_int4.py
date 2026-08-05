"""Flat symmetric INT4 diagnostic for the corrected GDN recurrence."""

from __future__ import annotations

from typing import Tuple

import numpy as np

from .gdn_fp32 import gdn_recurrence_core_step, normalize_qk
from .gdn_mxfp4_encoded import decode_q1_15, encode_q1_15


def quantize_symmetric_int4(x: object) -> tuple[np.ndarray, np.float32]:
    array = np.asarray(x, dtype=np.float32)
    if not np.all(np.isfinite(array)):
        raise ValueError("INT4 tensors cannot contain NaN or Inf")
    max_abs = float(np.max(np.abs(array))) if array.size else 0.0
    scale = np.float32(1.0 if max_abs == 0.0 else max_abs / 7.0)
    codes = np.rint(array / scale).astype(np.int32)
    return np.clip(codes, -7, 7).astype(np.int8), scale


def dequantize_symmetric_int4(codes: object, scale: object) -> np.ndarray:
    return (
        np.asarray(codes, dtype=np.int8).astype(np.float32) * np.float32(scale)
    ).astype(np.float32)


def _int4_roundtrip(x: object) -> np.ndarray:
    codes, scale = quantize_symmetric_int4(x)
    return dequantize_symmetric_int4(codes, scale)


def gdn_decode_step(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
) -> Tuple[np.ndarray, np.ndarray]:
    """Run one corrected token through a flat INT4 Q/DQ fallback."""

    q_scaled, k_normalized = normalize_qk(q, k)
    output, updated_state = gdn_recurrence_core_step(
        _int4_roundtrip(q_scaled),
        _int4_roundtrip(k_normalized),
        _int4_roundtrip(v),
        decode_q1_15(encode_q1_15(alpha)),
        decode_q1_15(encode_q1_15(beta)),
        _int4_roundtrip(state_in),
    )
    return output, _int4_roundtrip(updated_state)

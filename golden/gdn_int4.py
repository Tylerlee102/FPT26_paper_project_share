"""INT4 fallback GDN model for the Phase 4 decision gate."""

from __future__ import annotations

from typing import Tuple

import numpy as np

from .gdn_fp32 import gdn_decode_step as gdn_decode_step_fp32


def quantize_symmetric_int4(x: object) -> tuple[np.ndarray, np.float32]:
    arr = np.asarray(x, dtype=np.float32)
    if not np.all(np.isfinite(arr)):
        raise ValueError("INT4 tensors cannot contain NaN or Inf")
    max_abs = float(np.max(np.abs(arr))) if arr.size else 0.0
    scale = np.float32(1.0 if max_abs == 0.0 else max_abs / 7.0)
    codes = np.rint(arr / scale).astype(np.int32)
    return np.clip(codes, -7, 7).astype(np.int8), scale


def dequantize_symmetric_int4(codes: object, scale: object) -> np.ndarray:
    return (np.asarray(codes, dtype=np.int8).astype(np.float32) * np.float32(scale)).astype(np.float32)


def _int4_roundtrip(x: object) -> np.ndarray:
    codes, scale = quantize_symmetric_int4(x)
    return dequantize_symmetric_int4(codes, scale)


def gdn_decode_step(
    q: object,
    k: object,
    v: object,
    beta: object,
    gate: object,
    state_in: object,
) -> Tuple[np.ndarray, np.ndarray]:
    """Run one decode step through the simple symmetric INT4 fallback path."""

    return gdn_decode_step_fp32(
        _int4_roundtrip(q),
        _int4_roundtrip(k),
        _int4_roundtrip(v),
        np.asarray(beta, dtype=np.float32),
        _int4_roundtrip(gate),
        _int4_roundtrip(state_in),
    )

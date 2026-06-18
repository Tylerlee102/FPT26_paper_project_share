"""MX format primitives for the Python golden path.

The implementation is deliberately table-driven for the tiny element formats.
That keeps rounding behavior visible and gives the HLS tests a compact source of
truth to compare against.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple

import numpy as np


E8M0_BIAS = 127
E2M1_VALUES = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0], dtype=np.float32)
E2M1_MAX = float(E2M1_VALUES[-1])


@dataclass(frozen=True)
class MXTensor:
    elements: np.ndarray
    scales: np.ndarray
    block_size: int
    axis: int


def _as_float32(x: object) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float32)
    if not np.all(np.isfinite(arr)):
        raise ValueError("MX tensors cannot contain NaN or Inf")
    return arr


def _normalize_axis(axis: int, ndim: int) -> int:
    if axis < 0:
        axis += ndim
    if axis < 0 or axis >= ndim:
        raise ValueError(f"axis {axis} is out of range for {ndim} dimensions")
    return axis


def _round_to_even_index(distances: np.ndarray, codes: np.ndarray) -> np.ndarray:
    min_distance = np.min(distances, axis=-1, keepdims=True)
    ties = np.isclose(distances, min_distance, rtol=0.0, atol=1e-12)
    widened_codes = codes.astype(np.int16)
    even_preference = np.where((widened_codes % 2) == 0, 0, 1).astype(np.int16)
    ranked = np.where(ties, even_preference, 1000 + widened_codes)
    return np.argmin(ranked, axis=-1).astype(np.uint8)


def encode_e2m1(x: object) -> np.ndarray:
    """Encode float values to unsigned FP4 E2M1 bytes.

    The low nibble is used: bit 3 is sign, bits 2:0 select the magnitude table
    `[0, 0.5, 1, 1.5, 2, 3, 4, 6]`.
    """

    arr = _as_float32(x)
    sign = np.signbit(arr).astype(np.uint8) << 3
    abs_arr = np.clip(np.abs(arr), 0.0, E2M1_MAX)
    distances = np.abs(abs_arr[..., None] - E2M1_VALUES)
    codes = np.arange(E2M1_VALUES.size, dtype=np.uint8)
    mag = _round_to_even_index(distances, codes)
    return (sign | mag).astype(np.uint8)


def decode_e2m1(elements: object) -> np.ndarray:
    codes = np.asarray(elements, dtype=np.uint8) & 0x0F
    sign = np.where((codes & 0x08) != 0, -1.0, 1.0).astype(np.float32)
    mag = E2M1_VALUES[codes & 0x07]
    return (sign * mag).astype(np.float32)


def encode_e8m0_scale(scale: object) -> np.ndarray:
    arr = _as_float32(scale)
    if np.any(arr <= 0.0):
        raise ValueError("E8M0 scales must be positive")
    exponents = np.rint(np.log2(arr)).astype(np.int32) + E8M0_BIAS
    return np.clip(exponents, 0, 255).astype(np.uint8)


def decode_e8m0_scale(scales: object) -> np.ndarray:
    codes = np.asarray(scales, dtype=np.uint8).astype(np.int32)
    return np.exp2(codes - E8M0_BIAS).astype(np.float32)


def _block_view(x: np.ndarray, block_size: int, axis: int) -> Tuple[np.ndarray, int]:
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    moved = np.moveaxis(x, axis, -1)
    length = moved.shape[-1]
    num_blocks = (length + block_size - 1) // block_size
    padded_length = num_blocks * block_size
    if padded_length == length:
        padded = moved
    else:
        pad_width = [(0, 0)] * moved.ndim
        pad_width[-1] = (0, padded_length - length)
        padded = np.pad(moved, pad_width, mode="constant")
    return padded.reshape(*padded.shape[:-1], num_blocks, block_size), length


def _restore_blocks(blocked: np.ndarray, original_shape: tuple[int, ...], axis: int, length: int) -> np.ndarray:
    moved = blocked.reshape(*blocked.shape[:-2], blocked.shape[-2] * blocked.shape[-1])[..., :length]
    return np.moveaxis(moved, -1, axis).reshape(original_shape)


def _to_mx(
    x: object,
    block_size: int,
    axis: int,
    *,
    element_max: float,
    encode_element: Callable[[object], np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    arr = _as_float32(x)
    axis = _normalize_axis(axis, arr.ndim)
    blocks, length = _block_view(arr, block_size, axis)
    max_abs = np.max(np.abs(blocks), axis=-1)
    safe_max = np.maximum(max_abs, np.float32(np.finfo(np.float32).tiny))
    scale_exp = np.where(max_abs == 0.0, 0.0, np.ceil(np.log2(safe_max / element_max)))
    scales = encode_e8m0_scale(np.exp2(scale_exp).astype(np.float32))
    decoded_scales = decode_e8m0_scale(scales)
    scaled = blocks / decoded_scales[..., None]
    quantized_blocks = encode_element(scaled)
    elements = _restore_blocks(quantized_blocks, arr.shape, axis, length)
    return elements.astype(np.uint8), scales.astype(np.uint8)


def _from_mx(
    elements: object,
    scales: object,
    block_size: int,
    axis: int,
    *,
    decode_element: Callable[[object], np.ndarray],
) -> np.ndarray:
    elems = np.asarray(elements, dtype=np.uint8)
    axis = _normalize_axis(axis, elems.ndim)
    blocks, length = _block_view(elems, block_size, axis)
    scale_arr = np.asarray(scales, dtype=np.uint8)
    expected = blocks.shape[:-1]
    if scale_arr.shape != expected:
        raise ValueError(f"scales shape must be {expected}, got {scale_arr.shape}")
    values = decode_element(blocks) * decode_e8m0_scale(scale_arr)[..., None]
    return _restore_blocks(values.astype(np.float32), elems.shape, axis, length).astype(np.float32)


def to_mxfp4(x: object, block_size: int, axis: int) -> tuple[np.ndarray, np.ndarray]:
    """Quantize to MXFP4 using E2M1 elements and E8M0 power-of-two scales."""

    return _to_mx(
        x,
        block_size,
        axis,
        element_max=E2M1_MAX,
        encode_element=encode_e2m1,
    )


def from_mxfp4(elements: object, scales: object, block_size: int, axis: int) -> np.ndarray:
    return _from_mx(
        elements,
        scales,
        block_size,
        axis,
        decode_element=decode_e2m1,
    )


def _e4m3_table() -> np.ndarray:
    values = np.zeros(256, dtype=np.float32)
    for code in range(256):
        sign = -1.0 if code & 0x80 else 1.0
        exp = (code >> 3) & 0x0F
        mant = code & 0x07
        if exp == 0:
            mag = (mant / 8.0) * np.exp2(-6)
        else:
            mag = (1.0 + mant / 8.0) * np.exp2(exp - 7)
        values[code] = sign * mag
    return values


E4M3_VALUES = _e4m3_table()
E4M3_MAX = float(np.max(E4M3_VALUES))


def encode_e4m3(x: object) -> np.ndarray:
    arr = _as_float32(x)
    codes = np.arange(256, dtype=np.uint8)
    flat = arr.reshape(-1)
    encoded = np.empty(flat.shape, dtype=np.uint8)
    chunk_size = 65536
    for start in range(0, flat.size, chunk_size):
        stop = min(start + chunk_size, flat.size)
        distances = np.abs(flat[start:stop, None] - E4M3_VALUES)
        encoded[start:stop] = _round_to_even_index(distances, codes)
    return encoded.reshape(arr.shape)


def decode_e4m3(elements: object) -> np.ndarray:
    return E4M3_VALUES[np.asarray(elements, dtype=np.uint8)].astype(np.float32)


def to_mxfp8(x: object, block_size: int, axis: int) -> tuple[np.ndarray, np.ndarray]:
    """Quantize to MXFP8 using E4M3 elements and E8M0 power-of-two scales."""

    return _to_mx(
        x,
        block_size,
        axis,
        element_max=E4M3_MAX,
        encode_element=encode_e4m3,
    )


def from_mxfp8(elements: object, scales: object, block_size: int, axis: int) -> np.ndarray:
    return _from_mx(
        elements,
        scales,
        block_size,
        axis,
        decode_element=decode_e4m3,
    )


def quantization_error(original: object, restored: object) -> dict[str, float]:
    """Return compact absolute, relative, and cosine error metrics."""

    a = _as_float32(original).reshape(-1)
    b = _as_float32(restored).reshape(-1)
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    diff = b - a
    denom = float(np.linalg.norm(a))
    b_norm = float(np.linalg.norm(b))
    cosine = 1.0 if denom == 0.0 and b_norm == 0.0 else float(np.dot(a, b) / max(denom * b_norm, 1e-30))
    return {
        "max_abs": float(np.max(np.abs(diff))) if diff.size else 0.0,
        "mean_abs": float(np.mean(np.abs(diff))) if diff.size else 0.0,
        "rel_l2": float(np.linalg.norm(diff) / max(denom, 1e-30)),
        "cosine": cosine,
    }

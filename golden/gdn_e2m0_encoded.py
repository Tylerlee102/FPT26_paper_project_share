"""Encoded-integer oracle for the E2M0-corrected MXFP4 write-log GDN.

This module is intentionally independent of the floating Q/DQ feasibility
model in :mod:`golden.gdn_e2m0_residual`.  It defines the finite-arithmetic
contract intended for HLS: two residual-stacked E2M1/E8M0 terms for token and
log vectors, an E2M1 base plus a signed three-bit E2M0 residual, Q1.15 decay
coefficients, INT32 aligned accumulation, and a fixed-capacity atomic fold.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .gdn_mxfp4_encoded import (
    E8M0_BIAS,
    ArithmeticCounters,
    _decode_integer_arrays,
    _multiply_q1_15,
    _quantize_exact_e2m1,
    _round_shift_rne,
    _saturate_int32,
    _select_scale_power,
    _to_float32,
    _validate_encoded_array,
    decode_q1_15,
    encode_q1_15,
)
from .mx_format import from_mxfp4, to_mxfp4


E2M0_INTEGER_MAGNITUDES = (0, 1, 2, 4)
E2M0_INVALID_NEGATIVE_ZERO = 4
COEFFICIENT_ONE = 1 << 15
ACCUMULATOR_BITS = 32
ACCUMULATOR_GUARD_BITS = 5


@dataclass
class E2M0ArithmeticCounters(ArithmeticCounters):
    e2m0_residual_clips: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            **super().as_dict(),
            "e2m0_residual_clips": self.e2m0_residual_clips,
        }


def _aligned_sum_guarded(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    counters: ArithmeticCounters,
) -> tuple[int, int]:
    """INT32 reduction retaining five powers below the largest raw exponent."""

    flat_m = np.asarray(mantissas, dtype=np.int64).reshape(-1)
    flat_x = np.asarray(exponents, dtype=np.int64).reshape(-1)
    nonzero = flat_m != 0
    if not np.any(nonzero):
        return 0, 0
    target = int(np.max(flat_x[nonzero])) - ACCUMULATOR_GUARD_BITS
    accumulator = 0
    for mantissa, exponent in zip(flat_m, flat_x):
        raw = int(mantissa)
        if raw == 0:
            continue
        shift = target - int(exponent)
        aligned = (
            _round_shift_rne(raw, shift)
            if shift >= 0
            else raw << (-shift)
        )
        if aligned == 0 and shift > 0:
            counters.alignment_underflows += 1
        accumulator = _saturate_int32(accumulator + aligned, counters)
    return accumulator, target


@dataclass(frozen=True)
class EncodedMXFP4Stack:
    elements: np.ndarray
    scales: np.ndarray
    block_size: int


@dataclass(frozen=True)
class EncodedE2M0State:
    primary_elements: np.ndarray
    primary_scales: np.ndarray
    residual_elements: np.ndarray
    residual_scales: np.ndarray
    block_size: int


@dataclass(frozen=True)
class EncodedE2M0Token:
    q: EncodedMXFP4Stack
    k: EncodedMXFP4Stack
    v: EncodedMXFP4Stack
    alpha_codes: np.ndarray
    beta_codes: np.ndarray


@dataclass(frozen=True)
class EncodedE2M0StepResult:
    output_mantissas: np.ndarray
    output_exponents: np.ndarray
    output_fp32: np.ndarray
    materialized_state_fp32: np.ndarray
    counters: ArithmeticCounters
    folded: bool
    live_entries: int


def _copy_stack(stack: EncodedMXFP4Stack) -> EncodedMXFP4Stack:
    return EncodedMXFP4Stack(
        np.array(stack.elements, dtype=np.uint8, copy=True),
        np.array(stack.scales, dtype=np.uint8, copy=True),
        stack.block_size,
    )


def _stack_from_float(values: object, *, block_size: int, depth: int = 2) -> EncodedMXFP4Stack:
    if depth != 2:
        raise ValueError("the encoded hardware candidate fixes stack depth to two")
    source = np.asarray(values, dtype=np.float32)
    if source.ndim < 1 or not np.all(np.isfinite(source)):
        raise ValueError("stack source must be a finite array")
    residual = source.copy()
    elements: list[np.ndarray] = []
    scales: list[np.ndarray] = []
    reconstruction = np.zeros_like(source)
    for _ in range(depth):
        term_elements, term_scales = to_mxfp4(
            residual, block_size=block_size, axis=-1
        )
        elements.append(term_elements.astype(np.uint8))
        scales.append(term_scales.astype(np.uint8))
        term = from_mxfp4(
            term_elements, term_scales, block_size=block_size, axis=-1
        )
        reconstruction = (reconstruction + term).astype(np.float32)
        residual = (source - reconstruction).astype(np.float32)
    return EncodedMXFP4Stack(
        np.stack(elements, axis=0), np.stack(scales, axis=0), block_size
    )


def _validate_stack(
    name: str, stack: EncodedMXFP4Stack
) -> tuple[np.ndarray, np.ndarray]:
    if not isinstance(stack, EncodedMXFP4Stack):
        raise TypeError(f"{name} must be EncodedMXFP4Stack")
    elements = np.asarray(stack.elements)
    scales = np.asarray(stack.scales)
    if elements.ndim < 2 or elements.shape[0] != 2 or scales.shape[0] != 2:
        raise ValueError(f"{name} must contain exactly two stack terms")
    checked_elements: list[np.ndarray] = []
    checked_scales: list[np.ndarray] = []
    for term in range(2):
        term_elements, term_scales = _validate_encoded_array(
            f"{name}[{term}]",
            elements[term],
            scales[term],
            stack.block_size,
            require_canonical_zero=True,
        )
        checked_elements.append(term_elements)
        checked_scales.append(term_scales)
    return np.stack(checked_elements), np.stack(checked_scales)


def decode_stack(stack: EncodedMXFP4Stack) -> np.ndarray:
    elements, scales = _validate_stack("stack", stack)
    result = np.zeros(elements.shape[1:], dtype=np.float32)
    for term in range(2):
        result = (
            result
            + from_mxfp4(
                elements[term],
                scales[term],
                block_size=stack.block_size,
                axis=-1,
            )
        ).astype(np.float32)
    return result


def _decode_stack_integer(
    name: str, stack: EncodedMXFP4Stack
) -> tuple[np.ndarray, np.ndarray]:
    elements, scales = _validate_stack(name, stack)
    mantissas: list[np.ndarray] = []
    exponents: list[np.ndarray] = []
    for term in range(2):
        term_mantissas, term_exponents = _decode_integer_arrays(
            f"{name}[{term}]",
            elements[term],
            scales[term],
            stack.block_size,
            require_canonical_zero=True,
        )
        mantissas.append(term_mantissas)
        exponents.append(term_exponents)
    return np.stack(mantissas), np.stack(exponents)


def _block_view(values: np.ndarray, block_size: int) -> tuple[np.ndarray, int]:
    length = values.shape[-1]
    blocks = (length + block_size - 1) // block_size
    padded_length = blocks * block_size
    if padded_length == length:
        padded = values
    else:
        pad = [(0, 0)] * values.ndim
        pad[-1] = (0, padded_length - length)
        padded = np.pad(values, pad)
    return padded.reshape(*padded.shape[:-1], blocks, block_size), length


def _encode_e2m0_float(
    values: object, *, block_size: int
) -> tuple[np.ndarray, np.ndarray]:
    source = np.asarray(values, dtype=np.float32)
    if source.ndim < 1 or not np.all(np.isfinite(source)):
        raise ValueError("E2M0 source must be a finite array")
    blocks, length = _block_view(source, block_size)
    max_abs = np.max(np.abs(blocks), axis=-1)
    safe = np.maximum(max_abs, np.float32(np.finfo(np.float32).tiny))
    power = np.where(
        max_abs == 0,
        0,
        np.ceil(np.log2(safe / np.float32(2.0))),
    ).astype(np.int32)
    upper_codes = np.clip(power + E8M0_BIAS, 0, 254).astype(np.uint8)
    lower_codes = np.maximum(upper_codes.astype(np.int16) - 1, 0).astype(np.uint8)

    candidates: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    table = np.asarray((0.0, 0.5, 1.0, 2.0), dtype=np.float32)
    for scale_codes in (upper_codes, lower_codes):
        scales = np.exp2(scale_codes.astype(np.int16) - E8M0_BIAS).astype(np.float32)
        scaled = blocks / scales[..., None]
        absolute = np.clip(np.abs(scaled), 0.0, 2.0)
        upper = np.clip(np.searchsorted(table, absolute, side="left"), 0, 3)
        lower = np.maximum(upper - 1, 0)
        lower_distance = np.abs(absolute - table[lower])
        upper_distance = np.abs(table[upper] - absolute)
        tie = lower_distance == upper_distance
        choose_upper = (upper_distance < lower_distance) | (
            tie & ((upper & 1) == 0) & ((lower & 1) != 0)
        )
        indices = np.where(choose_upper, upper, lower).astype(np.uint8)
        signs = np.where(np.signbit(scaled), np.uint8(4), np.uint8(0))
        codes = np.where(indices == 0, np.uint8(0), indices | signs).astype(np.uint8)
        reconstructed = np.where(
            signs != 0, -table[indices], table[indices]
        ) * scales[..., None]
        error = np.sum(
            (reconstructed.astype(np.float64) - blocks.astype(np.float64)) ** 2,
            axis=-1,
        )
        candidates.append((codes, reconstructed.astype(np.float32), error))

    choose_lower = candidates[1][2] < candidates[0][2]
    codes = np.where(choose_lower[..., None], candidates[1][0], candidates[0][0])
    scales = np.where(choose_lower, lower_codes, upper_codes).astype(np.uint8)
    flattened = codes.reshape(*codes.shape[:-2], codes.shape[-2] * block_size)
    return flattened[..., :length].astype(np.uint8), scales


def _validate_e2m0(
    name: str,
    elements: object,
    scales: object,
    block_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    element_array = np.asarray(elements)
    scale_array = np.asarray(scales)
    if block_size not in (16, 32) or element_array.ndim < 1:
        raise ValueError("E2M0 block size must be 16 or 32")
    if not np.issubdtype(element_array.dtype, np.integer) or not np.issubdtype(
        scale_array.dtype, np.integer
    ):
        raise ValueError(f"{name} codes must be integers")
    widened = element_array.astype(np.int64)
    if np.any(widened < 0) or np.any(widened > 7) or np.any(
        widened == E2M0_INVALID_NEGATIVE_ZERO
    ):
        raise ValueError(f"{name} contains an invalid E2M0 code")
    blocks = (element_array.shape[-1] + block_size - 1) // block_size
    expected = (*element_array.shape[:-1], blocks)
    if scale_array.shape != expected:
        raise ValueError(f"{name} scale shape must be {expected}")
    scale_wide = scale_array.astype(np.int64)
    if np.any(scale_wide < 0) or np.any(scale_wide > 254):
        raise ValueError(f"{name} contains invalid E8M0 scale code 255")
    for block in range(blocks):
        start = block * block_size
        stop = min(start + block_size, element_array.shape[-1])
        zero = np.all(widened[..., start:stop] == 0, axis=-1)
        if np.any(zero & (scale_wide[..., block] != E8M0_BIAS)):
            raise ValueError(f"{name} has a noncanonical zero block")
    return element_array.astype(np.uint8), scale_array.astype(np.uint8)


def _decode_e2m0_integer(
    name: str,
    elements: object,
    scales: object,
    block_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    element_array, scale_array = _validate_e2m0(
        name, elements, scales, block_size
    )
    magnitude_indices = element_array & np.uint8(3)
    table = np.asarray(E2M0_INTEGER_MAGNITUDES, dtype=np.int64)
    mantissas = table[magnitude_indices]
    mantissas = np.where((element_array & np.uint8(4)) != 0, -mantissas, mantissas)
    expanded = np.repeat(scale_array, block_size, axis=-1)[
        ..., : element_array.shape[-1]
    ]
    exponents = expanded.astype(np.int16) - np.int16(E8M0_BIAS + 1)
    return mantissas.astype(np.int64), exponents.astype(np.int16)


def decode_e2m0_state(state: EncodedE2M0State) -> np.ndarray:
    primary = from_mxfp4(
        state.primary_elements,
        state.primary_scales,
        block_size=state.block_size,
        axis=-1,
    )
    residual_m, residual_e = _decode_e2m0_integer(
        "state residual",
        state.residual_elements,
        state.residual_scales,
        state.block_size,
    )
    return (primary + _to_float32(residual_m, residual_e)).astype(np.float32)


def encode_e2m0_state(
    values: object, *, block_size: int = 32
) -> EncodedE2M0State:
    source = np.asarray(values, dtype=np.float32)
    if source.ndim != 3 or not np.all(np.isfinite(source)):
        raise ValueError("state must be finite [value_heads,key_dim,value_dim]")
    primary_elements, primary_scales = to_mxfp4(
        source, block_size=block_size, axis=-1
    )
    primary = from_mxfp4(
        primary_elements, primary_scales, block_size=block_size, axis=-1
    )
    residual_elements, residual_scales = _encode_e2m0_float(
        source - primary, block_size=block_size
    )
    return EncodedE2M0State(
        primary_elements.astype(np.uint8),
        primary_scales.astype(np.uint8),
        residual_elements,
        residual_scales,
        block_size,
    )


def encode_e2m0_token(
    q_scaled: object,
    k_normalized: object,
    v: object,
    alpha: object,
    beta: object,
    *,
    block_size: int = 32,
) -> EncodedE2M0Token:
    q = _stack_from_float(q_scaled, block_size=block_size)
    k = _stack_from_float(k_normalized, block_size=block_size)
    value = _stack_from_float(v, block_size=block_size)
    if q.elements.shape[1:] != k.elements.shape[1:] or q.elements.ndim != 3:
        raise ValueError("q and k must have matching [qk_heads,key_dim] shapes")
    if value.elements.ndim != 3 or value.elements.shape[1] % q.elements.shape[1] != 0:
        raise ValueError("value heads must be divisible by q/k heads")
    alpha_codes = encode_q1_15(alpha)
    beta_codes = encode_q1_15(beta)
    if alpha_codes.shape != value.elements.shape[1:2] or beta_codes.shape != alpha_codes.shape:
        raise ValueError("alpha and beta must have shape [value_heads]")
    return EncodedE2M0Token(q, k, value, alpha_codes, beta_codes)


def _quantize_e2m1_term(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    *,
    block_size: int,
    counters: ArithmeticCounters,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mantissa_array = np.asarray(mantissas, dtype=np.int64)
    exponent_array = np.asarray(exponents, dtype=np.int16)
    if mantissa_array.shape != exponent_array.shape or mantissa_array.ndim < 1:
        raise ValueError("exact arrays must have matching shapes")
    length = mantissa_array.shape[-1]
    blocks = (length + block_size - 1) // block_size
    elements = np.zeros(mantissa_array.shape, dtype=np.uint8)
    scales = np.full((*mantissa_array.shape[:-1], blocks), E8M0_BIAS, dtype=np.uint8)
    decoded_m = np.zeros_like(mantissa_array)
    decoded_e = np.zeros_like(exponent_array)
    for leading in np.ndindex(mantissa_array.shape[:-1]):
        for block in range(blocks):
            start = block * block_size
            stop = min(start + block_size, length)
            block_m = mantissa_array[leading + (slice(start, stop),)]
            block_e = exponent_array[leading + (slice(start, stop),)]
            scale_power = (
                0
                if np.all(block_m == 0)
                else _select_scale_power(block_m, block_e, counters)
            )
            scales[leading + (block,)] = np.uint8(scale_power + E8M0_BIAS)
            for lane in range(start, stop):
                code = _quantize_exact_e2m1(
                    int(mantissa_array[leading + (lane,)]),
                    int(exponent_array[leading + (lane,)]),
                    scale_power,
                    counters,
                )
                elements[leading + (lane,)] = np.uint8(code)
                magnitude = (0, 1, 2, 3, 4, 6, 8, 12)[code & 7]
                decoded_m[leading + (lane,)] = -magnitude if code & 8 else magnitude
                decoded_e[leading + (lane,)] = scale_power - 1
    return elements, scales, decoded_m, decoded_e


def _quantize_stack_exact(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    *,
    block_size: int,
    counters: ArithmeticCounters,
) -> EncodedMXFP4Stack:
    first_e, first_s, first_m, first_x = _quantize_e2m1_term(
        mantissas, exponents, block_size=block_size, counters=counters
    )
    residual_m = np.empty_like(np.asarray(mantissas, dtype=np.int64))
    residual_e = np.empty_like(np.asarray(exponents, dtype=np.int16))
    for index in np.ndindex(residual_m.shape):
        residual_m[index], residual_e[index] = _aligned_sum_guarded(
            np.asarray((int(mantissas[index]), -int(first_m[index])), dtype=np.int64),
            np.asarray((int(exponents[index]), int(first_x[index])), dtype=np.int32),
            counters,
        )
    second_e, second_s, _, _ = _quantize_e2m1_term(
        residual_m, residual_e, block_size=block_size, counters=counters
    )
    return EncodedMXFP4Stack(
        np.stack((first_e, second_e)),
        np.stack((first_s, second_s)),
        block_size,
    )


def _exceeds_e2m0_max(mantissa: int, exponent: int, scale_power: int) -> bool:
    if mantissa == 0:
        return False
    common = min(int(exponent), int(scale_power) - 1)
    value = abs(int(mantissa)) << (int(exponent) - common)
    maximum = 4 << (int(scale_power) - 1 - common)
    return value > maximum


def _select_e2m0_scale_power(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    counters: ArithmeticCounters,
) -> int:
    flat_m = np.asarray(mantissas, dtype=np.int64).reshape(-1)
    flat_e = np.asarray(exponents, dtype=np.int64).reshape(-1)
    best_m = 0
    best_e = 0
    for mantissa, exponent in zip(flat_m, flat_e):
        if mantissa == 0:
            continue
        if best_m == 0:
            best_m, best_e = int(mantissa), int(exponent)
            continue
        common = min(best_e, int(exponent))
        if abs(int(mantissa)) << (int(exponent) - common) > abs(best_m) << (
            best_e - common
        ):
            best_m, best_e = int(mantissa), int(exponent)
    if best_m == 0:
        return 0
    power = best_e + abs(best_m).bit_length() - 2
    if _exceeds_e2m0_max(best_m, best_e, power):
        power += 1
    if power < -127:
        counters.scale_clamps += 1
        return -127
    if power > 127:
        counters.scale_clamps += 1
        return 127
    return power


def _quantize_exact_e2m0(mantissa: int, exponent: int, scale_power: int) -> int:
    if mantissa == 0:
        return 0
    common = min(int(exponent), int(scale_power) - 1)
    source = abs(int(mantissa)) << (int(exponent) - common)
    best_index = 0
    best_distance: int | None = None
    for index, magnitude in enumerate(E2M0_INTEGER_MAGNITUDES):
        candidate = magnitude << (int(scale_power) - 1 - common)
        distance = abs(source - candidate)
        if best_distance is None or distance < best_distance or (
            distance == best_distance
            and (index & 1) == 0
            and (best_index & 1) != 0
        ):
            best_index = index
            best_distance = distance
    if best_index == 0:
        return 0
    return best_index | (4 if mantissa < 0 else 0)


def _e2m0_sse(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    scale_power: int,
    codes: np.ndarray,
) -> int:
    flat_m = np.asarray(mantissas, dtype=np.int64).reshape(-1)
    flat_e = np.asarray(exponents, dtype=np.int64).reshape(-1)
    common = min([int(scale_power) - 1, *[int(value) for value in flat_e]])
    total = 0
    for mantissa, exponent, code in zip(flat_m, flat_e, np.asarray(codes).reshape(-1)):
        source = int(mantissa) << (int(exponent) - common)
        magnitude = E2M0_INTEGER_MAGNITUDES[int(code) & 3]
        candidate = magnitude << (int(scale_power) - 1 - common)
        if int(code) & 4:
            candidate = -candidate
        error = source - candidate
        total += error * error
    return total


def _quantize_e2m0_exact(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    *,
    block_size: int,
    counters: ArithmeticCounters,
) -> tuple[np.ndarray, np.ndarray]:
    mantissa_array = np.asarray(mantissas, dtype=np.int64)
    exponent_array = np.asarray(exponents, dtype=np.int16)
    length = mantissa_array.shape[-1]
    blocks = (length + block_size - 1) // block_size
    elements = np.zeros(mantissa_array.shape, dtype=np.uint8)
    scales = np.full((*mantissa_array.shape[:-1], blocks), E8M0_BIAS, dtype=np.uint8)
    for leading in np.ndindex(mantissa_array.shape[:-1]):
        for block in range(blocks):
            start = block * block_size
            stop = min(start + block_size, length)
            block_m = mantissa_array[leading + (slice(start, stop),)]
            block_e = exponent_array[leading + (slice(start, stop),)]
            upper = _select_e2m0_scale_power(block_m, block_e, counters)
            lower = max(-127, upper - 1)
            upper_codes = np.asarray(
                [_quantize_exact_e2m0(int(m), int(e), upper) for m, e in zip(block_m, block_e)],
                dtype=np.uint8,
            )
            lower_codes = np.asarray(
                [_quantize_exact_e2m0(int(m), int(e), lower) for m, e in zip(block_m, block_e)],
                dtype=np.uint8,
            )
            choose_lower = _e2m0_sse(block_m, block_e, lower, lower_codes) < _e2m0_sse(
                block_m, block_e, upper, upper_codes
            )
            selected_power = lower if choose_lower else upper
            selected_codes = lower_codes if choose_lower else upper_codes
            if not isinstance(counters, E2M0ArithmeticCounters):
                raise TypeError("E2M0 quantization requires E2M0ArithmeticCounters")
            counters.e2m0_residual_clips += sum(
                _exceeds_e2m0_max(int(m), int(e), selected_power)
                for m, e in zip(block_m, block_e)
            )
            if np.all(selected_codes == 0):
                selected_power = 0
            elements[leading + (slice(start, stop),)] = selected_codes
            scales[leading + (block,)] = np.uint8(selected_power + E8M0_BIAS)
    return elements, scales


def _quantize_state_exact(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    *,
    block_size: int,
    counters: ArithmeticCounters,
) -> EncodedE2M0State:
    primary_e, primary_s, primary_m, primary_x = _quantize_e2m1_term(
        mantissas, exponents, block_size=block_size, counters=counters
    )
    residual_m = np.empty_like(np.asarray(mantissas, dtype=np.int64))
    residual_x = np.empty_like(np.asarray(exponents, dtype=np.int16))
    for index in np.ndindex(residual_m.shape):
        residual_m[index], residual_x[index] = _aligned_sum_guarded(
            np.asarray((int(mantissas[index]), -int(primary_m[index])), dtype=np.int64),
            np.asarray((int(exponents[index]), int(primary_x[index])), dtype=np.int32),
            counters,
        )
    residual_e, residual_s = _quantize_e2m0_exact(
        residual_m, residual_x, block_size=block_size, counters=counters
    )
    return EncodedE2M0State(
        primary_e, primary_s, residual_e, residual_s, block_size
    )


def _multiply_coefficient_codes(left: int, right: int) -> int:
    product = int(left) * int(right)
    quotient, remainder = divmod(product, COEFFICIENT_ONE)
    halfway = COEFFICIENT_ONE >> 1
    if remainder > halfway or (remainder == halfway and (quotient & 1)):
        quotient += 1
    return min(COEFFICIENT_ONE, quotient)


class EncodedE2M0WriteLogGDN:
    """Mutable resident encoded state for the fixed-capacity hardware candidate."""

    def __init__(
        self,
        initial_state: EncodedE2M0State,
        *,
        num_qk_heads: int,
        capacity: int = 7,
    ) -> None:
        if not isinstance(initial_state, EncodedE2M0State):
            raise TypeError("initial_state must be EncodedE2M0State")
        primary, primary_scales = _validate_encoded_array(
            "state primary",
            initial_state.primary_elements,
            initial_state.primary_scales,
            initial_state.block_size,
            require_canonical_zero=True,
        )
        residual, residual_scales = _validate_e2m0(
            "state residual",
            initial_state.residual_elements,
            initial_state.residual_scales,
            initial_state.block_size,
        )
        if primary.ndim != 3 or residual.shape != primary.shape:
            raise ValueError("state terms must have [value_heads,key_dim,value_dim] shape")
        self.num_value_heads, self.key_dim, self.value_dim = primary.shape
        if num_qk_heads <= 0 or self.num_value_heads % num_qk_heads:
            raise ValueError("value heads must be divisible by q/k heads")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.num_qk_heads = num_qk_heads
        self.heads_per_qk = self.num_value_heads // num_qk_heads
        self.capacity = capacity
        self.block_size = initial_state.block_size
        self.base = EncodedE2M0State(
            primary.copy(), primary_scales.copy(), residual.copy(), residual_scales.copy(), self.block_size
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
            (capacity, 2, self.num_value_heads, blocks_v), E8M0_BIAS, dtype=np.uint8
        )
        self.gamma_codes = np.full(self.num_value_heads, COEFFICIENT_ONE, dtype=np.uint16)
        self.lambda_codes = np.zeros((capacity, self.num_value_heads), dtype=np.uint16)
        self.live_entries = 0

    def _decode_base(self) -> tuple[np.ndarray, np.ndarray]:
        primary_m, primary_x = _decode_integer_arrays(
            "state primary",
            self.base.primary_elements,
            self.base.primary_scales,
            self.block_size,
            require_canonical_zero=True,
        )
        residual_m, residual_x = _decode_e2m0_integer(
            "state residual",
            self.base.residual_elements,
            self.base.residual_scales,
            self.block_size,
        )
        return np.stack((primary_m, residual_m)), np.stack((primary_x, residual_x))

    def _decoded_logs(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        key_stack = EncodedMXFP4Stack(
            self.key_elements[: self.live_entries],
            self.key_scales[: self.live_entries],
            self.block_size,
        )
        update_stack = EncodedMXFP4Stack(
            self.update_elements[: self.live_entries],
            self.update_scales[: self.live_entries],
            self.block_size,
        )
        # Stack terms are axis one in resident storage; normalize to [term,entry,...].
        key_stack = EncodedMXFP4Stack(
            np.swapaxes(key_stack.elements, 0, 1),
            np.swapaxes(key_stack.scales, 0, 1),
            self.block_size,
        )
        update_stack = EncodedMXFP4Stack(
            np.swapaxes(update_stack.elements, 0, 1),
            np.swapaxes(update_stack.scales, 0, 1),
            self.block_size,
        )
        key_m, key_x = _decode_stack_integer("log key", key_stack)
        update_m, update_x = _decode_stack_integer("log update", update_stack)
        return key_m, key_x, update_m, update_x

    def _left_action(
        self,
        vector: EncodedMXFP4Stack,
        counters: ArithmeticCounters,
    ) -> tuple[np.ndarray, np.ndarray]:
        vector_m, vector_x = _decode_stack_integer("left-action vector", vector)
        base_m, base_x = self._decode_base()
        key_m, key_x, update_m, update_x = self._decoded_logs()
        output_m = np.zeros((self.num_value_heads, self.value_dim), dtype=np.int64)
        output_x = np.zeros((self.num_value_heads, self.value_dim), dtype=np.int16)

        log_dots_m = np.zeros((self.live_entries, self.num_qk_heads), dtype=np.int64)
        log_dots_x = np.zeros((self.live_entries, self.num_qk_heads), dtype=np.int16)
        for entry in range(self.live_entries):
            for qk_head in range(self.num_qk_heads):
                terms_m: list[int] = []
                terms_x: list[int] = []
                for vector_term in range(2):
                    for key_term in range(2):
                        for row in range(self.key_dim):
                            terms_m.append(
                                int(vector_m[vector_term, qk_head, row])
                                * int(key_m[key_term, entry, qk_head, row])
                            )
                            terms_x.append(
                                int(vector_x[vector_term, qk_head, row])
                                + int(key_x[key_term, entry, qk_head, row])
                            )
                log_dots_m[entry, qk_head], log_dots_x[entry, qk_head] = _aligned_sum_guarded(
                    np.asarray(terms_m, dtype=np.int64),
                    np.asarray(terms_x, dtype=np.int32),
                    counters,
                )

        for head in range(self.num_value_heads):
            qk_head = head // self.heads_per_qk
            for value_index in range(self.value_dim):
                base_terms_m: list[int] = []
                base_terms_x: list[int] = []
                for vector_term in range(2):
                    for base_term in range(2):
                        for row in range(self.key_dim):
                            base_terms_m.append(
                                int(vector_m[vector_term, qk_head, row])
                                * int(base_m[base_term, head, row, value_index])
                            )
                            base_terms_x.append(
                                int(vector_x[vector_term, qk_head, row])
                                + int(base_x[base_term, head, row, value_index])
                            )
                base_dot_m, base_dot_x = _aligned_sum_guarded(
                    np.asarray(base_terms_m, dtype=np.int64),
                    np.asarray(base_terms_x, dtype=np.int32),
                    counters,
                )
                base_dot_m, base_dot_x = _multiply_q1_15(
                    base_dot_m, base_dot_x, int(self.gamma_codes[head]), counters
                )
                terms_m = [base_dot_m]
                terms_x = [base_dot_x]
                for entry in range(self.live_entries):
                    scaled_dot_m, scaled_dot_x = _multiply_q1_15(
                        int(log_dots_m[entry, qk_head]),
                        int(log_dots_x[entry, qk_head]),
                        int(self.lambda_codes[entry, head]),
                        counters,
                    )
                    for update_term in range(2):
                        terms_m.append(
                            scaled_dot_m
                            * int(update_m[update_term, entry, head, value_index])
                        )
                        terms_x.append(
                            scaled_dot_x
                            + int(update_x[update_term, entry, head, value_index])
                        )
                output_m[head, value_index], output_x[head, value_index] = _aligned_sum_guarded(
                    np.asarray(terms_m, dtype=np.int64),
                    np.asarray(terms_x, dtype=np.int32),
                    counters,
                )
        return output_m, output_x

    def _materialize_exact(
        self, counters: ArithmeticCounters
    ) -> tuple[np.ndarray, np.ndarray]:
        base_m, base_x = self._decode_base()
        key_m, key_x, update_m, update_x = self._decoded_logs()
        state_m = np.zeros((self.num_value_heads, self.key_dim, self.value_dim), dtype=np.int64)
        state_x = np.zeros_like(state_m, dtype=np.int16)
        for head in range(self.num_value_heads):
            qk_head = head // self.heads_per_qk
            for row in range(self.key_dim):
                for value_index in range(self.value_dim):
                    base_value_m, base_value_x = _aligned_sum_guarded(
                        base_m[:, head, row, value_index],
                        base_x[:, head, row, value_index],
                        counters,
                    )
                    base_value_m, base_value_x = _multiply_q1_15(
                        base_value_m,
                        base_value_x,
                        int(self.gamma_codes[head]),
                        counters,
                    )
                    terms_m = [base_value_m]
                    terms_x = [base_value_x]
                    for entry in range(self.live_entries):
                        rank_terms_m: list[int] = []
                        rank_terms_x: list[int] = []
                        for key_term in range(2):
                            for update_term in range(2):
                                rank_terms_m.append(
                                    int(key_m[key_term, entry, qk_head, row])
                                    * int(update_m[update_term, entry, head, value_index])
                                )
                                rank_terms_x.append(
                                    int(key_x[key_term, entry, qk_head, row])
                                    + int(update_x[update_term, entry, head, value_index])
                                )
                        rank_m, rank_x = _aligned_sum_guarded(
                            np.asarray(rank_terms_m, dtype=np.int64),
                            np.asarray(rank_terms_x, dtype=np.int32),
                            counters,
                        )
                        rank_m, rank_x = _multiply_q1_15(
                            rank_m,
                            rank_x,
                            int(self.lambda_codes[entry, head]),
                            counters,
                        )
                        terms_m.append(rank_m)
                        terms_x.append(rank_x)
                    state_m[head, row, value_index], state_x[head, row, value_index] = _aligned_sum_guarded(
                        np.asarray(terms_m, dtype=np.int64),
                        np.asarray(terms_x, dtype=np.int32),
                        counters,
                    )
        return state_m, state_x

    def materialize_state_fp32(self) -> np.ndarray:
        state = decode_e2m0_state(self.base) * (
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

    def step(self, token: EncodedE2M0Token) -> EncodedE2M0StepResult:
        if self.live_entries >= self.capacity:
            raise RuntimeError("write log is full before accepting a token")
        q_e, _ = _validate_stack("q", token.q)
        k_e, _ = _validate_stack("k", token.k)
        v_e, _ = _validate_stack("v", token.v)
        if q_e.shape[1:] != (self.num_qk_heads, self.key_dim):
            raise ValueError("q has the wrong shape")
        if k_e.shape != q_e.shape or v_e.shape[1:] != (
            self.num_value_heads,
            self.value_dim,
        ):
            raise ValueError("k or v has the wrong shape")
        alpha = np.asarray(token.alpha_codes, dtype=np.int64)
        beta = np.asarray(token.beta_codes, dtype=np.int64)
        decode_q1_15(alpha)
        decode_q1_15(beta)
        if alpha.shape != (self.num_value_heads,) or beta.shape != alpha.shape:
            raise ValueError("alpha and beta have the wrong shape")

        counters = E2M0ArithmeticCounters()
        for head in range(self.num_value_heads):
            self.gamma_codes[head] = np.uint16(
                _multiply_coefficient_codes(int(self.gamma_codes[head]), int(alpha[head]))
            )
            for entry in range(self.live_entries):
                self.lambda_codes[entry, head] = np.uint16(
                    _multiply_coefficient_codes(
                        int(self.lambda_codes[entry, head]), int(alpha[head])
                    )
                )

        prediction_m, prediction_x = self._left_action(token.k, counters)
        v_m, v_x = _decode_stack_integer("v", token.v)
        delta_m = np.zeros((self.num_value_heads, self.value_dim), dtype=np.int64)
        delta_x = np.zeros_like(delta_m, dtype=np.int16)
        for head in range(self.num_value_heads):
            for value_index in range(self.value_dim):
                residual_m, residual_x = _aligned_sum_guarded(
                    np.asarray(
                        (
                            int(v_m[0, head, value_index]),
                            int(v_m[1, head, value_index]),
                            -int(prediction_m[head, value_index]),
                        ),
                        dtype=np.int64,
                    ),
                    np.asarray(
                        (
                            int(v_x[0, head, value_index]),
                            int(v_x[1, head, value_index]),
                            int(prediction_x[head, value_index]),
                        ),
                        dtype=np.int32,
                    ),
                    counters,
                )
                delta_m[head, value_index], delta_x[head, value_index] = _multiply_q1_15(
                    residual_m, residual_x, int(beta[head]), counters
                )

        update = _quantize_stack_exact(
            delta_m, delta_x, block_size=self.block_size, counters=counters
        )
        slot = self.live_entries
        self.key_elements[slot] = token.k.elements
        self.key_scales[slot] = token.k.scales
        self.update_elements[slot] = update.elements
        self.update_scales[slot] = update.scales
        self.lambda_codes[slot].fill(COEFFICIENT_ONE)
        self.live_entries += 1

        output_m, output_x = self._left_action(token.q, counters)
        folded = self.live_entries == self.capacity
        if folded:
            state_m, state_x = self._materialize_exact(counters)
            replacement = _quantize_state_exact(
                state_m,
                state_x,
                block_size=self.block_size,
                counters=counters,
            )
            counters.state_scale_changes += int(
                np.count_nonzero(
                    replacement.primary_scales != self.base.primary_scales
                )
                + np.count_nonzero(
                    replacement.residual_scales != self.base.residual_scales
                )
            )
            self.base = replacement
            self.gamma_codes.fill(COEFFICIENT_ONE)
            self.key_elements.fill(0)
            self.key_scales.fill(E8M0_BIAS)
            self.update_elements.fill(0)
            self.update_scales.fill(E8M0_BIAS)
            self.lambda_codes.fill(0)
            self.live_entries = 0

        return EncodedE2M0StepResult(
            output_m,
            output_x,
            _to_float32(output_m, output_x),
            self.materialize_state_fp32(),
            counters,
            folded,
            self.live_entries,
        )

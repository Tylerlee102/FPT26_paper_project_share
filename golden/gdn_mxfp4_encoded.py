"""Encoded-integer MXFP4 oracle for the GDN recurrence-core boundary.

The implementation consumes E2M1 element codes, E8M0 scale bytes, and Q1.15
alpha/beta codes. Arithmetic alignment, RNE shifts, saturation, output read,
and state requantization are explicit. It does not call the FP32 recurrence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .mx_format import from_mxfp4, to_mxfp4


INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1
E8M0_BIAS = 127
E2M1_INTEGER_MAGNITUDES = (0, 1, 2, 3, 4, 6, 8, 12)


@dataclass(frozen=True)
class EncodedState:
    elements: np.ndarray
    scales: np.ndarray
    block_size: int


@dataclass(frozen=True)
class EncodedToken:
    q_elements: np.ndarray
    q_scales: np.ndarray
    k_elements: np.ndarray
    k_scales: np.ndarray
    v_elements: np.ndarray
    v_scales: np.ndarray
    alpha_codes: np.ndarray
    beta_codes: np.ndarray
    block_size: int


@dataclass
class ArithmeticCounters:
    element_saturations: int = 0
    accumulator_saturations: int = 0
    scale_clamps: int = 0
    alignment_underflows: int = 0
    state_scale_changes: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "element_saturations": self.element_saturations,
            "accumulator_saturations": self.accumulator_saturations,
            "scale_clamps": self.scale_clamps,
            "alignment_underflows": self.alignment_underflows,
            "state_scale_changes": self.state_scale_changes,
        }


@dataclass(frozen=True)
class EncodedStepResult:
    output_mantissas: np.ndarray
    output_exponents: np.ndarray
    output_fp32: np.ndarray
    state: EncodedState
    updated_mantissas: np.ndarray
    updated_exponents: np.ndarray
    counters: ArithmeticCounters


def encode_q1_15(values: object) -> np.ndarray:
    """Encode values in `[0,1]`; both endpoints are exact."""

    array = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError("Q1.15 values cannot contain NaN or Inf")
    if np.any(array < 0.0) or np.any(array > 1.0):
        raise ValueError("Q1.15 values must be in [0, 1]")
    return np.rint(array * 32768.0).astype(np.uint16)


def decode_q1_15(codes: object) -> np.ndarray:
    array = np.asarray(codes)
    if not np.issubdtype(array.dtype, np.integer):
        raise ValueError("Q1.15 codes must be integers")
    widened = array.astype(np.int64)
    if np.any(widened < 0) or np.any(widened > 32768):
        raise ValueError("valid Q1.15 codes are 0..32768")
    return (widened.astype(np.float64) / 32768.0).astype(np.float32)


def encode_state(state: object, *, block_size: int = 32) -> EncodedState:
    array = np.asarray(state, dtype=np.float32)
    if array.ndim != 3:
        raise ValueError("state must have shape [value_heads, key_dim, value_dim]")
    elements, scales = to_mxfp4(array, block_size=block_size, axis=-1)
    return EncodedState(elements, scales, block_size)


def decode_state(state: EncodedState) -> np.ndarray:
    _validate_state(state)
    return from_mxfp4(
        state.elements,
        state.scales,
        block_size=state.block_size,
        axis=-1,
    )


def encode_token(
    q_scaled: object,
    k_normalized: object,
    v: object,
    alpha: object,
    beta: object,
    *,
    block_size: int = 32,
) -> EncodedToken:
    q_array = np.asarray(q_scaled, dtype=np.float32)
    k_array = np.asarray(k_normalized, dtype=np.float32)
    v_array = np.asarray(v, dtype=np.float32)
    if q_array.ndim != 2 or k_array.shape != q_array.shape:
        raise ValueError("q_scaled and k_normalized must have matching 2-D shapes")
    if v_array.ndim != 2:
        raise ValueError("v must have shape [value_heads, value_dim]")
    if v_array.shape[0] % q_array.shape[0] != 0:
        raise ValueError("value_heads must be divisible by qk_heads")
    if not np.all(np.isfinite(q_array)) or not np.all(np.isfinite(k_array)):
        raise ValueError("q_scaled and k_normalized must be finite")
    if not np.all(np.isfinite(v_array)):
        raise ValueError("v must be finite")

    q_elements, q_scales = to_mxfp4(q_array, block_size=block_size, axis=-1)
    k_elements, k_scales = to_mxfp4(k_array, block_size=block_size, axis=-1)
    v_elements, v_scales = to_mxfp4(v_array, block_size=block_size, axis=-1)
    return EncodedToken(
        q_elements,
        q_scales,
        k_elements,
        k_scales,
        v_elements,
        v_scales,
        encode_q1_15(alpha),
        encode_q1_15(beta),
        block_size,
    )


def _expected_scale_shape(elements: np.ndarray, block_size: int) -> tuple[int, ...]:
    blocks = (elements.shape[-1] + block_size - 1) // block_size
    return (*elements.shape[:-1], blocks)


def _validate_encoded_array(
    name: str,
    elements: object,
    scales: object,
    block_size: int,
    *,
    require_canonical_zero: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    if block_size not in (16, 32):
        raise ValueError("block_size must be 16 or 32")
    element_array = np.asarray(elements)
    scale_array = np.asarray(scales)
    if element_array.ndim < 1:
        raise ValueError(f"{name} elements must have at least one dimension")
    if not np.issubdtype(element_array.dtype, np.integer):
        raise ValueError(f"{name} elements must be integer codes")
    if not np.issubdtype(scale_array.dtype, np.integer):
        raise ValueError(f"{name} scales must be integer codes")
    widened_elements = element_array.astype(np.int64)
    widened_scales = scale_array.astype(np.int64)
    if np.any(widened_elements < 0) or np.any(widened_elements > 15):
        raise ValueError(f"{name} contains an invalid E2M1 code")
    if np.any(widened_elements == 8):
        raise ValueError(f"{name} contains noncanonical negative zero")
    if scale_array.shape != _expected_scale_shape(element_array, block_size):
        raise ValueError(
            f"{name} scale shape must be {_expected_scale_shape(element_array, block_size)}, "
            f"got {scale_array.shape}"
        )
    if np.any(widened_scales < 0) or np.any(widened_scales > 254):
        raise ValueError(f"{name} contains invalid E8M0 scale code 255")
    if require_canonical_zero:
        for block in range(scale_array.shape[-1]):
            start = block * block_size
            stop = min(start + block_size, element_array.shape[-1])
            zero_block = np.all(widened_elements[..., start:stop] == 0, axis=-1)
            noncanonical_scale = widened_scales[..., block] != E8M0_BIAS
            if np.any(zero_block & noncanonical_scale):
                raise ValueError(
                    f"{name} contains an all-zero block with noncanonical scale"
                )
    return element_array.astype(np.uint8), scale_array.astype(np.uint8)


def _validate_state(state: EncodedState) -> tuple[np.ndarray, np.ndarray]:
    elements, scales = _validate_encoded_array(
        "state",
        state.elements,
        state.scales,
        state.block_size,
        require_canonical_zero=True,
    )
    if elements.ndim != 3:
        raise ValueError("state elements must have K-by-V shape [value_heads, key_dim, value_dim]")
    return elements, scales


def _decode_integer_arrays(
    name: str,
    elements: object,
    scales: object,
    block_size: int,
    *,
    require_canonical_zero: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    element_array, scale_array = _validate_encoded_array(
        name,
        elements,
        scales,
        block_size,
        require_canonical_zero=require_canonical_zero,
    )
    magnitude_code = element_array & np.uint8(0x07)
    magnitude_table = np.asarray(E2M1_INTEGER_MAGNITUDES, dtype=np.int64)
    mantissas = magnitude_table[magnitude_code]
    signs = np.where((element_array & np.uint8(0x08)) != 0, -1, 1).astype(np.int64)
    mantissas = mantissas * signs

    expanded_scales = np.repeat(scale_array, block_size, axis=-1)[
        ..., : element_array.shape[-1]
    ]
    # E2M1 magnitude integer r decodes as r/2, hence scale_code - 128.
    exponents = expanded_scales.astype(np.int16) - np.int16(E8M0_BIAS + 1)
    return mantissas.astype(np.int64), exponents.astype(np.int16)


def _round_shift_rne(value: int, shift: int) -> int:
    if shift <= 0:
        return value << (-shift)
    if value == 0:
        return 0
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    quotient, remainder = divmod(magnitude, 1 << shift)
    halfway = 1 << (shift - 1)
    if remainder > halfway or (remainder == halfway and (quotient & 1) != 0):
        quotient += 1
    return sign * quotient


def _saturate_int32(value: int, counters: ArithmeticCounters) -> int:
    if value > INT32_MAX:
        counters.accumulator_saturations += 1
        return INT32_MAX
    if value < INT32_MIN:
        counters.accumulator_saturations += 1
        return INT32_MIN
    return value


def _aligned_sum(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    counters: ArithmeticCounters,
) -> tuple[int, int]:
    flat_mantissas = np.asarray(mantissas, dtype=np.int64).reshape(-1)
    flat_exponents = np.asarray(exponents, dtype=np.int64).reshape(-1)
    nonzero = flat_mantissas != 0
    if not np.any(nonzero):
        return 0, 0
    target_exponent = int(np.max(flat_exponents[nonzero]))
    total = 0
    for mantissa, exponent in zip(flat_mantissas, flat_exponents):
        raw = int(mantissa)
        if raw == 0:
            continue
        aligned = _round_shift_rne(raw, target_exponent - int(exponent))
        if aligned == 0 and raw != 0 and target_exponent > int(exponent):
            counters.alignment_underflows += 1
        total = _saturate_int32(total + aligned, counters)
    return total, target_exponent


def _multiply_q1_15(
    mantissa: int,
    exponent: int,
    code: int,
    counters: ArithmeticCounters,
) -> tuple[int, int]:
    if code < 0 or code > 32768:
        raise ValueError("valid Q1.15 codes are 0..32768")
    product = int(mantissa) * int(code)
    rounded = _round_shift_rne(product, 15)
    return _saturate_int32(rounded, counters), int(exponent)


def _greater_abs(
    left_mantissa: int,
    left_exponent: int,
    right_mantissa: int,
    right_exponent: int,
) -> bool:
    left = abs(int(left_mantissa))
    right = abs(int(right_mantissa))
    if right == 0:
        return left != 0
    if left == 0:
        return False
    common = min(int(left_exponent), int(right_exponent))
    return (left << (int(left_exponent) - common)) > (
        right << (int(right_exponent) - common)
    )


def _exceeds_e2m1_max(mantissa: int, exponent: int, scale_power: int) -> bool:
    magnitude = abs(int(mantissa))
    if magnitude == 0:
        return False
    element_exponent = int(scale_power) - 1
    common = min(int(exponent), element_exponent)
    value_integer = magnitude << (int(exponent) - common)
    max_integer = 12 << (element_exponent - common)
    return value_integer > max_integer


def _select_scale_power(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    counters: ArithmeticCounters,
) -> int:
    flat_mantissas = np.asarray(mantissas, dtype=np.int64).reshape(-1)
    flat_exponents = np.asarray(exponents, dtype=np.int64).reshape(-1)
    max_mantissa = 0
    max_exponent = 0
    for mantissa, exponent in zip(flat_mantissas, flat_exponents):
        if _greater_abs(int(mantissa), int(exponent), max_mantissa, max_exponent):
            max_mantissa = int(mantissa)
            max_exponent = int(exponent)
    if max_mantissa == 0:
        return 0

    # Smallest s for which abs(value) <= 6 * 2**s.
    scale_power = max_exponent + abs(max_mantissa).bit_length() - 3
    if _exceeds_e2m1_max(max_mantissa, max_exponent, scale_power):
        scale_power += 1
    if scale_power < -127:
        counters.scale_clamps += 1
        return -127
    if scale_power > 127:
        counters.scale_clamps += 1
        return 127
    return scale_power


def _quantize_exact_e2m1(
    mantissa: int,
    exponent: int,
    scale_power: int,
    counters: ArithmeticCounters,
) -> int:
    if mantissa == 0:
        return 0
    sign_bit = 0x08 if mantissa < 0 else 0
    magnitude = abs(int(mantissa))
    element_exponent = int(scale_power) - 1
    common = min(int(exponent), element_exponent)
    value_integer = magnitude << (int(exponent) - common)

    best_code = 0
    best_distance: int | None = None
    for code, candidate_magnitude in enumerate(E2M1_INTEGER_MAGNITUDES):
        candidate_integer = int(candidate_magnitude) << (element_exponent - common)
        distance = abs(value_integer - candidate_integer)
        if best_distance is None or distance < best_distance:
            best_code = code
            best_distance = distance
        elif distance == best_distance and (code & 1) == 0 and (best_code & 1) != 0:
            best_code = code

    if _exceeds_e2m1_max(mantissa, exponent, scale_power):
        counters.element_saturations += 1
        best_code = 7
    if best_code == 0:
        return 0
    return sign_bit | best_code


def _requantize_state(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    previous_scales: np.ndarray,
    block_size: int,
    counters: ArithmeticCounters,
) -> EncodedState:
    value_heads, key_dim, value_dim = mantissas.shape
    blocks = (value_dim + block_size - 1) // block_size
    elements = np.zeros((value_heads, key_dim, value_dim), dtype=np.uint8)
    scales = np.empty((value_heads, key_dim, blocks), dtype=np.uint8)
    for head in range(value_heads):
        for key_index in range(key_dim):
            for block in range(blocks):
                start = block * block_size
                stop = min(start + block_size, value_dim)
                block_mantissas = mantissas[head, key_index, start:stop]
                block_exponents = exponents[head, key_index, start:stop]
                if np.all(block_mantissas == 0):
                    scale_power = 0
                else:
                    scale_power = _select_scale_power(
                        block_mantissas, block_exponents, counters
                    )
                scale_code = scale_power + E8M0_BIAS
                scales[head, key_index, block] = np.uint8(scale_code)
                if int(previous_scales[head, key_index, block]) != scale_code:
                    counters.state_scale_changes += 1
                for value_index in range(start, stop):
                    elements[head, key_index, value_index] = np.uint8(
                        _quantize_exact_e2m1(
                            int(mantissas[head, key_index, value_index]),
                            int(exponents[head, key_index, value_index]),
                            scale_power,
                            counters,
                        )
                    )
    return EncodedState(elements, scales, block_size)


def _to_float32(mantissas: np.ndarray, exponents: np.ndarray) -> np.ndarray:
    values = np.ldexp(
        np.asarray(mantissas, dtype=np.float64),
        np.asarray(exponents, dtype=np.int32),
    )
    return values.astype(np.float32)


def recurrence_core_step_encoded(
    token: EncodedToken,
    state: EncodedState,
) -> EncodedStepResult:
    """Execute one token with the frozen encoded arithmetic contract."""

    if token.block_size != state.block_size:
        raise ValueError("token and state block sizes must match")
    block_size = token.block_size
    q_mantissas, q_exponents = _decode_integer_arrays(
        "q",
        token.q_elements,
        token.q_scales,
        block_size,
        require_canonical_zero=True,
    )
    k_mantissas, k_exponents = _decode_integer_arrays(
        "k",
        token.k_elements,
        token.k_scales,
        block_size,
        require_canonical_zero=True,
    )
    v_mantissas, v_exponents = _decode_integer_arrays(
        "v",
        token.v_elements,
        token.v_scales,
        block_size,
        require_canonical_zero=True,
    )
    state_elements, state_scales = _validate_state(state)
    state_mantissas, state_exponents = _decode_integer_arrays(
        "state",
        state_elements,
        state_scales,
        block_size,
        require_canonical_zero=True,
    )
    alpha_codes = np.asarray(token.alpha_codes, dtype=np.int64)
    beta_codes = np.asarray(token.beta_codes, dtype=np.int64)
    decode_q1_15(alpha_codes)
    decode_q1_15(beta_codes)

    if q_mantissas.ndim != 2 or k_mantissas.shape != q_mantissas.shape:
        raise ValueError("q and k encoded tensors must have matching 2-D shapes")
    if v_mantissas.ndim != 2:
        raise ValueError("v encoded tensor must be 2-D")
    qk_heads, key_dim = q_mantissas.shape
    value_heads, value_dim = v_mantissas.shape
    if value_heads % qk_heads != 0:
        raise ValueError("value_heads must be divisible by qk_heads")
    if state_mantissas.shape != (value_heads, key_dim, value_dim):
        raise ValueError("encoded state must have K-by-V shape")
    if alpha_codes.shape != (value_heads,) or beta_codes.shape != (value_heads,):
        raise ValueError("alpha and beta codes must have shape [value_heads]")

    counters = ArithmeticCounters()
    heads_per_qk = value_heads // qk_heads

    decayed_mantissas = np.empty_like(state_mantissas, dtype=np.int64)
    decayed_exponents = state_exponents.copy()
    for head in range(value_heads):
        for key_index in range(key_dim):
            for value_index in range(value_dim):
                decayed_mantissas[head, key_index, value_index], _ = _multiply_q1_15(
                    int(state_mantissas[head, key_index, value_index]),
                    int(state_exponents[head, key_index, value_index]),
                    int(alpha_codes[head]),
                    counters,
                )

    prediction_mantissas = np.empty((value_heads, value_dim), dtype=np.int64)
    prediction_exponents = np.empty((value_heads, value_dim), dtype=np.int16)
    for head in range(value_heads):
        qk_head = head // heads_per_qk
        for value_index in range(value_dim):
            term_mantissas = (
                k_mantissas[qk_head] * decayed_mantissas[head, :, value_index]
            )
            term_exponents = (
                k_exponents[qk_head].astype(np.int32)
                + decayed_exponents[head, :, value_index].astype(np.int32)
            )
            mantissa, exponent = _aligned_sum(
                term_mantissas, term_exponents, counters
            )
            prediction_mantissas[head, value_index] = mantissa
            prediction_exponents[head, value_index] = exponent

    delta_mantissas = np.empty((value_heads, value_dim), dtype=np.int64)
    delta_exponents = np.empty((value_heads, value_dim), dtype=np.int16)
    for head in range(value_heads):
        for value_index in range(value_dim):
            residual_mantissa, residual_exponent = _aligned_sum(
                np.array(
                    [
                        int(v_mantissas[head, value_index]),
                        -int(prediction_mantissas[head, value_index]),
                    ],
                    dtype=np.int64,
                ),
                np.array(
                    [
                        int(v_exponents[head, value_index]),
                        int(prediction_exponents[head, value_index]),
                    ],
                    dtype=np.int32,
                ),
                counters,
            )
            delta_mantissa, delta_exponent = _multiply_q1_15(
                residual_mantissa,
                residual_exponent,
                int(beta_codes[head]),
                counters,
            )
            delta_mantissas[head, value_index] = delta_mantissa
            delta_exponents[head, value_index] = delta_exponent

    updated_mantissas = np.empty_like(state_mantissas, dtype=np.int64)
    updated_exponents = np.empty_like(state_exponents, dtype=np.int16)
    for head in range(value_heads):
        qk_head = head // heads_per_qk
        for key_index in range(key_dim):
            for value_index in range(value_dim):
                write_mantissa = int(k_mantissas[qk_head, key_index]) * int(
                    delta_mantissas[head, value_index]
                )
                write_exponent = int(k_exponents[qk_head, key_index]) + int(
                    delta_exponents[head, value_index]
                )
                mantissa, exponent = _aligned_sum(
                    np.array(
                        [
                            int(decayed_mantissas[head, key_index, value_index]),
                            write_mantissa,
                        ],
                        dtype=np.int64,
                    ),
                    np.array(
                        [
                            int(decayed_exponents[head, key_index, value_index]),
                            write_exponent,
                        ],
                        dtype=np.int32,
                    ),
                    counters,
                )
                updated_mantissas[head, key_index, value_index] = mantissa
                updated_exponents[head, key_index, value_index] = exponent

    # Official ordering reads output from the updated arithmetic state before
    # the persistent-state requantization boundary.
    output_mantissas = np.empty((value_heads, value_dim), dtype=np.int64)
    output_exponents = np.empty((value_heads, value_dim), dtype=np.int16)
    for head in range(value_heads):
        qk_head = head // heads_per_qk
        for value_index in range(value_dim):
            term_mantissas = (
                q_mantissas[qk_head] * updated_mantissas[head, :, value_index]
            )
            term_exponents = (
                q_exponents[qk_head].astype(np.int32)
                + updated_exponents[head, :, value_index].astype(np.int32)
            )
            mantissa, exponent = _aligned_sum(
                term_mantissas, term_exponents, counters
            )
            output_mantissas[head, value_index] = mantissa
            output_exponents[head, value_index] = exponent

    state_out = _requantize_state(
        updated_mantissas,
        updated_exponents,
        state_scales,
        block_size,
        counters,
    )
    return EncodedStepResult(
        output_mantissas=output_mantissas,
        output_exponents=output_exponents,
        output_fp32=_to_float32(output_mantissas, output_exponents),
        state=state_out,
        updated_mantissas=updated_mantissas,
        updated_exponents=updated_exponents,
        counters=counters,
    )

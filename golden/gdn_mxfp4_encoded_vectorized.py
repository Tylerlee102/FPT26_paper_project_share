"""Vectorized execution of the frozen encoded-integer MXFP4 contract.

The scalar implementation in :mod:`golden.gdn_mxfp4_encoded` remains the
authoritative oracle. This module preserves its reduction order, RNE behavior,
per-add INT32 saturation, scale selection, and state-write boundary while
vectorizing independent heads, rows, and columns for long-trace diagnostics.
"""

from __future__ import annotations

import numpy as np

from .gdn_mxfp4_encoded import (
    E8M0_BIAS,
    INT32_MAX,
    INT32_MIN,
    ArithmeticCounters,
    EncodedState,
    EncodedStepResult,
    EncodedToken,
    _decode_integer_arrays,
    _to_float32,
    _validate_state,
    decode_q1_15,
)


def _round_shift_rne_array(values: np.ndarray, shifts: np.ndarray) -> np.ndarray:
    """Round signed integers after nonnegative right shifts using RNE."""

    value_array, shift_array = np.broadcast_arrays(
        np.asarray(values, dtype=np.int64),
        np.asarray(shifts, dtype=np.int64),
    )
    if np.any(shift_array < 0):
        raise ValueError("vectorized RNE shifts must be nonnegative")

    result = np.zeros(value_array.shape, dtype=np.int64)
    no_shift = shift_array == 0
    result[no_shift] = value_array[no_shift]

    # Every arithmetic value in this contract has magnitude below 2**63.
    # A right shift of 63 or more therefore rounds to zero, including the
    # exact halfway case whose zero quotient is even.
    active = (shift_array > 0) & (shift_array < 63) & (value_array != 0)
    if not np.any(active):
        return result

    active_values = value_array[active]
    active_shifts = shift_array[active]
    magnitudes = np.abs(active_values)
    quotients = np.right_shift(magnitudes, active_shifts)
    remainders = magnitudes - np.left_shift(quotients, active_shifts)
    halfway = np.left_shift(np.ones_like(active_shifts), active_shifts - 1)
    round_up = (remainders > halfway) | (
        (remainders == halfway) & ((quotients & 1) != 0)
    )
    rounded = quotients + round_up.astype(np.int64)
    result[active] = np.where(active_values < 0, -rounded, rounded)
    return result


def _saturate_int32_array(
    values: np.ndarray,
    counters: ArithmeticCounters,
) -> np.ndarray:
    value_array = np.asarray(values, dtype=np.int64)
    saturated = (value_array > INT32_MAX) | (value_array < INT32_MIN)
    counters.accumulator_saturations += int(np.count_nonzero(saturated))
    return np.clip(value_array, INT32_MIN, INT32_MAX).astype(np.int64)


def _multiply_q1_15_array(
    mantissas: np.ndarray,
    codes: np.ndarray,
    counters: ArithmeticCounters,
) -> np.ndarray:
    products = np.asarray(mantissas, dtype=np.int64) * np.asarray(
        codes, dtype=np.int64
    )
    rounded = _round_shift_rne_array(products, np.int64(15))
    return _saturate_int32_array(rounded, counters)


def _aligned_sum_last(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    counters: ArithmeticCounters,
) -> tuple[np.ndarray, np.ndarray]:
    """Align and reduce the final axis in scalar-oracle term order."""

    mantissa_array = np.asarray(mantissas, dtype=np.int64)
    exponent_array = np.asarray(exponents, dtype=np.int32)
    if mantissa_array.shape != exponent_array.shape or mantissa_array.ndim < 1:
        raise ValueError("aligned arrays must have one matching reduction axis")

    nonzero = mantissa_array != 0
    all_zero = ~np.any(nonzero, axis=-1)
    target = np.max(
        np.where(nonzero, exponent_array, np.iinfo(np.int32).min), axis=-1
    )
    target = np.where(all_zero, 0, target).astype(np.int32)
    total = np.zeros(target.shape, dtype=np.int64)

    # Keep the scalar oracle's left-to-right saturation semantics. The Python
    # loop is only over the reduction dimension; all independent reductions
    # execute as arrays.
    for index in range(mantissa_array.shape[-1]):
        raw = mantissa_array[..., index]
        shifts = target.astype(np.int64) - exponent_array[..., index].astype(
            np.int64
        )
        # The scalar oracle skips zero terms before inspecting their exponent.
        # Canonical zero blocks can therefore carry an exponent above the
        # selected nonzero target without implying a left shift.
        shifts = np.where(raw == 0, 0, shifts)
        aligned = _round_shift_rne_array(raw, shifts)
        counters.alignment_underflows += int(
            np.count_nonzero((raw != 0) & (shifts > 0) & (aligned == 0))
        )
        total = _saturate_int32_array(total + aligned, counters)
    return total, target.astype(np.int16)


def _block_scale_powers(
    block_mantissas: np.ndarray,
    block_exponents: np.ndarray,
    counters: ArithmeticCounters,
) -> np.ndarray:
    """Select the scalar oracle's smallest non-overflowing E8M0 scale."""

    absolute = np.abs(np.asarray(block_mantissas, dtype=np.int64))
    exponents = np.asarray(block_exponents, dtype=np.int32)
    represented = np.ldexp(absolute.astype(np.float64), exponents)
    max_indices = np.argmax(represented, axis=-1)[..., np.newaxis]
    max_mantissas = np.take_along_axis(absolute, max_indices, axis=-1)[..., 0]
    max_exponents = np.take_along_axis(exponents, max_indices, axis=-1)[..., 0]
    zero_blocks = max_mantissas == 0

    bit_lengths = np.zeros(max_mantissas.shape, dtype=np.int32)
    nonzero = ~zero_blocks
    if np.any(nonzero):
        bit_lengths[nonzero] = (
            np.floor(np.log2(max_mantissas[nonzero].astype(np.float64))).astype(
                np.int32
            )
            + 1
        )
    powers = max_exponents + bit_lengths - 3
    represented_max = np.ldexp(
        max_mantissas.astype(np.float64), max_exponents
    )
    representable_limit = np.ldexp(
        np.full(powers.shape, 12.0, dtype=np.float64), powers - 1
    )
    powers = powers + ((represented_max > representable_limit) & nonzero)
    powers = np.where(zero_blocks, 0, powers)

    below = nonzero & (powers < -127)
    above = nonzero & (powers > 127)
    counters.scale_clamps += int(np.count_nonzero(below | above))
    return np.clip(powers, -127, 127).astype(np.int32)


def _requantize_state_vectorized(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    previous_scales: np.ndarray,
    block_size: int,
    counters: ArithmeticCounters,
) -> EncodedState:
    value_heads, key_dim, value_dim = mantissas.shape
    blocks = (value_dim + block_size - 1) // block_size
    padded_value_dim = blocks * block_size
    pad = padded_value_dim - value_dim
    if pad:
        block_mantissas = np.pad(mantissas, ((0, 0), (0, 0), (0, pad)))
        block_exponents = np.pad(exponents, ((0, 0), (0, 0), (0, pad)))
    else:
        block_mantissas = np.asarray(mantissas)
        block_exponents = np.asarray(exponents)
    block_mantissas = block_mantissas.reshape(
        value_heads, key_dim, blocks, block_size
    ).astype(np.int64)
    block_exponents = block_exponents.reshape(
        value_heads, key_dim, blocks, block_size
    ).astype(np.int32)

    scale_powers = _block_scale_powers(
        block_mantissas, block_exponents, counters
    )
    scale_codes = (scale_powers + E8M0_BIAS).astype(np.uint8)
    counters.state_scale_changes += int(
        np.count_nonzero(
            np.asarray(previous_scales, dtype=np.uint8) != scale_codes
        )
    )

    absolute = np.abs(block_mantissas)
    relative = np.ldexp(
        absolute.astype(np.float64),
        block_exponents - (scale_powers[..., np.newaxis] - 1),
    )
    codes = np.zeros(relative.shape, dtype=np.uint8)
    # Midpoint ties select the even E2M1 code, matching the scalar loop.
    codes = np.where(relative > 0.5, 1, codes)
    codes = np.where(relative >= 1.5, 2, codes)
    codes = np.where(relative > 2.5, 3, codes)
    codes = np.where(relative >= 3.5, 4, codes)
    codes = np.where(relative > 5.0, 5, codes)
    codes = np.where(relative >= 7.0, 6, codes)
    codes = np.where(relative > 10.0, 7, codes).astype(np.uint8)
    saturated = relative > 12.0
    counters.element_saturations += int(np.count_nonzero(saturated))
    codes[saturated] = np.uint8(7)
    sign = np.where(block_mantissas < 0, np.uint8(0x08), np.uint8(0))
    codes = np.where(codes == 0, np.uint8(0), codes | sign).astype(np.uint8)
    elements = codes.reshape(value_heads, key_dim, padded_value_dim)[
        ..., :value_dim
    ]
    return EncodedState(elements, scale_codes, block_size)


def recurrence_core_step_encoded_vectorized(
    token: EncodedToken,
    state: EncodedState,
) -> EncodedStepResult:
    """Execute one frozen-contract token with vectorized independent work."""

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
    qk_for_value_head = np.arange(value_heads) // heads_per_qk

    decayed_mantissas = _multiply_q1_15_array(
        state_mantissas,
        alpha_codes[:, np.newaxis, np.newaxis],
        counters,
    )
    decayed_exponents = state_exponents.astype(np.int16, copy=True)

    prediction_terms = (
        k_mantissas[qk_for_value_head, :, np.newaxis] * decayed_mantissas
    )
    prediction_term_exponents = (
        k_exponents[qk_for_value_head, :, np.newaxis].astype(np.int32)
        + decayed_exponents.astype(np.int32)
    )
    prediction_mantissas, prediction_exponents = _aligned_sum_last(
        np.swapaxes(prediction_terms, 1, 2),
        np.swapaxes(prediction_term_exponents, 1, 2),
        counters,
    )

    residual_mantissas, residual_exponents = _aligned_sum_last(
        np.stack((v_mantissas, -prediction_mantissas), axis=-1),
        np.stack((v_exponents, prediction_exponents), axis=-1),
        counters,
    )
    delta_mantissas = _multiply_q1_15_array(
        residual_mantissas,
        beta_codes[:, np.newaxis],
        counters,
    )
    delta_exponents = residual_exponents

    write_mantissas = (
        k_mantissas[qk_for_value_head, :, np.newaxis]
        * delta_mantissas[:, np.newaxis, :]
    )
    write_exponents = (
        k_exponents[qk_for_value_head, :, np.newaxis].astype(np.int32)
        + delta_exponents[:, np.newaxis, :].astype(np.int32)
    )
    updated_mantissas, updated_exponents = _aligned_sum_last(
        np.stack((decayed_mantissas, write_mantissas), axis=-1),
        np.stack(
            (decayed_exponents.astype(np.int32), write_exponents), axis=-1
        ),
        counters,
    )

    output_terms = (
        q_mantissas[qk_for_value_head, :, np.newaxis] * updated_mantissas
    )
    output_term_exponents = (
        q_exponents[qk_for_value_head, :, np.newaxis].astype(np.int32)
        + updated_exponents.astype(np.int32)
    )
    output_mantissas, output_exponents = _aligned_sum_last(
        np.swapaxes(output_terms, 1, 2),
        np.swapaxes(output_term_exponents, 1, 2),
        counters,
    )

    state_out = _requantize_state_vectorized(
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

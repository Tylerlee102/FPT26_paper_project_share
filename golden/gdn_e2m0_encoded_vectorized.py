"""Vectorized executor for the scalar E2M0 write-log encoded oracle.

The scalar implementation remains authoritative.  This module preserves its
term order and per-add INT32 saturation while vectorizing independent heads,
rows, and columns for long synthetic traces.
"""

from __future__ import annotations

import numpy as np

from .gdn_e2m0_encoded import (
    ACCUMULATOR_GUARD_BITS,
    COEFFICIENT_ONE,
    E2M0_INTEGER_MAGNITUDES,
    E2M0ArithmeticCounters,
    EncodedE2M0State,
    EncodedE2M0StepResult,
    EncodedE2M0Token,
    EncodedE2M0WriteLogGDN,
    EncodedMXFP4Stack,
    _decode_e2m0_integer,
    _decode_stack_integer,
    _to_float32,
    _validate_stack,
)
from .gdn_mxfp4_encoded import E8M0_BIAS, ArithmeticCounters, decode_q1_15
from .gdn_mxfp4_encoded_vectorized import (
    _block_scale_powers,
    _multiply_q1_15_array,
    _round_shift_rne_array,
    _saturate_int32_array,
)


E2M1_INTEGER_MAGNITUDES = np.asarray(
    (0, 1, 2, 3, 4, 6, 8, 12), dtype=np.int64
)


def _aligned_sum_last_guarded(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    counters: ArithmeticCounters,
) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized form of the scalar guard-5 INT32 reduction."""

    mantissa_array = np.asarray(mantissas, dtype=np.int64)
    exponent_array = np.asarray(exponents, dtype=np.int32)
    if mantissa_array.shape != exponent_array.shape or mantissa_array.ndim < 1:
        raise ValueError("aligned arrays must have one matching reduction axis")
    nonzero = mantissa_array != 0
    all_zero = ~np.any(nonzero, axis=-1)
    dominant = np.max(
        np.where(nonzero, exponent_array, np.iinfo(np.int32).min), axis=-1
    )
    target = np.where(
        all_zero, 0, dominant - ACCUMULATOR_GUARD_BITS
    ).astype(np.int32)
    total = np.zeros(target.shape, dtype=np.int64)
    for index in range(mantissa_array.shape[-1]):
        raw = mantissa_array[..., index]
        shifts = target.astype(np.int64) - exponent_array[..., index].astype(
            np.int64
        )
        shifts = np.where(raw == 0, 0, shifts)
        aligned = np.zeros(raw.shape, dtype=np.int64)
        right = shifts >= 0
        if np.any(right):
            aligned[right] = _round_shift_rne_array(raw[right], shifts[right])
        left = ~right
        if np.any(left):
            aligned[left] = np.left_shift(raw[left], -shifts[left])
        counters.alignment_underflows += int(
            np.count_nonzero((raw != 0) & (shifts > 0) & (aligned == 0))
        )
        total = _saturate_int32_array(total + aligned, counters)
    return total, target.astype(np.int16)


def _reshape_blocks(
    values: np.ndarray, block_size: int
) -> tuple[np.ndarray, int, int]:
    length = values.shape[-1]
    blocks = (length + block_size - 1) // block_size
    padded_length = blocks * block_size
    if padded_length != length:
        pad = [(0, 0)] * values.ndim
        pad[-1] = (0, padded_length - length)
        values = np.pad(values, pad)
    return values.reshape(*values.shape[:-1], blocks, block_size), length, padded_length


def _quantize_e2m1_term_vectorized(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    *,
    block_size: int,
    counters: ArithmeticCounters,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mantissa_array = np.asarray(mantissas, dtype=np.int64)
    exponent_array = np.asarray(exponents, dtype=np.int32)
    if mantissa_array.shape != exponent_array.shape:
        raise ValueError("exact arrays must have matching shapes")
    block_m, length, padded_length = _reshape_blocks(mantissa_array, block_size)
    block_x, _, _ = _reshape_blocks(exponent_array, block_size)
    powers = _block_scale_powers(block_m, block_x, counters)
    relative = np.ldexp(
        np.abs(block_m).astype(np.float64),
        block_x - (powers[..., np.newaxis] - 1),
    )
    indices = np.zeros(relative.shape, dtype=np.uint8)
    indices = np.where(relative > 0.5, 1, indices)
    indices = np.where(relative >= 1.5, 2, indices)
    indices = np.where(relative > 2.5, 3, indices)
    indices = np.where(relative >= 3.5, 4, indices)
    indices = np.where(relative > 5.0, 5, indices)
    indices = np.where(relative >= 7.0, 6, indices)
    indices = np.where(relative > 10.0, 7, indices).astype(np.uint8)
    saturated = relative > 12.0
    counters.element_saturations += int(np.count_nonzero(saturated))
    indices[saturated] = np.uint8(7)
    sign = np.where(block_m < 0, np.uint8(8), np.uint8(0))
    codes = np.where(indices == 0, np.uint8(0), indices | sign).astype(np.uint8)
    decoded_m = E2M1_INTEGER_MAGNITUDES[indices]
    decoded_m = np.where(sign != 0, -decoded_m, decoded_m).astype(np.int64)
    decoded_x = np.broadcast_to(
        (powers - 1)[..., np.newaxis], block_m.shape
    ).astype(np.int16)
    flat_shape = (*mantissa_array.shape[:-1], padded_length)
    elements = codes.reshape(flat_shape)[..., :length]
    decoded_m = decoded_m.reshape(flat_shape)[..., :length]
    decoded_x = decoded_x.reshape(flat_shape)[..., :length]
    scales = (powers + E8M0_BIAS).astype(np.uint8)
    return elements, scales, decoded_m, decoded_x


def _quantize_stack_exact_vectorized(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    *,
    block_size: int,
    counters: ArithmeticCounters,
) -> EncodedMXFP4Stack:
    first_e, first_s, first_m, first_x = _quantize_e2m1_term_vectorized(
        mantissas, exponents, block_size=block_size, counters=counters
    )
    residual_m, residual_x = _aligned_sum_last_guarded(
        np.stack((np.asarray(mantissas), -first_m), axis=-1),
        np.stack((np.asarray(exponents), first_x), axis=-1),
        counters,
    )
    second_e, second_s, _, _ = _quantize_e2m1_term_vectorized(
        residual_m, residual_x, block_size=block_size, counters=counters
    )
    return EncodedMXFP4Stack(
        np.stack((first_e, second_e)),
        np.stack((first_s, second_s)),
        block_size,
    )


def _e2m0_scale_powers(
    block_m: np.ndarray,
    block_x: np.ndarray,
    counters: ArithmeticCounters,
) -> np.ndarray:
    absolute = np.abs(np.asarray(block_m, dtype=np.int64))
    exponents = np.asarray(block_x, dtype=np.int32)
    represented = np.ldexp(absolute.astype(np.float64), exponents)
    maximum_indices = np.argmax(represented, axis=-1)[..., np.newaxis]
    maximum_m = np.take_along_axis(absolute, maximum_indices, axis=-1)[..., 0]
    maximum_x = np.take_along_axis(exponents, maximum_indices, axis=-1)[..., 0]
    zero = maximum_m == 0
    bit_lengths = np.zeros(maximum_m.shape, dtype=np.int32)
    active = ~zero
    bit_lengths[active] = (
        np.floor(np.log2(maximum_m[active].astype(np.float64))).astype(np.int32)
        + 1
    )
    powers = maximum_x + bit_lengths - 2
    limit = np.ldexp(np.full(powers.shape, 4.0), powers - 1)
    powers += ((represented.max(axis=-1) > limit) & active).astype(np.int32)
    powers = np.where(zero, 0, powers)
    clamped = active & ((powers < -127) | (powers > 127))
    counters.scale_clamps += int(np.count_nonzero(clamped))
    return np.clip(powers, -127, 127).astype(np.int32)


def _e2m0_codes_at_power(
    block_m: np.ndarray,
    block_x: np.ndarray,
    powers: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    relative = np.ldexp(
        np.abs(block_m).astype(np.float64),
        block_x - (powers[..., np.newaxis] - 1),
    )
    indices = np.zeros(relative.shape, dtype=np.uint8)
    indices = np.where(relative > 0.5, 1, indices)
    indices = np.where(relative >= 1.5, 2, indices)
    indices = np.where(relative > 3.0, 3, indices).astype(np.uint8)
    sign = np.where(block_m < 0, np.uint8(4), np.uint8(0))
    codes = np.where(indices == 0, np.uint8(0), indices | sign).astype(np.uint8)
    signed = np.asarray(E2M0_INTEGER_MAGNITUDES, dtype=np.float64)[indices]
    signed = np.where(sign != 0, -signed, signed)
    reconstructed = np.ldexp(signed, powers[..., np.newaxis] - 1)
    source = np.ldexp(block_m.astype(np.float64), block_x)
    squared_error = np.sum((source - reconstructed) ** 2, axis=-1)
    return codes, squared_error, relative


def _quantize_e2m0_exact_vectorized(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    *,
    block_size: int,
    counters: ArithmeticCounters,
) -> tuple[np.ndarray, np.ndarray]:
    mantissa_array = np.asarray(mantissas, dtype=np.int64)
    exponent_array = np.asarray(exponents, dtype=np.int32)
    block_m, length, padded_length = _reshape_blocks(mantissa_array, block_size)
    block_x, _, _ = _reshape_blocks(exponent_array, block_size)
    upper = _e2m0_scale_powers(block_m, block_x, counters)
    lower = np.maximum(upper - 1, -127)
    upper_codes, upper_error, upper_relative = _e2m0_codes_at_power(
        block_m, block_x, upper
    )
    lower_codes, lower_error, lower_relative = _e2m0_codes_at_power(
        block_m, block_x, lower
    )
    choose_lower = lower_error < upper_error
    codes = np.where(choose_lower[..., np.newaxis], lower_codes, upper_codes)
    powers = np.where(choose_lower, lower, upper)
    selected_relative = np.where(
        choose_lower[..., np.newaxis], lower_relative, upper_relative
    )
    if not isinstance(counters, E2M0ArithmeticCounters):
        raise TypeError("E2M0 quantization requires E2M0ArithmeticCounters")
    counters.e2m0_residual_clips += int(
        np.count_nonzero(selected_relative > 4.0)
    )
    zero = np.all(codes == 0, axis=-1)
    powers = np.where(zero, 0, powers)
    flat_shape = (*mantissa_array.shape[:-1], padded_length)
    return (
        codes.reshape(flat_shape)[..., :length].astype(np.uint8),
        (powers + E8M0_BIAS).astype(np.uint8),
    )


def _quantize_state_exact_vectorized(
    mantissas: np.ndarray,
    exponents: np.ndarray,
    *,
    block_size: int,
    counters: ArithmeticCounters,
) -> EncodedE2M0State:
    primary_e, primary_s, primary_m, primary_x = _quantize_e2m1_term_vectorized(
        mantissas, exponents, block_size=block_size, counters=counters
    )
    residual_m, residual_x = _aligned_sum_last_guarded(
        np.stack((np.asarray(mantissas), -primary_m), axis=-1),
        np.stack((np.asarray(exponents), primary_x), axis=-1),
        counters,
    )
    residual_e, residual_s = _quantize_e2m0_exact_vectorized(
        residual_m, residual_x, block_size=block_size, counters=counters
    )
    return EncodedE2M0State(
        primary_e, primary_s, residual_e, residual_s, block_size
    )


class EncodedE2M0WriteLogGDNVectorized(EncodedE2M0WriteLogGDN):
    """Vectorized implementation cross-checked against the scalar oracle."""

    def _left_action_vectorized(
        self,
        vector: EncodedMXFP4Stack,
        counters: ArithmeticCounters,
    ) -> tuple[np.ndarray, np.ndarray]:
        vector_m, vector_x = _decode_stack_integer("left-action vector", vector)
        base_m, base_x = self._decode_base()
        key_m, key_x, update_m, update_x = self._decoded_logs()
        head_map = np.arange(self.num_value_heads) // self.heads_per_qk

        base_products = (
            vector_m[:, np.newaxis, head_map, :, np.newaxis]
            * base_m[np.newaxis, :, :, :, :]
        )
        base_product_x = (
            vector_x[:, np.newaxis, head_map, :, np.newaxis].astype(np.int32)
            + base_x[np.newaxis, :, :, :, :].astype(np.int32)
        )
        base_terms = np.transpose(base_products, (2, 4, 0, 1, 3)).reshape(
            self.num_value_heads, self.value_dim, -1
        )
        base_terms_x = np.transpose(base_product_x, (2, 4, 0, 1, 3)).reshape(
            self.num_value_heads, self.value_dim, -1
        )
        base_dot_m, base_dot_x = _aligned_sum_last_guarded(
            base_terms, base_terms_x, counters
        )
        base_dot_m = _multiply_q1_15_array(
            base_dot_m, self.gamma_codes[:, np.newaxis], counters
        )

        contribution_m = [base_dot_m]
        contribution_x = [base_dot_x]
        for entry in range(self.live_entries):
            dot_products = (
                vector_m[:, np.newaxis, :, :]
                * key_m[:, entry, :, :][np.newaxis, :, :, :]
            )
            dot_product_x = (
                vector_x[:, np.newaxis, :, :].astype(np.int32)
                + key_x[:, entry, :, :][np.newaxis, :, :, :].astype(np.int32)
            )
            dot_m, dot_x = _aligned_sum_last_guarded(
                np.transpose(dot_products, (2, 0, 1, 3)).reshape(
                    self.num_qk_heads, -1
                ),
                np.transpose(dot_product_x, (2, 0, 1, 3)).reshape(
                    self.num_qk_heads, -1
                ),
                counters,
            )
            scaled_dot_m = _multiply_q1_15_array(
                dot_m[head_map], self.lambda_codes[entry], counters
            )
            for update_term in range(2):
                contribution_m.append(
                    scaled_dot_m[:, np.newaxis]
                    * update_m[update_term, entry]
                )
                contribution_x.append(
                    dot_x[head_map, np.newaxis].astype(np.int32)
                    + update_x[update_term, entry].astype(np.int32)
                )
        return _aligned_sum_last_guarded(
            np.stack(contribution_m, axis=-1),
            np.stack(contribution_x, axis=-1),
            counters,
        )

    def _materialize_vectorized(
        self, counters: ArithmeticCounters
    ) -> tuple[np.ndarray, np.ndarray]:
        base_m, base_x = self._decode_base()
        key_m, key_x, update_m, update_x = self._decoded_logs()
        base_value_m, base_value_x = _aligned_sum_last_guarded(
            np.moveaxis(base_m, 0, -1), np.moveaxis(base_x, 0, -1), counters
        )
        base_value_m = _multiply_q1_15_array(
            base_value_m,
            self.gamma_codes[:, np.newaxis, np.newaxis],
            counters,
        )
        terms_m = [base_value_m]
        terms_x = [base_value_x]
        head_map = np.arange(self.num_value_heads) // self.heads_per_qk
        for entry in range(self.live_entries):
            entry_keys_m = key_m[:, entry, head_map, :]
            entry_keys_x = key_x[:, entry, head_map, :]
            entry_updates_m = update_m[:, entry]
            entry_updates_x = update_x[:, entry]
            products = (
                entry_keys_m[:, np.newaxis, :, :, np.newaxis]
                * entry_updates_m[np.newaxis, :, :, np.newaxis, :]
            )
            product_x = (
                entry_keys_x[:, np.newaxis, :, :, np.newaxis].astype(np.int32)
                + entry_updates_x[np.newaxis, :, :, np.newaxis, :].astype(np.int32)
            )
            rank_m, rank_x = _aligned_sum_last_guarded(
                np.transpose(products, (2, 3, 4, 0, 1)).reshape(
                    self.num_value_heads, self.key_dim, self.value_dim, -1
                ),
                np.transpose(product_x, (2, 3, 4, 0, 1)).reshape(
                    self.num_value_heads, self.key_dim, self.value_dim, -1
                ),
                counters,
            )
            rank_m = _multiply_q1_15_array(
                rank_m,
                self.lambda_codes[entry, :, np.newaxis, np.newaxis],
                counters,
            )
            terms_m.append(rank_m)
            terms_x.append(rank_x)
        return _aligned_sum_last_guarded(
            np.stack(terms_m, axis=-1), np.stack(terms_x, axis=-1), counters
        )

    def materialize_state_fp32(self) -> np.ndarray:
        return super().materialize_state_fp32()

    def _quantize_base_exact_vectorized(
        self,
        mantissas: np.ndarray,
        exponents: np.ndarray,
        counters: ArithmeticCounters,
    ) -> EncodedE2M0State:
        if not isinstance(counters, E2M0ArithmeticCounters):
            raise TypeError("E2M0 base quantization requires E2M0 counters")
        return _quantize_state_exact_vectorized(
            mantissas,
            exponents,
            block_size=self.block_size,
            counters=counters,
        )

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

        counters = self._new_counters()
        self.gamma_codes = np.clip(
            _round_shift_rne_array(
                self.gamma_codes.astype(np.int64) * alpha, np.int64(15)
            ),
            0,
            COEFFICIENT_ONE,
        ).astype(np.uint16)
        if self.live_entries:
            self.lambda_codes[: self.live_entries] = np.clip(
                _round_shift_rne_array(
                    self.lambda_codes[: self.live_entries].astype(np.int64)
                    * alpha[np.newaxis, :],
                    np.int64(15),
                ),
                0,
                COEFFICIENT_ONE,
            ).astype(np.uint16)

        prediction_m, prediction_x = self._left_action_vectorized(token.k, counters)
        v_m, v_x = _decode_stack_integer("v", token.v)
        residual_m, residual_x = _aligned_sum_last_guarded(
            np.stack((v_m[0], v_m[1], -prediction_m), axis=-1),
            np.stack((v_x[0], v_x[1], prediction_x), axis=-1),
            counters,
        )
        delta_m = _multiply_q1_15_array(
            residual_m, beta[:, np.newaxis], counters
        )
        update = _quantize_stack_exact_vectorized(
            delta_m,
            residual_x,
            block_size=self.block_size,
            counters=counters,
        )
        slot = self.live_entries
        self.key_elements[slot] = token.k.elements
        self.key_scales[slot] = token.k.scales
        self.update_elements[slot] = update.elements
        self.update_scales[slot] = update.scales
        self.lambda_codes[slot].fill(COEFFICIENT_ONE)
        self.live_entries += 1

        output_m, output_x = self._left_action_vectorized(token.q, counters)
        folded = self.live_entries == self.capacity
        if folded:
            state_m, state_x = self._materialize_vectorized(counters)
            replacement = self._quantize_base_exact_vectorized(
                state_m,
                state_x,
                counters,
            )
            counters.state_scale_changes += self._base_scale_change_count(replacement)
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

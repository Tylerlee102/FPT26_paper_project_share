from __future__ import annotations

import unittest
from fractions import Fraction

import numpy as np

from golden.gdn_fp32 import gdn_recurrence_core_step
from golden.gdn_mxfp4_encoded import (
    ArithmeticCounters,
    EncodedState,
    EncodedToken,
    _aligned_sum,
    _decode_integer_arrays,
    _round_shift_rne,
    decode_q1_15,
    decode_state,
    encode_q1_15,
    encode_state,
    encode_token,
    recurrence_core_step_encoded,
)
from golden.mx_format import from_mxfp4


class TestGdnMxfp4Encoded(unittest.TestCase):
    def test_exhaustive_valid_e2m1_pairs_are_exact(self) -> None:
        magnitudes = (0, 1, 2, 3, 4, 6, 8, 12)
        valid_codes = tuple(code for code in range(16) if code != 8)

        def power_of_two(exponent: int) -> Fraction:
            if exponent >= 0:
                return Fraction(1 << exponent, 1)
            return Fraction(1, 1 << (-exponent))

        def expected_value(code: int, scale_code: int) -> Fraction:
            magnitude = magnitudes[code & 0x07]
            sign = -1 if code & 0x08 and magnitude else 1
            return Fraction(sign * magnitude, 2) * power_of_two(scale_code - 127)

        for scale_a in (0, 127, 254):
            for scale_b in (0, 127, 254):
                for code_a in valid_codes:
                    mantissa_a, exponent_a = _decode_integer_arrays(
                        "a",
                        np.array([[code_a]], dtype=np.uint8),
                        np.array([[scale_a]], dtype=np.uint8),
                        16,
                    )
                    for code_b in valid_codes:
                        mantissa_b, exponent_b = _decode_integer_arrays(
                            "b",
                            np.array([[code_b]], dtype=np.uint8),
                            np.array([[scale_b]], dtype=np.uint8),
                            16,
                        )
                        product_mantissa = int(mantissa_a[0, 0] * mantissa_b[0, 0])
                        product_exponent = int(exponent_a[0, 0] + exponent_b[0, 0])
                        actual = Fraction(product_mantissa, 1) * power_of_two(
                            product_exponent
                        )
                        expected = expected_value(code_a, scale_a) * expected_value(
                            code_b, scale_b
                        )
                        self.assertEqual(actual, expected)

                        reduced_mantissa, reduced_exponent = _aligned_sum(
                            np.array([product_mantissa], dtype=np.int64),
                            np.array([product_exponent], dtype=np.int32),
                            ArithmeticCounters(),
                        )
                        self.assertEqual(reduced_mantissa, product_mantissa)
                        expected_exponent = product_exponent if product_mantissa else 0
                        self.assertEqual(reduced_exponent, expected_exponent)

    def test_signed_round_shift_rne_exhaustive(self) -> None:
        for shift in range(1, 9):
            denominator = 1 << shift
            for value in range(-255, 256):
                magnitude = abs(value)
                quotient, remainder = divmod(magnitude, denominator)
                if 2 * remainder > denominator or (
                    2 * remainder == denominator and quotient % 2 == 1
                ):
                    quotient += 1
                expected = -quotient if value < 0 else quotient
                self.assertEqual(_round_shift_rne(value, shift), expected)

    def test_q1_15_endpoints_and_ties_to_even(self) -> None:
        values = np.array([0.0, 1.0 / 65536.0, 3.0 / 65536.0, 1.0])
        codes = encode_q1_15(values)

        np.testing.assert_array_equal(codes, np.array([0, 0, 2, 32768], dtype=np.uint16))
        np.testing.assert_array_equal(
            decode_q1_15(np.array([0, 32768], dtype=np.uint16)),
            np.array([0.0, 1.0], dtype=np.float32),
        )
        with self.assertRaisesRegex(ValueError, "0..32768"):
            decode_q1_15(np.array([32769], dtype=np.uint16))

    def test_exact_zero_state_write_matches_fp32_core(self) -> None:
        q_scaled = np.array([[0.5, 0.0]], dtype=np.float32)
        k_normalized = np.array([[1.0, 0.0]], dtype=np.float32)
        v = np.array([[2.0, -1.0, 3.0], [4.0, 1.0, -2.0]], dtype=np.float32)
        alpha = np.ones(2, dtype=np.float32)
        beta = np.ones(2, dtype=np.float32)
        state = np.zeros((2, 2, 3), dtype=np.float32)

        token = encode_token(
            q_scaled, k_normalized, v, alpha, beta, block_size=16
        )
        encoded_state = encode_state(state, block_size=16)
        result = recurrence_core_step_encoded(token, encoded_state)

        decoded_q = from_mxfp4(token.q_elements, token.q_scales, 16, -1)
        decoded_k = from_mxfp4(token.k_elements, token.k_scales, 16, -1)
        decoded_v = from_mxfp4(token.v_elements, token.v_scales, 16, -1)
        expected_output, expected_state = gdn_recurrence_core_step(
            decoded_q,
            decoded_k,
            decoded_v,
            decode_q1_15(token.alpha_codes),
            decode_q1_15(token.beta_codes),
            decode_state(encoded_state),
        )

        np.testing.assert_array_equal(result.output_fp32, expected_output)
        np.testing.assert_array_equal(decode_state(result.state), expected_state)
        self.assertEqual(result.state.elements.shape, (2, 2, 3))

    def test_output_reads_updated_state_before_requantization(self) -> None:
        q_scaled = np.array([[1.0]], dtype=np.float32)
        k_normalized = np.array([[0.5]], dtype=np.float32)
        v = np.array([[1.0]], dtype=np.float32)
        alpha = np.array([1.0], dtype=np.float32)
        beta = np.array([1.0], dtype=np.float32)
        state = np.array([[[1.0]]], dtype=np.float32)

        result = recurrence_core_step_encoded(
            encode_token(q_scaled, k_normalized, v, alpha, beta, block_size=16),
            encode_state(state, block_size=16),
        )

        np.testing.assert_allclose(result.output_fp32, np.array([[1.25]], dtype=np.float32))
        np.testing.assert_allclose(decode_state(result.state), np.array([[[1.0]]], dtype=np.float32))
        updated_value = np.ldexp(
            float(result.updated_mantissas[0, 0, 0]),
            int(result.updated_exponents[0, 0, 0]),
        )
        self.assertEqual(updated_value, 1.25)

    def test_paired_heads_keep_independent_state_and_gates(self) -> None:
        q_scaled = np.array([[1.0, 0.0]], dtype=np.float32)
        k_normalized = np.array([[1.0, 0.0]], dtype=np.float32)
        v = np.array([[1.0, 0.0], [0.0, 2.0]], dtype=np.float32)
        alpha = np.array([0.0, 1.0], dtype=np.float32)
        beta = np.array([1.0, 0.0], dtype=np.float32)
        state = np.zeros((2, 2, 2), dtype=np.float32)
        state[1] = np.eye(2, dtype=np.float32)

        result = recurrence_core_step_encoded(
            encode_token(q_scaled, k_normalized, v, alpha, beta, block_size=16),
            encode_state(state, block_size=16),
        )
        decoded = decode_state(result.state)

        self.assertFalse(np.array_equal(decoded[0], decoded[1]))
        np.testing.assert_array_equal(decoded[1], state[1])

    def test_changing_state_scale_is_counted_and_deterministic(self) -> None:
        q_scaled = np.array([[0.5, 0.0]], dtype=np.float32)
        k_normalized = np.array([[1.0, 0.0]], dtype=np.float32)
        v = np.array([[32.0, -16.0]], dtype=np.float32)
        token = encode_token(
            q_scaled,
            k_normalized,
            v,
            np.ones(1, dtype=np.float32),
            np.ones(1, dtype=np.float32),
            block_size=16,
        )
        state = encode_state(np.zeros((1, 2, 2), dtype=np.float32), block_size=16)

        first = recurrence_core_step_encoded(token, state)
        second = recurrence_core_step_encoded(token, state)

        self.assertGreater(first.counters.state_scale_changes, 0)
        self.assertEqual(first.counters.as_dict(), second.counters.as_dict())
        np.testing.assert_array_equal(first.output_mantissas, second.output_mantissas)
        np.testing.assert_array_equal(first.state.elements, second.state.elements)
        np.testing.assert_array_equal(first.state.scales, second.state.scales)

    def test_large_exponent_gap_records_alignment_underflow(self) -> None:
        token = encode_token(
            np.array([[1.0, 1.0]], dtype=np.float32),
            np.array([[1.0, 1.0]], dtype=np.float32),
            np.zeros((1, 1), dtype=np.float32),
            np.ones(1, dtype=np.float32),
            np.ones(1, dtype=np.float32),
            block_size=16,
        )
        state = EncodedState(
            elements=np.array([[[1], [1]]], dtype=np.uint8),
            scales=np.array([[[100], [150]]], dtype=np.uint8),
            block_size=16,
        )

        result = recurrence_core_step_encoded(token, state)

        self.assertGreater(result.counters.alignment_underflows, 0)

    def test_invalid_scale_and_noncanonical_zero_are_rejected(self) -> None:
        token = encode_token(
            np.array([[1.0]], dtype=np.float32),
            np.array([[1.0]], dtype=np.float32),
            np.array([[1.0]], dtype=np.float32),
            np.array([1.0], dtype=np.float32),
            np.array([1.0], dtype=np.float32),
            block_size=16,
        )
        invalid_scale = EncodedState(
            elements=np.array([[[0]]], dtype=np.uint8),
            scales=np.array([[[255]]], dtype=np.uint8),
            block_size=16,
        )
        negative_zero = EncodedState(
            elements=np.array([[[8]]], dtype=np.uint8),
            scales=np.array([[[127]]], dtype=np.uint8),
            block_size=16,
        )
        noncanonical_zero_block = EncodedState(
            elements=np.array([[[0]]], dtype=np.uint8),
            scales=np.array([[[126]]], dtype=np.uint8),
            block_size=16,
        )

        with self.assertRaisesRegex(ValueError, "255"):
            recurrence_core_step_encoded(token, invalid_scale)
        with self.assertRaisesRegex(ValueError, "negative zero"):
            recurrence_core_step_encoded(token, negative_zero)
        with self.assertRaisesRegex(ValueError, "all-zero block"):
            recurrence_core_step_encoded(token, noncanonical_zero_block)

    def test_token_and_state_block_sizes_must_match(self) -> None:
        token = encode_token(
            np.array([[1.0]], dtype=np.float32),
            np.array([[1.0]], dtype=np.float32),
            np.array([[1.0]], dtype=np.float32),
            np.array([1.0], dtype=np.float32),
            np.array([1.0], dtype=np.float32),
            block_size=16,
        )
        state = encode_state(np.zeros((1, 1, 1), dtype=np.float32), block_size=32)

        with self.assertRaisesRegex(ValueError, "must match"):
            recurrence_core_step_encoded(token, state)


if __name__ == "__main__":
    unittest.main()

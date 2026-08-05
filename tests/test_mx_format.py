from __future__ import annotations

import unittest

import numpy as np

from golden.mx_format import (
    E2M1_VALUES,
    E4M3_FINITE_CODES,
    E4M3_FINITE_VALUES,
    E4M3_POSITIVE_VALUES,
    decode_e2m1,
    decode_e4m3,
    decode_e8m0_scale,
    encode_e2m1,
    encode_e4m3,
    encode_e8m0_scale,
    from_mxfp4,
    from_mxfp8,
    quantization_error,
    to_mxfp4,
    to_mxfp8,
)


class TestMxFormat(unittest.TestCase):
    def test_e2m1_known_values(self) -> None:
        values = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, -6.0], dtype=np.float32)
        codes = encode_e2m1(values)

        np.testing.assert_array_equal(codes, np.array([0, 1, 2, 3, 4, 5, 6, 7, 15], dtype=np.uint8))
        np.testing.assert_allclose(decode_e2m1(codes), values, atol=0.0, rtol=0.0)

    def test_e2m1_round_to_nearest_even(self) -> None:
        halfway = np.array([0.25, 0.75, 1.25, 2.5, 5.0], dtype=np.float32)
        decoded = decode_e2m1(encode_e2m1(halfway))

        np.testing.assert_allclose(decoded, np.array([0.0, 1.0, 1.0, 2.0, 4.0], dtype=np.float32))

    def test_e2m1_canonicalizes_negative_zero(self) -> None:
        codes = encode_e2m1(np.array([-0.0, 0.0], dtype=np.float32))

        np.testing.assert_array_equal(codes, np.array([0, 0], dtype=np.uint8))

    def test_e2m1_vectorized_encoder_matches_exhaustive_table_rounding(self) -> None:
        midpoints = (E2M1_VALUES[:-1] + E2M1_VALUES[1:]) / 2.0
        rng = np.random.default_rng(0xE2D1)
        values = np.concatenate(
            (
                np.array([-0.0, 0.0, -10.0, 10.0], dtype=np.float32),
                E2M1_VALUES,
                -E2M1_VALUES,
                midpoints,
                -midpoints,
                rng.uniform(-10.0, 10.0, size=1024).astype(np.float32),
            )
        )
        magnitudes = np.clip(np.abs(values), 0.0, E2M1_VALUES[-1])
        distances = np.abs(magnitudes[:, None] - E2M1_VALUES[None, :])
        minimum = np.min(distances, axis=1, keepdims=True)
        ties = np.isclose(distances, minimum, rtol=0.0, atol=1e-12)
        codes = np.arange(E2M1_VALUES.size, dtype=np.uint8)
        ranks = np.where(ties, np.where((codes & 1) == 0, 0, 1), 1000)
        magnitude_codes = codes[np.argmin(ranks, axis=1)]
        sign = (np.signbit(values) & (magnitude_codes != 0)).astype(np.uint8) << 3
        expected = sign | magnitude_codes

        np.testing.assert_array_equal(encode_e2m1(values), expected)

    def test_e8m0_scale_roundtrip(self) -> None:
        scales = np.array([0.25, 0.5, 1.0, 2.0, 16.0], dtype=np.float32)
        codes = encode_e8m0_scale(scales)

        np.testing.assert_allclose(decode_e8m0_scale(codes), scales, atol=0.0, rtol=0.0)

    def test_e8m0_rejects_reserved_nan_code(self) -> None:
        with self.assertRaisesRegex(ValueError, "255"):
            decode_e8m0_scale(np.array([255], dtype=np.uint8))

    def test_mxfp4_block_size_16_and_32(self) -> None:
        rng = np.random.default_rng(0xFB72)
        x = rng.normal(0.0, 0.75, size=(4, 64)).astype(np.float32)

        for block_size in (16, 32):
            elements, scales = to_mxfp4(x, block_size=block_size, axis=-1)
            restored = from_mxfp4(elements, scales, block_size=block_size, axis=-1)

            self.assertEqual(elements.dtype, np.uint8)
            self.assertEqual(scales.dtype, np.uint8)
            self.assertEqual(elements.shape, x.shape)
            self.assertEqual(scales.shape, (4, 64 // block_size))
            self.assertLessEqual(float(np.max(np.abs(restored - x))), 0.75)

    def test_mxfp4_zero_blocks_are_stable(self) -> None:
        x = np.zeros((2, 17), dtype=np.float32)
        elements, scales = to_mxfp4(x, block_size=16, axis=-1)
        restored = from_mxfp4(elements, scales, block_size=16, axis=-1)

        np.testing.assert_array_equal(elements, np.zeros_like(elements))
        np.testing.assert_allclose(restored, x, atol=0.0, rtol=0.0)

    def test_e4m3_representable_values_roundtrip(self) -> None:
        codes = np.array([code for code in range(256) if code not in (0x7F, 0xFF)], dtype=np.uint8)
        values = decode_e4m3(codes)
        finite_nonzero = values[values != 0.0]
        sample = finite_nonzero[::17]

        np.testing.assert_allclose(decode_e4m3(encode_e4m3(sample)), sample, atol=0.0, rtol=0.0)

    def test_e4m3_maximum_and_nan_codes_follow_finite_only_format(self) -> None:
        encoded = encode_e4m3(np.array([448.0, 480.0, -480.0], dtype=np.float32))
        decoded = decode_e4m3(encoded)

        np.testing.assert_array_equal(decoded, np.array([448.0, 448.0, -448.0], dtype=np.float32))
        with self.assertRaisesRegex(ValueError, "NaN encoding"):
            decode_e4m3(np.array([0x7F, 0xFF], dtype=np.uint8))

    def test_e4m3_vectorized_encoder_matches_exhaustive_table_rounding(self) -> None:
        midpoints = (E4M3_POSITIVE_VALUES[:-1] + E4M3_POSITIVE_VALUES[1:]) / 2.0
        rng = np.random.default_rng(0xE4F3)
        values = np.concatenate(
            (
                np.array([-0.0, 0.0, -500.0, 500.0], dtype=np.float32),
                E4M3_POSITIVE_VALUES,
                -E4M3_POSITIVE_VALUES,
                midpoints,
                -midpoints,
                rng.uniform(-500.0, 500.0, size=1024).astype(np.float32),
            )
        )

        distances = np.abs(values[:, None] - E4M3_FINITE_VALUES[None, :])
        minimum = np.min(distances, axis=1, keepdims=True)
        ties = np.isclose(distances, minimum, rtol=0.0, atol=1e-12)
        even = (E4M3_FINITE_CODES.astype(np.int16) & 1) == 0
        ranks = np.where(ties, np.where(even, 0, 1), 1000)
        expected = E4M3_FINITE_CODES[np.argmin(ranks, axis=1)]

        np.testing.assert_array_equal(encode_e4m3(values), expected)

    def test_mxfp8_is_more_precise_than_mxfp4_on_state_like_values(self) -> None:
        rng = np.random.default_rng(99)
        x = rng.normal(0.0, 0.05, size=(2, 16, 16)).astype(np.float32)

        fp4_elems, fp4_scales = to_mxfp4(x, block_size=16, axis=-1)
        fp8_elems, fp8_scales = to_mxfp8(x, block_size=16, axis=-1)
        fp4 = from_mxfp4(fp4_elems, fp4_scales, block_size=16, axis=-1)
        fp8 = from_mxfp8(fp8_elems, fp8_scales, block_size=16, axis=-1)

        self.assertLessEqual(quantization_error(x, fp8)["rel_l2"], quantization_error(x, fp4)["rel_l2"])


if __name__ == "__main__":
    unittest.main()

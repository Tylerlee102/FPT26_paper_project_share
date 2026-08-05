from __future__ import annotations

import unittest

import numpy as np

from golden.gdn_mxfp4 import quantize_state
from golden.mxfp4_scale_policy import (
    initialize_mxfp4_state,
    quantize_mxfp4_state_with_policy,
)
from golden.mx_format import from_mxfp4, to_mxfp4_with_scales


class TestMxfp4ScalePolicy(unittest.TestCase):
    def test_every_token_matches_dynamic_state_quantization(self) -> None:
        rng = np.random.default_rng(0x5CA1E)
        initial = rng.normal(0.0, 0.1, size=(2, 3, 17)).astype(np.float32)
        updated = rng.normal(0.0, 0.7, size=initial.shape).astype(np.float32)
        resident = initialize_mxfp4_state(initial, block_size=16)

        result = quantize_mxfp4_state_with_policy(
            updated,
            resident.scales,
            token_index=1,
            policy="every_token",
            block_size=16,
        )

        np.testing.assert_array_equal(
            result.resident_state,
            quantize_state(updated, block_size=16, precision="mxfp4"),
        )

    def test_fixed_policy_preserves_scales_and_counts_saturation(self) -> None:
        initial = np.full((1, 1, 16), 0.5, dtype=np.float32)
        resident = initialize_mxfp4_state(initial, block_size=16)
        updated = np.full((1, 1, 16), 128.0, dtype=np.float32)

        result = quantize_mxfp4_state_with_policy(
            updated,
            resident.scales,
            token_index=1,
            policy="fixed",
            block_size=16,
        )

        np.testing.assert_array_equal(result.scales, resident.scales)
        self.assertEqual(result.scale_refreshes, 0)
        self.assertEqual(result.state_scale_changes, 0)
        self.assertEqual(result.element_saturations, 16)

    def test_periodic_policy_refreshes_only_on_interval(self) -> None:
        initial = np.full((1, 1, 16), 0.5, dtype=np.float32)
        resident = initialize_mxfp4_state(initial, block_size=16)
        updated = np.full((1, 1, 16), 32.0, dtype=np.float32)

        held = quantize_mxfp4_state_with_policy(
            updated,
            resident.scales,
            token_index=3,
            policy="periodic",
            refresh_interval=4,
            block_size=16,
        )
        refreshed = quantize_mxfp4_state_with_policy(
            updated,
            resident.scales,
            token_index=4,
            policy="periodic",
            refresh_interval=4,
            block_size=16,
        )

        np.testing.assert_array_equal(held.scales, resident.scales)
        self.assertEqual(held.scale_refreshes, 0)
        self.assertEqual(refreshed.scale_refreshes, 1)
        self.assertGreater(refreshed.state_scale_changes, 0)
        self.assertEqual(refreshed.element_saturations, 0)

    def test_threshold_policy_refreshes_high_and_low_nonzero_blocks(self) -> None:
        scales = np.array([[[127, 127]]], dtype=np.uint8)
        state = np.concatenate(
            (
                np.full(16, 8.0, dtype=np.float32),
                np.full(16, 0.5, dtype=np.float32),
            )
        ).reshape(1, 1, 32)

        result = quantize_mxfp4_state_with_policy(
            state,
            scales,
            token_index=1,
            policy="threshold",
            block_size=16,
        )

        self.assertEqual(result.scale_refreshes, 2)
        self.assertEqual(result.state_scale_changes, 2)
        self.assertEqual(result.element_saturations, 0)

    def test_fixed_scale_quantizer_validates_shape_and_reports_clipping(self) -> None:
        values = np.array([[0.0, 8.0]], dtype=np.float32)
        elements, saturations = to_mxfp4_with_scales(
            values,
            np.array([[127]], dtype=np.uint8),
            block_size=16,
            axis=-1,
        )

        self.assertEqual(saturations, 1)
        np.testing.assert_array_equal(
            from_mxfp4(elements, np.array([[127]], dtype=np.uint8), 16, -1),
            np.array([[0.0, 6.0]], dtype=np.float32),
        )
        with self.assertRaisesRegex(ValueError, "scales shape"):
            to_mxfp4_with_scales(values, np.array([127], dtype=np.uint8), 16, -1)

    def test_invalid_policy_is_rejected(self) -> None:
        resident = initialize_mxfp4_state(
            np.zeros((1, 1, 16), dtype=np.float32), block_size=16
        )
        with self.assertRaisesRegex(ValueError, "unknown scale policy"):
            quantize_mxfp4_state_with_policy(
                resident.resident_state,
                resident.scales,
                token_index=1,
                policy="sometimes",
                block_size=16,
            )


if __name__ == "__main__":
    unittest.main()

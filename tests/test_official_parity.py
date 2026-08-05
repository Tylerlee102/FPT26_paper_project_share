from __future__ import annotations

import unittest

import numpy as np

from scripts.official_parity import (
    BF16_COSINE_LIMIT,
    BF16_MAX_ABS_LIMIT,
    BF16_REL_L2_LIMIT,
    FP32_MAX_ABS_LIMIT,
    FP32_REL_L2_LIMIT,
    ParityConfiguration,
    comparison_status,
    error_metrics,
    validate_configuration,
)


class TestOfficialParityHelpers(unittest.TestCase):
    def test_default_configuration_is_exact_qwen_boundary(self) -> None:
        config = ParityConfiguration()
        validate_configuration(config)
        self.assertEqual(config.qk_heads, 16)
        self.assertEqual(config.value_heads, 32)
        self.assertEqual(config.key_dim, 128)
        self.assertEqual(config.value_dim, 128)

    def test_invalid_configuration_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "divisible"):
            validate_configuration(ParityConfiguration(qk_heads=3, value_heads=4))
        with self.assertRaisesRegex(ValueError, "prefill"):
            validate_configuration(ParityConfiguration(tokens=64, prefill_tokens=64))

    def test_metrics_and_fp32_threshold(self) -> None:
        reference = np.array([1.0, -2.0, 3.0], dtype=np.float64)
        identical = error_metrics(reference, reference.copy())
        self.assertEqual(identical, {"cosine": 1.0, "rel_l2": 0.0, "max_abs": 0.0})
        self.assertEqual(
            comparison_status(identical, identical, precision="fp32"), "PASS"
        )

        bad_output = dict(identical)
        bad_output["rel_l2"] = FP32_REL_L2_LIMIT * 2
        bad_output["max_abs"] = FP32_MAX_ABS_LIMIT * 2
        self.assertEqual(
            comparison_status(bad_output, identical, precision="fp32"), "FAIL"
        )

    def test_bf16_threshold_requires_cosine_and_error_bounds(self) -> None:
        passing = {
            "cosine": BF16_COSINE_LIMIT,
            "rel_l2": BF16_REL_L2_LIMIT,
            "max_abs": BF16_MAX_ABS_LIMIT,
        }
        self.assertEqual(
            comparison_status(passing, passing, precision="bf16"), "PASS"
        )
        failing = dict(passing)
        failing["cosine"] = BF16_COSINE_LIMIT - 1e-6
        self.assertEqual(
            comparison_status(failing, passing, precision="bf16"), "FAIL"
        )


if __name__ == "__main__":
    unittest.main()

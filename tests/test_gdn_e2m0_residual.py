from __future__ import annotations

import unittest

import numpy as np

from golden.gdn_e2m0_residual import (
    E2M0ResidualWriteLogGDN,
    quantize_e2m0_residual,
    quantize_mxfp4_e2m0_stack,
)
from golden.gdn_mxfp4 import quantize_activation
from golden.gdn_write_log import WriteLogConfiguration


class TestE2M0Residual(unittest.TestCase):
    def test_stack_reduces_error_beyond_one_mxfp4_term(self) -> None:
        rng = np.random.default_rng(0xE2A0)
        values = rng.normal(size=(8, 128)).astype(np.float32)
        one = quantize_activation(values, block_size=32)
        two = quantize_mxfp4_e2m0_stack(values, block_size=32, depth=2)
        self.assertLess(np.linalg.norm(two - values), np.linalg.norm(one - values))

    def test_quantizer_is_deterministic_and_handles_partial_blocks(self) -> None:
        rng = np.random.default_rng(0xFB72)
        values = rng.normal(size=(3, 47)).astype(np.float32)
        left = quantize_e2m0_residual(values, block_size=32)
        right = quantize_e2m0_residual(values, block_size=32)
        self.assertEqual(left.shape, values.shape)
        np.testing.assert_array_equal(left, right)
        self.assertTrue(np.all(np.isfinite(left)))

    def test_adjacent_scale_search_improves_known_block(self) -> None:
        values = np.array(
            [[0.26, -0.49, 0.74, -1.01, 1.49, -1.74, 1.99, -2.01]],
            dtype=np.float32,
        )
        quantized = quantize_e2m0_residual(values, block_size=8)
        self.assertLess(float(np.linalg.norm(quantized - values)), 0.8)

    def test_engine_is_deterministic_and_never_drops_entries(self) -> None:
        rng = np.random.default_rng(0xC0FFEE)
        initial = rng.normal(0.0, 0.1, size=(2, 4, 4)).astype(np.float32)
        config = WriteLogConfiguration(
            capacity=3,
            mode="mxfp4",
            activation_block_size=16,
            base_block_size=16,
            log_block_size=16,
            log_precision="mxfp8_e4m3",
            base_stack_depth=2,
        )
        engines = [
            E2M0ResidualWriteLogGDN(initial, num_qk_heads=1, config=config),
            E2M0ResidualWriteLogGDN(initial, num_qk_heads=1, config=config),
        ]
        inputs = [
            (
                rng.normal(size=(1, 4)).astype(np.float32),
                rng.normal(size=(1, 4)).astype(np.float32),
                rng.normal(size=(2, 4)).astype(np.float32),
                rng.uniform(0.9, 1.0, size=2).astype(np.float32),
                rng.uniform(0.0, 1.0, size=2).astype(np.float32),
            )
            for _ in range(7)
        ]
        outputs = [[engine.step(*item) for item in inputs] for engine in engines]
        for left, right in zip(outputs[0], outputs[1]):
            np.testing.assert_array_equal(left[0], right[0])
            np.testing.assert_array_equal(left[1], right[1])
        self.assertEqual(engines[0].counters.dropped_entries, 0)
        self.assertEqual(engines[0].counters.folds, 2)

    def test_rejects_unknown_log_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown E2M0 write-log mode"):
            E2M0ResidualWriteLogGDN(
                np.zeros((2, 4, 4), dtype=np.float32),
                num_qk_heads=1,
                config=WriteLogConfiguration(capacity=3, mode="mxfp4"),
                log_mode="unknown",
            )


if __name__ == "__main__":
    unittest.main()

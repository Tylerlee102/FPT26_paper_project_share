from __future__ import annotations

import unittest

import numpy as np

from golden.gdn_fp32 import gdn_decode_step as fp32_decode_step
from golden.gdn_int4 import (
    dequantize_symmetric_int4,
    gdn_decode_step as int4_decode_step,
    quantize_symmetric_int4,
)


class TestGdnInt4(unittest.TestCase):
    def test_symmetric_int4_roundtrip_bounds(self) -> None:
        x = np.array([-2.0, -1.0, 0.0, 0.9, 2.0], dtype=np.float32)
        codes, scale = quantize_symmetric_int4(x)
        restored = dequantize_symmetric_int4(codes, scale)

        self.assertEqual(codes.dtype, np.int8)
        self.assertLessEqual(int(np.max(codes)), 7)
        self.assertGreaterEqual(int(np.min(codes)), -7)
        self.assertLessEqual(float(np.max(np.abs(restored - x))), float(scale) / 2.0 + 1e-6)

    def test_int4_decode_step_shapes_and_error_budget(self) -> None:
        rng = np.random.default_rng(9)
        q = rng.normal(0.0, 0.1, size=(1, 8)).astype(np.float32)
        k = rng.normal(0.0, 0.1, size=(1, 8)).astype(np.float32)
        v = rng.normal(0.0, 0.1, size=(2, 8)).astype(np.float32)
        alpha = rng.uniform(0.85, 1.0, size=(2,)).astype(np.float32)
        beta = rng.uniform(0.0, 0.5, size=(2,)).astype(np.float32)
        state = rng.normal(0.0, 0.02, size=(2, 8, 8)).astype(np.float32)

        fp32_output, fp32_state = fp32_decode_step(q, k, v, alpha, beta, state)
        int4_output, int4_state = int4_decode_step(q, k, v, alpha, beta, state)

        self.assertEqual(int4_output.shape, fp32_output.shape)
        self.assertEqual(int4_state.shape, fp32_state.shape)
        np.testing.assert_allclose(int4_output, fp32_output, atol=0.05, rtol=0.5)


if __name__ == "__main__":
    unittest.main()

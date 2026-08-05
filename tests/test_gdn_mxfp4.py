from __future__ import annotations

import unittest

import numpy as np

from golden.gdn_fp32 import gdn_decode_step as fp32_decode_step
from golden.gdn_mxfp4 import gdn_decode_step as mxfp4_decode_step
from golden.mx_format import from_mxfp4, to_mxfp4


class TestGdnMxfp4(unittest.TestCase):
    def test_mxfp4_vs_fp32_synthetic(self) -> None:
        rng = np.random.default_rng(7)
        q = rng.normal(0.0, 0.1, size=(1, 16)).astype(np.float32)
        k = rng.normal(0.0, 0.1, size=(1, 16)).astype(np.float32)
        v = rng.normal(0.0, 0.1, size=(2, 16)).astype(np.float32)
        alpha = rng.uniform(0.85, 1.0, size=(2,)).astype(np.float32)
        beta = rng.uniform(0.0, 0.5, size=(2,)).astype(np.float32)
        state = rng.normal(0.0, 0.02, size=(2, 16, 16)).astype(np.float32)

        fp32_output, fp32_state = fp32_decode_step(q, k, v, alpha, beta, state)
        mx_output, mx_state = mxfp4_decode_step(
            q, k, v, alpha, beta, state, block_size=16, state_block_size=16
        )

        self.assertEqual(mx_output.shape, fp32_output.shape)
        self.assertEqual(mx_state.shape, fp32_state.shape)
        self.assertGreater(float(np.linalg.norm(mx_output)), 0.0)
        np.testing.assert_allclose(mx_output, fp32_output, atol=0.05, rtol=0.35)

    def test_block_quantization_is_deterministic(self) -> None:
        rng = np.random.default_rng(11)
        x = rng.normal(0.0, 0.25, size=(2, 32)).astype(np.float32)

        elems_a, scales_a = to_mxfp4(x, block_size=16, axis=-1)
        elems_b, scales_b = to_mxfp4(x, block_size=16, axis=-1)

        np.testing.assert_array_equal(elems_a, elems_b)
        np.testing.assert_array_equal(scales_a, scales_b)
        np.testing.assert_array_equal(
            from_mxfp4(elems_a, scales_a, block_size=16, axis=-1),
            from_mxfp4(elems_b, scales_b, block_size=16, axis=-1),
        )

    def test_mxfp8_state_path_runs(self) -> None:
        rng = np.random.default_rng(12)
        q = rng.normal(0.0, 0.1, size=(1, 16)).astype(np.float32)
        k = rng.normal(0.0, 0.1, size=(1, 16)).astype(np.float32)
        v = rng.normal(0.0, 0.1, size=(2, 16)).astype(np.float32)
        alpha = rng.uniform(0.85, 1.0, size=(2,)).astype(np.float32)
        beta = rng.uniform(0.0, 0.5, size=(2,)).astype(np.float32)
        state = rng.normal(0.0, 0.02, size=(2, 16, 16)).astype(np.float32)

        out, state_out = mxfp4_decode_step(
            q,
            k,
            v,
            alpha,
            beta,
            state,
            block_size=16,
            state_block_size=16,
            state_precision="mxfp8_e4m3",
        )

        self.assertEqual(out.shape, v.shape)
        self.assertEqual(state_out.shape, state.shape)


if __name__ == "__main__":
    unittest.main()

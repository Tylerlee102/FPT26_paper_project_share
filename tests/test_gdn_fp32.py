from __future__ import annotations

import unittest

import numpy as np

from golden.gdn_fp32 import gdn_decode_step, ungated_decode_step


class TestGdnFp32(unittest.TestCase):
    def test_recurrence_fixed_point(self) -> None:
        rng = np.random.default_rng(123)
        q = rng.normal(size=(2, 4)).astype(np.float32)
        k = rng.normal(size=(2, 4)).astype(np.float32)
        v = rng.normal(size=(2, 4)).astype(np.float32)
        beta = np.zeros((2,), dtype=np.float32)
        gate = np.ones((2, 4), dtype=np.float32)
        state_in = rng.normal(size=(2, 4, 4)).astype(np.float32)

        _, state_out = gdn_decode_step(q, k, v, beta, gate, state_in)

        np.testing.assert_allclose(state_out, state_in, atol=0.0, rtol=0.0)

    def test_delta_rule_perfect_recall(self) -> None:
        q = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        k = q.copy()
        v = np.array([[0.5, -0.25, 0.75, 1.25]], dtype=np.float32)
        beta = np.ones((1,), dtype=np.float32)
        gate = np.ones((1, 4), dtype=np.float32)
        state_in = np.zeros((1, 4, 4), dtype=np.float32)

        output, _ = gdn_decode_step(q, k, v, beta, gate, state_in)

        np.testing.assert_allclose(output, v, atol=1e-5, rtol=0.0)

    def test_gate_disabled(self) -> None:
        rng = np.random.default_rng(456)
        q = rng.normal(size=(3, 5)).astype(np.float32)
        k = rng.normal(size=(3, 5)).astype(np.float32)
        v = rng.normal(size=(3, 5)).astype(np.float32)
        beta = rng.uniform(size=(3,)).astype(np.float32)
        gate = np.ones((3, 5), dtype=np.float32)
        state_in = rng.normal(size=(3, 5, 5)).astype(np.float32)

        gated, gated_state = gdn_decode_step(q, k, v, beta, gate, state_in)
        ungated, ungated_state = ungated_decode_step(q, k, v, beta, state_in)

        np.testing.assert_allclose(gated, ungated, atol=0.0, rtol=0.0)
        np.testing.assert_allclose(gated_state, ungated_state, atol=0.0, rtol=0.0)

    def test_against_independent_numpy_reference(self) -> None:
        rng = np.random.default_rng(789)
        q = rng.normal(size=(2, 3)).astype(np.float32)
        k = rng.normal(size=(2, 3)).astype(np.float32)
        v = rng.normal(size=(2, 3)).astype(np.float32)
        beta = rng.uniform(size=(2,)).astype(np.float32)
        gate = rng.uniform(size=(2, 3)).astype(np.float32)
        state_in = rng.normal(size=(2, 3, 3)).astype(np.float32)

        output, state_out = gdn_decode_step(q, k, v, beta, gate, state_in)

        expected_state = np.empty_like(state_in)
        expected_output = np.empty_like(q)
        for h in range(2):
            residual = state_in[h] @ k[h] - v[h]
            expected_state[h] = state_in[h] - beta[h] * np.outer(residual, k[h])
            expected_output[h] = gate[h] * (expected_state[h] @ q[h])

        np.testing.assert_allclose(state_out, expected_state, atol=1e-6, rtol=1e-6)
        np.testing.assert_allclose(output, expected_output, atol=1e-6, rtol=1e-6)


if __name__ == "__main__":
    unittest.main()

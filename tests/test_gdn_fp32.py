from __future__ import annotations

import unittest

import numpy as np

from golden.gdn_fp32 import (
    derive_alpha_beta,
    gdn_decode_sequence,
    gdn_decode_step,
    gdn_recurrence_core_step,
    normalize_qk,
    state_kv_to_vk,
    state_vk_to_kv,
)
from golden.gdn_oracle_fp64 import derive_alpha_beta_fp64, recurrence_step_fp64


class TestGdnFp32(unittest.TestCase):
    def test_random_non_square_state_matches_independent_fp64(self) -> None:
        rng = np.random.default_rng(0xFB72)
        q = rng.normal(size=(2, 3)).astype(np.float32)
        k = rng.normal(size=(2, 3)).astype(np.float32)
        v = rng.normal(size=(4, 5)).astype(np.float32)
        alpha = rng.uniform(0.2, 1.0, size=4).astype(np.float32)
        beta = rng.uniform(0.0, 1.0, size=4).astype(np.float32)
        state = rng.normal(size=(4, 3, 5)).astype(np.float32)

        output, state_out = gdn_decode_step(q, k, v, alpha, beta, state)
        expected_output, expected_state = recurrence_step_fp64(
            q, k, v, alpha, beta, state
        )

        np.testing.assert_allclose(state_out, expected_state, atol=5e-6, rtol=1e-5)
        np.testing.assert_allclose(output, expected_output, atol=5e-6, rtol=1e-5)

    def test_core_boundary_matches_internal_normalization(self) -> None:
        rng = np.random.default_rng(12)
        q = rng.normal(size=(1, 7)).astype(np.float32)
        k = rng.normal(size=(1, 7)).astype(np.float32)
        v = rng.normal(size=(2, 3)).astype(np.float32)
        alpha = np.array([0.75, 0.9], dtype=np.float32)
        beta = np.array([0.25, 1.0], dtype=np.float32)
        state = rng.normal(size=(2, 7, 3)).astype(np.float32)

        q_scaled, k_normalized = normalize_qk(q, k)
        boundary_output, boundary_state = gdn_recurrence_core_step(
            q_scaled, k_normalized, v, alpha, beta, state
        )
        full_output, full_state = gdn_decode_step(q, k, v, alpha, beta, state)

        np.testing.assert_array_equal(boundary_output, full_output)
        np.testing.assert_array_equal(boundary_state, full_state)

    def test_alpha_zero_erases_state_before_prediction(self) -> None:
        q = np.array([[1.0]], dtype=np.float32)
        k = np.array([[1.0]], dtype=np.float32)
        v = np.array([[7.0]], dtype=np.float32)
        alpha = np.array([0.0], dtype=np.float32)
        beta = np.array([0.0], dtype=np.float32)
        state = np.array([[[123.0]]], dtype=np.float32)

        output, state_out = gdn_decode_step(q, k, v, alpha, beta, state)

        np.testing.assert_array_equal(state_out, np.zeros_like(state))
        np.testing.assert_array_equal(output, np.zeros_like(v))

    def test_prediction_uses_decayed_state_and_output_uses_updated_state(self) -> None:
        eps = 1e-6
        q = np.array([[1.0]], dtype=np.float32)
        k = np.array([[1.0]], dtype=np.float32)
        v = np.array([[3.0]], dtype=np.float32)
        alpha = np.array([0.5], dtype=np.float32)
        beta = np.array([1.0], dtype=np.float32)
        state = np.array([[[2.0]]], dtype=np.float32)

        output, state_out = gdn_decode_step(q, k, v, alpha, beta, state, eps=eps)

        normalized = np.float32(1.0 / np.sqrt(1.0 + eps))
        decayed = np.float32(1.0)
        prediction = normalized * decayed
        delta = np.float32(3.0) - prediction
        expected_state = decayed + normalized * delta
        expected_output = normalized * expected_state
        np.testing.assert_allclose(state_out[0, 0, 0], expected_state, atol=2e-7, rtol=0.0)
        np.testing.assert_allclose(output[0, 0], expected_output, atol=2e-7, rtol=0.0)

    def test_contiguous_sequence_matches_separate_invocations(self) -> None:
        rng = np.random.default_rng(99)
        q = rng.normal(size=(6, 2, 4)).astype(np.float32)
        k = rng.normal(size=(6, 2, 4)).astype(np.float32)
        v = rng.normal(size=(6, 4, 3)).astype(np.float32)
        alpha = rng.uniform(0.5, 1.0, size=(6, 4)).astype(np.float32)
        beta = rng.uniform(0.0, 1.0, size=(6, 4)).astype(np.float32)
        state = rng.normal(size=(4, 4, 3)).astype(np.float32)

        sequence_output, sequence_state = gdn_decode_sequence(q, k, v, alpha, beta, state)
        manual_state = state.copy()
        manual_outputs = []
        for token in range(q.shape[0]):
            output, manual_state = gdn_decode_step(
                q[token], k[token], v[token], alpha[token], beta[token], manual_state
            )
            manual_outputs.append(output)

        np.testing.assert_array_equal(sequence_output, np.stack(manual_outputs))
        np.testing.assert_array_equal(sequence_state, manual_state)

    def test_paired_qk_head_mapping(self) -> None:
        q = np.array([[1.0, 0.0]], dtype=np.float32)
        k = np.array([[1.0, 0.0]], dtype=np.float32)
        v = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        alpha = np.ones(2, dtype=np.float32)
        beta = np.ones(2, dtype=np.float32)
        state = np.zeros((2, 2, 2), dtype=np.float32)

        output, state_out = gdn_decode_step(q, k, v, alpha, beta, state)

        self.assertFalse(np.array_equal(state_out[0], state_out[1]))
        ratio = output[1] / output[0]
        np.testing.assert_allclose(ratio, np.array([3.0, 2.0], dtype=np.float32), atol=1e-5)

    def test_state_orientation_round_trip(self) -> None:
        state = np.arange(2 * 3 * 5, dtype=np.float32).reshape(2, 3, 5)
        physical = state_kv_to_vk(state)

        self.assertEqual(physical.shape, (2, 5, 3))
        np.testing.assert_array_equal(state_vk_to_kv(physical), state)

    def test_gate_derivation_matches_fp64_and_stays_bounded(self) -> None:
        a = np.array([-50.0, 0.0, 20.0], dtype=np.float32)
        b = np.array([-100.0, 0.0, 100.0], dtype=np.float32)
        a_log = np.array([-3.0, 0.0, 2.0], dtype=np.float32)
        dt_bias = np.array([0.5, -0.25, 1.0], dtype=np.float32)

        alpha, beta = derive_alpha_beta(a, b, a_log, dt_bias)
        alpha64, beta64 = derive_alpha_beta_fp64(a, b, a_log, dt_bias)

        np.testing.assert_allclose(alpha, alpha64, atol=2e-7, rtol=2e-6)
        np.testing.assert_allclose(beta, beta64, atol=2e-7, rtol=2e-6)
        self.assertTrue(np.all(alpha >= 0.0))
        self.assertTrue(np.all(alpha <= 1.0))
        self.assertTrue(np.all(beta >= 0.0))
        self.assertTrue(np.all(beta <= 1.0))

    def test_invalid_shapes_bounds_and_nonfinite_inputs_are_rejected(self) -> None:
        q = np.ones((1, 2), dtype=np.float32)
        k = np.ones((1, 2), dtype=np.float32)
        v = np.ones((2, 3), dtype=np.float32)
        state = np.ones((2, 2, 3), dtype=np.float32)

        with self.assertRaisesRegex(ValueError, "alpha must be in"):
            gdn_decode_step(q, k, v, [-0.1, 1.0], [0.0, 1.0], state)
        with self.assertRaisesRegex(ValueError, "beta must be in"):
            gdn_decode_step(q, k, v, [0.0, 1.0], [0.0, 1.1], state)
        with self.assertRaisesRegex(ValueError, "K-by-V"):
            gdn_decode_step(q, k, v, [0.0, 1.0], [0.0, 1.0], np.ones((2, 3, 2)))
        with self.assertRaisesRegex(ValueError, "NaN or Inf"):
            bad_q = q.copy()
            bad_q[0, 0] = np.nan
            gdn_decode_step(bad_q, k, v, [0.0, 1.0], [0.0, 1.0], state)


if __name__ == "__main__":
    unittest.main()

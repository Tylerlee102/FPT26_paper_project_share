from __future__ import annotations

import unittest

import numpy as np

from golden.gdn_oracle_fp64 import (
    affine_scan_sequence_fp64,
    derive_alpha_beta_fp64,
    recurrence_sequence_fp64,
    recurrence_step_fp64,
    state_kv_to_vk,
    state_vk_to_kv,
)


class TestGdnOracleFp64(unittest.TestCase):
    def test_zero_state_unit_write_has_hand_derived_result(self) -> None:
        eps = 1e-6
        q = np.array([[1.0, 0.0]], dtype=np.float64)
        k = np.array([[1.0, 0.0]], dtype=np.float64)
        v = np.array([[2.0, -4.0, 6.0]], dtype=np.float64)
        alpha = np.array([1.0], dtype=np.float64)
        beta = np.array([1.0], dtype=np.float64)
        state = np.zeros((1, 2, 3), dtype=np.float64)

        output, state_out = recurrence_step_fp64(q, k, v, alpha, beta, state, eps=eps)

        k_factor = 1.0 / np.sqrt(1.0 + eps)
        q_factor = k_factor / np.sqrt(2.0)
        expected_state = np.zeros_like(state)
        expected_state[0, 0] = k_factor * v[0]
        expected_output = (q_factor * k_factor * v[0])[None, :]
        np.testing.assert_allclose(state_out, expected_state, atol=1e-15, rtol=1e-15)
        np.testing.assert_allclose(output, expected_output, atol=1e-15, rtol=1e-15)

    def test_beta_zero_performs_pure_decay(self) -> None:
        q = np.array([[2.0, -1.0]], dtype=np.float64)
        k = np.array([[1.0, 3.0]], dtype=np.float64)
        v = np.array([[9.0, 8.0, 7.0]], dtype=np.float64)
        alpha = np.array([0.25], dtype=np.float64)
        beta = np.array([0.0], dtype=np.float64)
        state = np.arange(6, dtype=np.float64).reshape(1, 2, 3)

        _, state_out = recurrence_step_fp64(q, k, v, alpha, beta, state)

        np.testing.assert_array_equal(state_out, state * 0.25)

    def test_alpha_zero_removes_all_previous_state_influence(self) -> None:
        rng = np.random.default_rng(4)
        q = rng.normal(size=(1, 3))
        k = rng.normal(size=(1, 3))
        v = rng.normal(size=(2, 4))
        alpha = np.zeros(2)
        beta = np.ones(2)
        state_a = rng.normal(size=(2, 3, 4))
        state_b = rng.normal(size=(2, 3, 4)) * 1000.0

        output_a, result_a = recurrence_step_fp64(q, k, v, alpha, beta, state_a)
        output_b, result_b = recurrence_step_fp64(q, k, v, alpha, beta, state_b)

        np.testing.assert_array_equal(result_a, result_b)
        np.testing.assert_array_equal(output_a, output_b)

    def test_affine_scan_matches_scalar_recurrence(self) -> None:
        rng = np.random.default_rng(0xA11CE)
        q = rng.normal(size=(7, 2, 3))
        k = rng.normal(size=(7, 2, 3))
        v = rng.normal(size=(7, 4, 5))
        alpha = rng.uniform(0.1, 1.0, size=(7, 4))
        beta = rng.uniform(0.0, 1.0, size=(7, 4))
        state = rng.normal(size=(4, 3, 5))

        recurrent_output, recurrent_state = recurrence_sequence_fp64(
            q, k, v, alpha, beta, state
        )
        affine_output, affine_state = affine_scan_sequence_fp64(
            q, k, v, alpha, beta, state
        )

        np.testing.assert_allclose(affine_output, recurrent_output, atol=2e-15, rtol=2e-14)
        np.testing.assert_allclose(affine_state, recurrent_state, atol=2e-15, rtol=2e-14)

    def test_paired_heads_share_qk_but_not_value_state_or_gates(self) -> None:
        q = np.array([[1.0, 2.0]], dtype=np.float64)
        k = np.array([[3.0, 4.0]], dtype=np.float64)
        v = np.array([[1.0, 0.0], [0.0, 2.0]], dtype=np.float64)
        alpha = np.array([0.0, 1.0], dtype=np.float64)
        beta = np.array([1.0, 0.0], dtype=np.float64)
        state = np.zeros((2, 2, 2), dtype=np.float64)
        state[1] = np.eye(2)

        _, state_out = recurrence_step_fp64(q, k, v, alpha, beta, state)

        self.assertFalse(np.array_equal(state_out[0], state_out[1]))
        np.testing.assert_array_equal(state_out[1], state[1])

    def test_non_square_orientation_and_round_trip(self) -> None:
        state = np.arange(2 * 3 * 5, dtype=np.float64).reshape(2, 3, 5)
        v_by_k = state_kv_to_vk(state)

        self.assertEqual(v_by_k.shape, (2, 5, 3))
        np.testing.assert_array_equal(state_vk_to_kv(v_by_k), state)

    def test_gate_derivation_has_known_center_and_stable_extremes(self) -> None:
        alpha, beta = derive_alpha_beta_fp64(
            a=[0.0, -1000.0, 1000.0],
            b=[0.0, -1000.0, 1000.0],
            a_log=[0.0, 0.0, 0.0],
            dt_bias=[0.0, 0.0, 0.0],
        )

        self.assertAlmostEqual(float(beta[0]), 0.5, places=15)
        self.assertAlmostEqual(float(alpha[0]), 0.5, places=15)
        self.assertEqual(float(beta[1]), 0.0)
        self.assertEqual(float(beta[2]), 1.0)
        self.assertAlmostEqual(float(alpha[1]), 1.0, places=15)
        self.assertEqual(float(alpha[2]), 0.0)

    def test_invalid_head_ratio_and_gate_range_are_rejected(self) -> None:
        q = np.ones((2, 3), dtype=np.float64)
        k = np.ones((2, 3), dtype=np.float64)
        v = np.ones((3, 4), dtype=np.float64)
        state = np.ones((3, 3, 4), dtype=np.float64)

        with self.assertRaisesRegex(ValueError, "must be divisible"):
            recurrence_step_fp64(q, k, v, np.ones(3), np.ones(3), state)
        with self.assertRaisesRegex(ValueError, "alpha must be in"):
            recurrence_step_fp64(
                q[:1], k[:1], v[:2], np.array([1.0, 1.01]), np.ones(2), state[:2]
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

import numpy as np

from golden.gdn_oracle_fp64 import recurrence_step_fp64
from golden.gdn_write_log import (
    LazyWriteLogGDN,
    WriteLogConfiguration,
    quantize_mxfp4_stack,
    roundtrip_bf16,
)


def _core_step(
    q: np.ndarray,
    k: np.ndarray,
    v: np.ndarray,
    alpha: np.ndarray,
    beta: np.ndarray,
    state: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    heads_per_qk = state.shape[0] // q.shape[0]
    q_heads = np.repeat(q, heads_per_qk, axis=0)
    k_heads = np.repeat(k, heads_per_qk, axis=0)
    decayed = alpha[:, None, None] * state
    prediction = np.einsum("hk,hkv->hv", k_heads, decayed)
    update = beta[:, None] * (v - prediction)
    state_out = decayed + k_heads[:, :, None] * update[:, None, :]
    output = np.einsum("hk,hkv->hv", q_heads, state_out)
    return output, state_out


class TestLazyWriteLogGDN(unittest.TestCase):
    def test_rank_one_write_uses_official_positive_sign(self) -> None:
        engine = LazyWriteLogGDN(
            np.zeros((1, 1, 1), dtype=np.float64),
            num_qk_heads=1,
            config=WriteLogConfiguration(capacity=4, mode="exact"),
        )

        output, state = engine.step_core(
            np.ones((1, 1), dtype=np.float64),
            np.ones((1, 1), dtype=np.float64),
            np.array([[2.0]], dtype=np.float64),
            np.array([1.0], dtype=np.float64),
            np.array([0.5], dtype=np.float64),
        )

        np.testing.assert_array_equal(output, np.array([[1.0]]))
        np.testing.assert_array_equal(state, np.array([[[1.0]]]))

    def test_exact_core_matches_direct_recurrence_across_folds(self) -> None:
        rng = np.random.default_rng(0xFB72)
        initial = rng.normal(0.0, 0.2, size=(4, 3, 2))
        for capacity in (1, 2, 4):
            engine = LazyWriteLogGDN(
                initial,
                num_qk_heads=2,
                config=WriteLogConfiguration(capacity=capacity, mode="exact"),
            )
            direct_state = initial.copy()
            for _ in range(11):
                q = rng.normal(size=(2, 3))
                k = rng.normal(size=(2, 3))
                v = rng.normal(size=(4, 2))
                alpha = rng.uniform(0.2, 1.0, size=4)
                beta = rng.uniform(0.0, 1.0, size=4)
                expected_output, direct_state = _core_step(
                    q, k, v, alpha, beta, direct_state
                )
                output, state = engine.step_core(q, k, v, alpha, beta)
                np.testing.assert_allclose(output, expected_output, rtol=2e-13, atol=2e-13)
                np.testing.assert_allclose(state, direct_state, rtol=2e-13, atol=2e-13)

    def test_exact_raw_step_matches_independent_fp64_oracle(self) -> None:
        rng = np.random.default_rng(0xA11CE)
        initial = rng.normal(0.0, 0.1, size=(4, 3, 2))
        engine = LazyWriteLogGDN(
            initial,
            num_qk_heads=2,
            config=WriteLogConfiguration(capacity=3, mode="exact"),
        )
        direct_state = initial.copy()
        for _ in range(7):
            q = rng.normal(size=(2, 3))
            k = rng.normal(size=(2, 3))
            v = rng.normal(size=(4, 2))
            alpha = rng.uniform(0.0, 1.0, size=4)
            beta = rng.uniform(0.0, 1.0, size=4)
            expected_output, direct_state = recurrence_step_fp64(
                q, k, v, alpha, beta, direct_state
            )
            output, state = engine.step(q, k, v, alpha, beta)
            np.testing.assert_allclose(output, expected_output, rtol=2e-13, atol=2e-13)
            np.testing.assert_allclose(state, direct_state, rtol=2e-13, atol=2e-13)

    def test_paired_keys_and_full_log_never_drop_writes(self) -> None:
        engine = LazyWriteLogGDN(
            np.zeros((4, 2, 3), dtype=np.float64),
            num_qk_heads=2,
            config=WriteLogConfiguration(capacity=4, mode="exact"),
        )
        q = np.ones((2, 2), dtype=np.float64)
        k = np.ones((2, 2), dtype=np.float64)
        v = np.ones((4, 3), dtype=np.float64)
        alpha = np.ones(4, dtype=np.float64)
        beta = np.full(4, 0.5, dtype=np.float64)

        for _ in range(9):
            engine.step_core(q, k, v, alpha, beta)

        self.assertEqual(engine.keys.shape, (4, 2, 2))
        self.assertEqual(engine.counters.appended_entries, 9)
        self.assertEqual(engine.counters.folds, 2)
        self.assertEqual(engine.counters.max_live_entries, 4)
        self.assertEqual(engine.counters.dropped_entries, 0)
        self.assertEqual(engine.live_entries, 1)

    def test_pure_decay_does_not_requantize_base_every_token(self) -> None:
        initial = np.arange(24, dtype=np.float64).reshape(4, 2, 3) / 32.0
        engine = LazyWriteLogGDN(
            initial,
            num_qk_heads=2,
            config=WriteLogConfiguration(capacity=4, mode="exact"),
        )
        q = np.ones((2, 2), dtype=np.float64)
        k = np.ones((2, 2), dtype=np.float64)
        v = np.zeros((4, 3), dtype=np.float64)
        alpha = np.full(4, 0.5, dtype=np.float64)
        beta = np.zeros(4, dtype=np.float64)

        for token in range(3):
            _, state = engine.step_core(q, k, v, alpha, beta)
            self.assertEqual(engine.counters.folds, 0)
            np.testing.assert_allclose(state, initial * (0.5 ** (token + 1)))
        engine.step_core(q, k, v, alpha, beta)
        self.assertEqual(engine.counters.folds, 1)

    def test_decay_threshold_fold_is_bounded_and_no_drop(self) -> None:
        engine = LazyWriteLogGDN(
            np.zeros((2, 2, 2), dtype=np.float64),
            num_qk_heads=1,
            config=WriteLogConfiguration(
                capacity=8,
                mode="exact",
                fold_policy="decay_threshold",
                adaptive_min_entries=2,
                fold_decay_threshold=0.9,
            ),
        )
        q = np.ones((1, 2), dtype=np.float64)
        k = np.ones((1, 2), dtype=np.float64)
        v = np.zeros((2, 2), dtype=np.float64)
        alpha = np.full(2, 0.95, dtype=np.float64)
        beta = np.zeros(2, dtype=np.float64)
        for _ in range(6):
            engine.step_core(q, k, v, alpha, beta)
        self.assertEqual(engine.counters.folds, 2)
        self.assertEqual(engine.counters.max_live_entries, 3)
        self.assertEqual(engine.counters.dropped_entries, 0)

    def test_quantized_coefficient_underflow_rebases_atomically(self) -> None:
        engine = LazyWriteLogGDN(
            np.ones((2, 2, 2), dtype=np.float32),
            num_qk_heads=1,
            config=WriteLogConfiguration(
                capacity=16,
                mode="mxfp4",
                activation_block_size=16,
                base_block_size=16,
                log_block_size=16,
            ),
        )
        q = np.ones((1, 2), dtype=np.float32)
        k = np.ones((1, 2), dtype=np.float32)
        v = np.zeros((2, 2), dtype=np.float32)
        beta = np.zeros(2, dtype=np.float32)
        tiny_alpha = np.full(2, 1.0 / 32768.0, dtype=np.float32)

        for _ in range(12):
            _, state = engine.step(q, k, v, tiny_alpha, beta)

        self.assertGreaterEqual(engine.counters.coefficient_rebases, 1)
        self.assertEqual(engine.counters.dropped_entries, 0)
        self.assertTrue(np.all(np.isfinite(state)))

    def test_quantized_execution_is_deterministic(self) -> None:
        rng = np.random.default_rng(0xC0FFEE)
        initial = rng.normal(size=(2, 4, 4)).astype(np.float32)
        config = WriteLogConfiguration(
            capacity=4,
            mode="mxfp4",
            activation_block_size=16,
            base_block_size=16,
            log_block_size=16,
            log_precision="mxfp8_e4m3",
        )
        engines = [
            LazyWriteLogGDN(initial, num_qk_heads=1, config=config),
            LazyWriteLogGDN(initial, num_qk_heads=1, config=config),
        ]
        inputs = []
        for _ in range(8):
            inputs.append(
                (
                    rng.normal(size=(1, 4)).astype(np.float32),
                    rng.normal(size=(1, 4)).astype(np.float32),
                    rng.normal(size=(2, 4)).astype(np.float32),
                    rng.uniform(0.8, 1.0, size=2).astype(np.float32),
                    rng.uniform(0.0, 1.0, size=2).astype(np.float32),
                )
            )
        results = [[engine.step(*values) for values in inputs] for engine in engines]
        for left, right in zip(results[0], results[1]):
            np.testing.assert_array_equal(left[0], right[0])
            np.testing.assert_array_equal(left[1], right[1])

    def test_second_mxfp4_residual_term_reduces_roundtrip_error(self) -> None:
        rng = np.random.default_rng(0x5EED5)
        values = rng.normal(size=(4, 32)).astype(np.float32)
        one_term = quantize_mxfp4_stack(values, block_size=32, depth=1)
        two_term = quantize_mxfp4_stack(values, block_size=32, depth=2)
        one_error = np.linalg.norm(one_term - values)
        two_error = np.linalg.norm(two_term - values)
        self.assertLess(two_error, one_error)

    def test_sparse_second_term_has_intermediate_error(self) -> None:
        rng = np.random.default_rng(0xB10C)
        values = rng.normal(size=(4, 64)).astype(np.float32)
        one_term = quantize_mxfp4_stack(values, block_size=16, depth=1)
        sparse = quantize_mxfp4_stack(
            values,
            block_size=16,
            depth=2,
            residual_block_fraction=0.5,
        )
        dense = quantize_mxfp4_stack(values, block_size=16, depth=2)
        one_error = np.linalg.norm(one_term - values)
        sparse_error = np.linalg.norm(sparse - values)
        dense_error = np.linalg.norm(dense - values)
        self.assertLess(sparse_error, one_error)
        self.assertGreater(sparse_error, dense_error)

    def test_bf16_roundtrip_uses_ties_to_even(self) -> None:
        one_bits = np.array([0x3F800000], dtype=np.uint32).view(np.float32)
        halfway_even = np.array([0x3F808000], dtype=np.uint32).view(np.float32)
        halfway_odd = np.array([0x3F818000], dtype=np.uint32).view(np.float32)
        rounded = roundtrip_bf16(np.concatenate([one_bits, halfway_even, halfway_odd]))
        expected = np.array([0x3F800000, 0x3F800000, 0x3F820000], dtype=np.uint32).view(
            np.float32
        )
        np.testing.assert_array_equal(rounded, expected)


if __name__ == "__main__":
    unittest.main()

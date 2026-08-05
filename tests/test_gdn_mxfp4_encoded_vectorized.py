from __future__ import annotations

import numpy as np

from golden.gdn_mxfp4_encoded import (
    encode_state,
    encode_token,
    recurrence_core_step_encoded,
)
from golden.gdn_mxfp4_encoded_vectorized import (
    _aligned_sum_last,
    _round_shift_rne_array,
    recurrence_core_step_encoded_vectorized,
)


def _assert_step_equal(scalar: object, vectorized: object) -> None:
    assert np.array_equal(
        scalar.output_mantissas, vectorized.output_mantissas
    )
    assert np.array_equal(scalar.output_exponents, vectorized.output_exponents)
    assert np.array_equal(scalar.output_fp32, vectorized.output_fp32)
    assert np.array_equal(scalar.updated_mantissas, vectorized.updated_mantissas)
    assert np.array_equal(scalar.updated_exponents, vectorized.updated_exponents)
    assert np.array_equal(scalar.state.elements, vectorized.state.elements)
    assert np.array_equal(scalar.state.scales, vectorized.state.scales)
    assert scalar.counters.as_dict() == vectorized.counters.as_dict()


def test_vectorized_rne_and_ordered_saturation_helpers() -> None:
    values = np.array(
        [-17, -15, -13, -3, -1, 0, 1, 3, 13, 15, 17], dtype=np.int64
    )
    shifts = np.array([2, 2, 2, 1, 1, 0, 1, 1, 2, 2, 2], dtype=np.int64)
    assert _round_shift_rne_array(values, shifts).tolist() == [
        -4,
        -4,
        -3,
        -2,
        0,
        0,
        0,
        2,
        3,
        4,
        4,
    ]

    from golden.gdn_mxfp4_encoded import ArithmeticCounters, INT32_MAX

    counters = ArithmeticCounters()
    reduced, exponents = _aligned_sum_last(
        np.array([[INT32_MAX, 1, -1]], dtype=np.int64),
        np.zeros((1, 3), dtype=np.int16),
        counters,
    )
    assert reduced.tolist() == [INT32_MAX - 1]
    assert exponents.tolist() == [0]
    assert counters.accumulator_saturations == 1


def test_vectorized_matches_scalar_across_multitoken_random_state() -> None:
    rng = np.random.default_rng(0xFB72)
    scalar_state = encode_state(
        rng.normal(0.0, 0.08, size=(4, 16, 16)).astype(np.float32),
        block_size=16,
    )
    vectorized_state = scalar_state

    for token_index in range(4):
        q = rng.normal(0.0, 0.1, size=(2, 16)).astype(np.float32)
        k = rng.normal(0.0, 0.1, size=(2, 16)).astype(np.float32)
        v = rng.normal(0.0, 0.1, size=(4, 16)).astype(np.float32)
        alpha = rng.uniform(0.85, 1.0, size=4).astype(np.float32)
        beta = rng.uniform(0.0, 1.0, size=4).astype(np.float32)
        if token_index == 0:
            alpha[0], beta[0] = 0.0, 1.0
            alpha[1], beta[1] = 1.0, 0.0
        encoded = encode_token(q, k, v, alpha, beta, block_size=16)

        scalar = recurrence_core_step_encoded(encoded, scalar_state)
        vectorized = recurrence_core_step_encoded_vectorized(
            encoded, vectorized_state
        )
        _assert_step_equal(scalar, vectorized)
        scalar_state = scalar.state
        vectorized_state = vectorized.state


def test_vectorized_matches_scalar_with_extreme_scales_and_cancellation() -> None:
    q = np.zeros((1, 16), dtype=np.float32)
    k = np.zeros((1, 16), dtype=np.float32)
    v = np.zeros((2, 16), dtype=np.float32)
    q[0, :4] = [2.0**20, -(2.0**-20), 3.0, -3.0]
    k[0, :4] = [-(2.0**18), 2.0**-18, 4.0, -4.0]
    v[0, :4] = [2.0**24, -(2.0**-24), 6.0, -6.0]
    v[1] = -v[0]
    state_array = np.zeros((2, 16, 16), dtype=np.float32)
    state_array[:, :4, :4] = np.array(
        [
            [2.0**16, -(2.0**-16), 5.0, -5.0],
            [-(2.0**16), 2.0**-16, -5.0, 5.0],
            [3.0, -3.0, 2.0**8, -(2.0**-8)],
            [-3.0, 3.0, -(2.0**8), 2.0**-8],
        ],
        dtype=np.float32,
    )
    state = encode_state(state_array, block_size=16)
    token = encode_token(
        q,
        k,
        v,
        np.array([1.0, 0.5], dtype=np.float32),
        np.array([1.0, 1.0], dtype=np.float32),
        block_size=16,
    )

    scalar = recurrence_core_step_encoded(token, state)
    vectorized = recurrence_core_step_encoded_vectorized(token, state)
    _assert_step_equal(scalar, vectorized)

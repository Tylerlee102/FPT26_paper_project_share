from __future__ import annotations

import numpy as np

from golden.gdn_rs2_encoded import (
    EncodedRS2WriteLogGDN,
    decode_rs2_state,
    encode_rs2_state,
    encode_rs2_token,
)
from golden.gdn_rs2_encoded_vectorized import EncodedRS2WriteLogGDNVectorized
from golden.gdn_e2m0_encoded import _aligned_sum_guarded
from golden.gdn_e2m0_encoded_vectorized import _aligned_sum_last_guarded
from golden.gdn_mxfp4_encoded import ArithmeticCounters


def _inputs(rng: np.random.Generator):
    return (
        rng.normal(size=(1, 4)).astype(np.float32),
        rng.normal(size=(1, 4)).astype(np.float32),
        rng.normal(size=(2, 4)).astype(np.float32),
        rng.uniform(0.9, 1.0, size=2).astype(np.float32),
        rng.uniform(0.0, 1.0, size=2).astype(np.float32),
    )


def test_rs2_state_roundtrip_is_finite_and_two_term() -> None:
    rng = np.random.default_rng(0xFB72)
    source = rng.normal(size=(2, 4, 17)).astype(np.float32)
    encoded = encode_rs2_state(source, block_size=16)
    decoded = decode_rs2_state(encoded)
    assert encoded.elements.shape == (2, 2, 4, 17)
    assert encoded.scales.shape == (2, 2, 4, 2)
    assert np.all(np.isfinite(decoded))
    assert np.linalg.norm(decoded - source) < np.linalg.norm(source)


def test_scalar_and_vectorized_rs2_executors_are_bit_exact() -> None:
    rng = np.random.default_rng(0xC0DEC0DE)
    initial = encode_rs2_state(
        rng.normal(size=(2, 4, 4)).astype(np.float32), block_size=16
    )
    scalar = EncodedRS2WriteLogGDN(initial, num_qk_heads=1, capacity=2)
    vectorized = EncodedRS2WriteLogGDNVectorized(
        initial, num_qk_heads=1, capacity=2
    )
    for token_index in range(4):
        token = encode_rs2_token(*_inputs(rng), block_size=16)
        left = scalar.step(token)
        right = vectorized.step(token)
        np.testing.assert_array_equal(left.output_mantissas, right.output_mantissas)
        np.testing.assert_array_equal(left.output_exponents, right.output_exponents)
        np.testing.assert_array_equal(left.output_fp32, right.output_fp32)
        np.testing.assert_array_equal(
            left.materialized_state_fp32, right.materialized_state_fp32
        )
        assert left.counters.as_dict() == right.counters.as_dict()
        assert left.folded == right.folded == ((token_index + 1) % 2 == 0)
        assert left.live_entries == right.live_entries == ((token_index + 1) % 2)
        np.testing.assert_array_equal(scalar.base.elements, vectorized.base.elements)
        np.testing.assert_array_equal(scalar.base.scales, vectorized.base.scales)


def test_guarded_alignment_fast_path_matches_scalar_with_saturation() -> None:
    mantissas = np.asarray(
        [
            [1 << 30, 1 << 30, -(1 << 29), 17],
            [3, -7, 9, -11],
        ],
        dtype=np.int64,
    )
    exponents = np.asarray(
        [
            [0, 0, 0, -8],
            [4, 1, 0, -3],
        ],
        dtype=np.int16,
    )
    scalar_counters = ArithmeticCounters()
    expected_m = []
    expected_x = []
    for row in range(mantissas.shape[0]):
        value_m, value_x = _aligned_sum_guarded(
            mantissas[row],
            exponents[row],
            scalar_counters,
        )
        expected_m.append(value_m)
        expected_x.append(value_x)
    vector_counters = ArithmeticCounters()
    actual_m, actual_x = _aligned_sum_last_guarded(
        mantissas, exponents, vector_counters
    )
    np.testing.assert_array_equal(actual_m, np.asarray(expected_m))
    np.testing.assert_array_equal(actual_x, np.asarray(expected_x))
    assert vector_counters.as_dict() == scalar_counters.as_dict()

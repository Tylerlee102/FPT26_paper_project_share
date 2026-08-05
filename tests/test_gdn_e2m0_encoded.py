from __future__ import annotations

import numpy as np
import pytest

from golden.gdn_e2m0_encoded import (
    EncodedE2M0State,
    EncodedE2M0WriteLogGDN,
    _decode_e2m0_integer,
    _encode_e2m0_float,
    _stack_from_float,
    decode_e2m0_state,
    decode_stack,
    encode_e2m0_state,
    encode_e2m0_token,
)
from golden.gdn_e2m0_residual import (
    quantize_e2m0_residual,
    quantize_mxfp4_e2m0_stack,
)
from golden.gdn_write_log import quantize_mxfp4_stack


def _sparse_token(*, alpha: float = 1.0, beta: float = 1.0):
    q = np.asarray([[0.5, 0.0]], dtype=np.float32)
    k = np.asarray([[1.0, 0.0]], dtype=np.float32)
    v = np.asarray(
        [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32
    )
    return encode_e2m0_token(
        q,
        k,
        v,
        np.full(2, alpha, dtype=np.float32),
        np.full(2, beta, dtype=np.float32),
        block_size=32,
    )


def test_e2m0_float_encoding_matches_frozen_qdq() -> None:
    rng = np.random.default_rng(123)
    values = rng.normal(0.0, 0.2, size=(3, 37)).astype(np.float32)
    elements, scales = _encode_e2m0_float(values, block_size=32)
    mantissas, exponents = _decode_e2m0_integer(
        "test", elements, scales, 32
    )
    reconstructed = np.ldexp(mantissas.astype(np.float64), exponents).astype(
        np.float32
    )
    expected = quantize_e2m0_residual(values, block_size=32)
    np.testing.assert_array_equal(reconstructed, expected)


def test_two_term_stack_matches_frozen_qdq() -> None:
    rng = np.random.default_rng(321)
    values = rng.normal(size=(4, 35)).astype(np.float32)
    encoded = _stack_from_float(values, block_size=32)
    np.testing.assert_array_equal(
        decode_stack(encoded),
        quantize_mxfp4_stack(values, block_size=32, depth=2),
    )


def test_state_encoding_matches_frozen_qdq() -> None:
    rng = np.random.default_rng(7)
    values = rng.normal(0.0, 0.1, size=(2, 3, 35)).astype(np.float32)
    encoded = encode_e2m0_state(values, block_size=32)
    np.testing.assert_array_equal(
        decode_e2m0_state(encoded),
        quantize_mxfp4_e2m0_stack(values, block_size=32, depth=2),
    )


def test_sparse_write_and_output_are_hand_computable() -> None:
    initial = encode_e2m0_state(
        np.zeros((2, 2, 3), dtype=np.float32), block_size=32
    )
    engine = EncodedE2M0WriteLogGDN(initial, num_qk_heads=1, capacity=7)
    result = engine.step(_sparse_token())

    expected_state = np.zeros((2, 2, 3), dtype=np.float32)
    expected_state[:, 0, 0] = 1.0
    expected_output = np.zeros((2, 3), dtype=np.float32)
    expected_output[:, 0] = 0.5
    np.testing.assert_array_equal(result.materialized_state_fp32, expected_state)
    np.testing.assert_array_equal(result.output_fp32, expected_output)
    assert result.live_entries == 1
    assert result.folded is False
    assert result.counters.accumulator_saturations == 0


def test_seventh_write_folds_atomically_without_dropping_state() -> None:
    initial = encode_e2m0_state(
        np.zeros((2, 2, 3), dtype=np.float32), block_size=32
    )
    engine = EncodedE2M0WriteLogGDN(initial, num_qk_heads=1, capacity=7)
    result = None
    for _ in range(7):
        result = engine.step(_sparse_token())
    assert result is not None
    assert result.folded is True
    assert result.live_entries == 0
    expected_state = np.zeros((2, 2, 3), dtype=np.float32)
    expected_state[:, 0, 0] = 1.0
    np.testing.assert_array_equal(result.materialized_state_fp32, expected_state)
    np.testing.assert_array_equal(decode_e2m0_state(engine.base), expected_state)


def test_zero_alpha_decays_base_and_live_log() -> None:
    initial_values = np.zeros((2, 2, 3), dtype=np.float32)
    initial_values[:, 1, 2] = 2.0
    engine = EncodedE2M0WriteLogGDN(
        encode_e2m0_state(initial_values, block_size=32),
        num_qk_heads=1,
        capacity=7,
    )
    engine.step(_sparse_token())
    zeroed = engine.step(_sparse_token(alpha=0.0, beta=0.0))
    np.testing.assert_array_equal(
        zeroed.materialized_state_fp32, np.zeros_like(initial_values)
    )


def test_invalid_e2m0_negative_zero_is_rejected() -> None:
    state = encode_e2m0_state(
        np.zeros((2, 2, 3), dtype=np.float32), block_size=32
    )
    bad = EncodedE2M0State(
        state.primary_elements,
        state.primary_scales,
        np.full_like(state.residual_elements, 4),
        state.residual_scales,
        state.block_size,
    )
    with pytest.raises(ValueError, match="invalid E2M0"):
        EncodedE2M0WriteLogGDN(bad, num_qk_heads=1)

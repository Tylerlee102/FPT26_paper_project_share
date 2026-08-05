from __future__ import annotations

import numpy as np

from golden.gdn_e2m0_encoded import (
    EncodedE2M0WriteLogGDN,
    encode_e2m0_state,
    encode_e2m0_token,
)
from golden.gdn_e2m0_encoded_vectorized import (
    EncodedE2M0WriteLogGDNVectorized,
)


def _assert_engine_equal(
    scalar: EncodedE2M0WriteLogGDN,
    vectorized: EncodedE2M0WriteLogGDNVectorized,
) -> None:
    assert scalar.live_entries == vectorized.live_entries
    np.testing.assert_array_equal(
        scalar.base.primary_elements, vectorized.base.primary_elements
    )
    np.testing.assert_array_equal(
        scalar.base.primary_scales, vectorized.base.primary_scales
    )
    np.testing.assert_array_equal(
        scalar.base.residual_elements, vectorized.base.residual_elements
    )
    np.testing.assert_array_equal(
        scalar.base.residual_scales, vectorized.base.residual_scales
    )
    np.testing.assert_array_equal(scalar.gamma_codes, vectorized.gamma_codes)
    np.testing.assert_array_equal(scalar.lambda_codes, vectorized.lambda_codes)
    np.testing.assert_array_equal(scalar.key_elements, vectorized.key_elements)
    np.testing.assert_array_equal(scalar.key_scales, vectorized.key_scales)
    np.testing.assert_array_equal(
        scalar.update_elements, vectorized.update_elements
    )
    np.testing.assert_array_equal(scalar.update_scales, vectorized.update_scales)


def test_vectorized_matches_scalar_across_folds_and_decay() -> None:
    rng = np.random.default_rng(0xE2A0)
    initial = rng.normal(0.0, 0.1, size=(4, 5, 7)).astype(np.float32)
    encoded_initial = encode_e2m0_state(initial, block_size=16)
    scalar = EncodedE2M0WriteLogGDN(
        encoded_initial, num_qk_heads=2, capacity=3
    )
    vectorized = EncodedE2M0WriteLogGDNVectorized(
        encoded_initial, num_qk_heads=2, capacity=3
    )

    for _ in range(8):
        q = rng.normal(0.0, 0.2, size=(2, 5)).astype(np.float32)
        k = rng.normal(0.0, 0.2, size=(2, 5)).astype(np.float32)
        v = rng.normal(0.0, 0.2, size=(4, 7)).astype(np.float32)
        alpha = rng.uniform(0.94, 1.0, size=4).astype(np.float32)
        beta = rng.uniform(0.0, 1.0, size=4).astype(np.float32)
        token = encode_e2m0_token(
            q, k, v, alpha, beta, block_size=16
        )
        scalar_result = scalar.step(token)
        vector_result = vectorized.step(token)
        np.testing.assert_array_equal(
            scalar_result.output_mantissas, vector_result.output_mantissas
        )
        np.testing.assert_array_equal(
            scalar_result.output_exponents, vector_result.output_exponents
        )
        np.testing.assert_array_equal(
            scalar_result.materialized_state_fp32,
            vector_result.materialized_state_fp32,
        )
        assert scalar_result.counters.as_dict() == vector_result.counters.as_dict()
        assert scalar_result.folded == vector_result.folded
        _assert_engine_equal(scalar, vectorized)

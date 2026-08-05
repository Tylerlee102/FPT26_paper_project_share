from __future__ import annotations

import numpy as np
import pytest

from golden.gdn_bf16 import gdn_decode_step, roundtrip_bf16
from golden.gdn_fp32 import gdn_recurrence_core_step, normalize_qk


def test_roundtrip_bf16_uses_round_to_nearest_even() -> None:
    one_bits = np.array([0x3F800000], dtype=np.uint32).view(np.float32)
    halfway_even = np.array([0x3F808000], dtype=np.uint32).view(np.float32)
    halfway_odd = np.array([0x3F818000], dtype=np.uint32).view(np.float32)
    rounded = roundtrip_bf16(
        np.concatenate([one_bits, halfway_even, halfway_odd])
    ).view(np.uint32)
    assert rounded.tolist() == [0x3F800000, 0x3F800000, 0x3F820000]


def test_step_matches_explicit_bf16_boundaries() -> None:
    generator = np.random.default_rng(0xB16)
    q = generator.normal(size=(1, 8)).astype(np.float32)
    k = generator.normal(size=(1, 8)).astype(np.float32)
    v = generator.normal(size=(2, 8)).astype(np.float32)
    alpha = np.array([0.97, 0.81], dtype=np.float32)
    beta = np.array([0.25, 1.0], dtype=np.float32)
    state = generator.normal(scale=0.1, size=(2, 8, 8)).astype(np.float32)

    output, updated = gdn_decode_step(q, k, v, alpha, beta, state)
    q_scaled, k_normalized = normalize_qk(q, k)
    expected_output, expected_state = gdn_recurrence_core_step(
        roundtrip_bf16(q_scaled),
        roundtrip_bf16(k_normalized),
        roundtrip_bf16(v),
        roundtrip_bf16(alpha),
        roundtrip_bf16(beta),
        roundtrip_bf16(state),
    )
    np.testing.assert_array_equal(output, roundtrip_bf16(expected_output))
    np.testing.assert_array_equal(updated, roundtrip_bf16(expected_state))
    assert np.all((output.view(np.uint32) & np.uint32(0xFFFF)) == 0)
    assert np.all((updated.view(np.uint32) & np.uint32(0xFFFF)) == 0)


def test_roundtrip_rejects_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        roundtrip_bf16(np.array([np.inf], dtype=np.float32))

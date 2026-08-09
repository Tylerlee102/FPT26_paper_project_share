"""Vectorized executor for the scalar residual-stack MXFP4 oracle."""

from __future__ import annotations

import numpy as np

from .gdn_e2m0_encoded import EncodedMXFP4Stack
from .gdn_e2m0_encoded_vectorized import (
    EncodedE2M0WriteLogGDNVectorized,
    _quantize_stack_exact_vectorized,
)
from .gdn_mxfp4_encoded import ArithmeticCounters
from .gdn_rs2_encoded import EncodedRS2State, EncodedRS2WriteLogGDN


class EncodedRS2WriteLogGDNVectorized(EncodedE2M0WriteLogGDNVectorized):
    """Vectorized RS2 executor using the scalar oracle's state contract."""

    def __init__(
        self,
        initial_state: EncodedRS2State,
        *,
        num_qk_heads: int,
        capacity: int = 2,
    ) -> None:
        EncodedRS2WriteLogGDN.__init__(
            self,
            initial_state,
            num_qk_heads=num_qk_heads,
            capacity=capacity,
        )

    def _decode_base(self) -> tuple[np.ndarray, np.ndarray]:
        return EncodedRS2WriteLogGDN._decode_base(self)

    def _new_counters(self) -> ArithmeticCounters:
        return ArithmeticCounters()

    def _quantize_base_exact_vectorized(
        self,
        mantissas: np.ndarray,
        exponents: np.ndarray,
        counters: ArithmeticCounters,
    ) -> EncodedMXFP4Stack:
        return _quantize_stack_exact_vectorized(
            mantissas,
            exponents,
            block_size=self.block_size,
            counters=counters,
        )

    def _base_scale_change_count(self, replacement: EncodedMXFP4Stack) -> int:
        return EncodedRS2WriteLogGDN._base_scale_change_count(self, replacement)

    def materialize_state_fp32(self) -> np.ndarray:
        return EncodedRS2WriteLogGDN.materialize_state_fp32(self)

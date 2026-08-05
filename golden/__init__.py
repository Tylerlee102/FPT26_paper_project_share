"""Golden software models for the Gated DeltaNet recurrence core."""

from .gdn_fp32 import (
    derive_alpha_beta,
    gdn_decode_sequence,
    gdn_decode_step,
    gdn_recurrence_core_step,
    normalize_qk,
)

__all__ = [
    "derive_alpha_beta",
    "gdn_decode_sequence",
    "gdn_decode_step",
    "gdn_recurrence_core_step",
    "normalize_qk",
]

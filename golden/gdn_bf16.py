"""BF16 Q/DQ diagnostic for the corrected GDN recurrence-core boundary.

Inputs and resident state are rounded to BF16 with round-to-nearest-even,
products and reductions execute in FP32, and the output and updated resident
state are rounded to BF16 at the kernel boundary. This is a software storage
and operand model, not bit-exact HLS or physical BF16 evidence.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from .gdn_fp32 import gdn_recurrence_core_step, normalize_qk


Array = np.ndarray


def roundtrip_bf16(values: object) -> Array:
    """Round finite FP32 values to BF16 using round-to-nearest-even."""

    array = np.asarray(values, dtype=np.float32)
    if not np.all(np.isfinite(array)):
        raise ValueError("BF16 values must be finite")
    bits = array.view(np.uint32)
    rounded = bits + np.uint32(0x7FFF) + (
        (bits >> np.uint32(16)) & np.uint32(1)
    )
    return (rounded & np.uint32(0xFFFF0000)).view(np.float32)


def gdn_decode_step(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
) -> Tuple[Array, Array]:
    """Execute one BF16-operand, FP32-accumulated recurrence-core token."""

    q_scaled, k_normalized = normalize_qk(q, k)
    output, updated_state = gdn_recurrence_core_step(
        roundtrip_bf16(q_scaled),
        roundtrip_bf16(k_normalized),
        roundtrip_bf16(v),
        roundtrip_bf16(alpha),
        roundtrip_bf16(beta),
        roundtrip_bf16(state_in),
    )
    return roundtrip_bf16(output), roundtrip_bf16(updated_state)

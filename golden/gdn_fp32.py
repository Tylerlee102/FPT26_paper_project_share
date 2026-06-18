"""FP32 Gated DeltaNet decode reference.

The state matrix maps keys to values for each head. For one decode token:

    S_t = S_{t-1} - beta_t * (S_{t-1} k_t - v_t) k_t^T
    y_t = gate_t * (S_t q_t)

Inputs are accepted as tensor-like objects and converted to NumPy float32 arrays.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


Array = np.ndarray


def _as_float32(name: str, value: object) -> Array:
    arr = np.asarray(value, dtype=np.float32)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN or Inf")
    return arr


def _validate_shapes(q: Array, k: Array, v: Array, beta: Array, gate: Array, state_in: Array) -> None:
    if q.ndim != 2:
        raise ValueError(f"q must have shape [num_heads, head_dim], got {q.shape}")
    if k.shape != q.shape:
        raise ValueError(f"k must match q shape {q.shape}, got {k.shape}")
    if v.shape != q.shape:
        raise ValueError(f"v must match q shape {q.shape}, got {v.shape}")
    if gate.shape != q.shape:
        raise ValueError(f"gate must match q shape {q.shape}, got {gate.shape}")

    num_heads, head_dim = q.shape
    if beta.shape != (num_heads,):
        raise ValueError(f"beta must have shape [{num_heads}], got {beta.shape}")
    if state_in.shape != (num_heads, head_dim, head_dim):
        raise ValueError(
            "state_in must have shape "
            f"[{num_heads}, {head_dim}, {head_dim}], got {state_in.shape}"
        )


def ungated_decode_step(
    q: object,
    k: object,
    v: object,
    beta: object,
    state_in: object,
) -> Tuple[Array, Array]:
    """Run one ungated GDN decode step in FP32.

    Returns:
        A tuple `(output, state_out)`, both NumPy float32 arrays.
    """

    q_arr = _as_float32("q", q)
    k_arr = _as_float32("k", k)
    v_arr = _as_float32("v", v)
    beta_arr = _as_float32("beta", beta)
    state_arr = _as_float32("state_in", state_in)
    gate_arr = np.ones_like(q_arr, dtype=np.float32)
    _validate_shapes(q_arr, k_arr, v_arr, beta_arr, gate_arr, state_arr)

    predicted_v = np.einsum("hij,hj->hi", state_arr, k_arr, dtype=np.float32)
    residual = predicted_v - v_arr
    update = beta_arr[:, None, None] * residual[:, :, None] * k_arr[:, None, :]
    state_out = state_arr - update.astype(np.float32)
    output = np.einsum("hij,hj->hi", state_out, q_arr, dtype=np.float32)
    return output.astype(np.float32), state_out.astype(np.float32)


def gdn_decode_step(
    q: object,
    k: object,
    v: object,
    beta: object,
    gate: object,
    state_in: object,
) -> Tuple[Array, Array]:
    """Run one gated GDN decode step in FP32.

    Args:
        q, k, v: Arrays with shape `[num_heads, head_dim]`.
        beta: Array with shape `[num_heads]`.
        gate: Array with shape `[num_heads, head_dim]`.
        state_in: Array with shape `[num_heads, head_dim, head_dim]`.

    Returns:
        `(output, state_out)` where output has shape `[num_heads, head_dim]` and
        state_out has shape `[num_heads, head_dim, head_dim]`.
    """

    q_arr = _as_float32("q", q)
    k_arr = _as_float32("k", k)
    v_arr = _as_float32("v", v)
    beta_arr = _as_float32("beta", beta)
    gate_arr = _as_float32("gate", gate)
    state_arr = _as_float32("state_in", state_in)
    _validate_shapes(q_arr, k_arr, v_arr, beta_arr, gate_arr, state_arr)

    ungated, state_out = ungated_decode_step(q_arr, k_arr, v_arr, beta_arr, state_arr)
    return (gate_arr * ungated).astype(np.float32), state_out


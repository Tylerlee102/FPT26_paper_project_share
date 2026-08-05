"""FP32 reference for the Qwen3-Next GDN recurrence-core boundary.

The logical state is K-by-V. Inputs to :func:`gdn_decode_step` are the
post-convolution q/k/v tensors. Q/K normalization and query scaling match the
pinned Transformers v4.57.0 fallback implementation. Gated RMSNorm and the
output projection are outside this module.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


Array = np.ndarray
L2_EPS = 1e-6


def _as_float32(name: str, value: object) -> Array:
    array = np.asarray(value, dtype=np.float32)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains NaN or Inf")
    return array


def _validate_step_shapes(
    q: Array,
    k: Array,
    v: Array,
    alpha: Array,
    beta: Array,
    state_in: Array,
) -> tuple[int, int, int, int]:
    if q.ndim != 2:
        raise ValueError(f"q must have shape [qk_heads, key_dim], got {q.shape}")
    if k.shape != q.shape:
        raise ValueError(f"k must match q shape {q.shape}, got {k.shape}")
    if v.ndim != 2:
        raise ValueError(f"v must have shape [value_heads, value_dim], got {v.shape}")

    qk_heads, key_dim = q.shape
    value_heads, value_dim = v.shape
    if qk_heads == 0 or value_heads == 0 or key_dim == 0 or value_dim == 0:
        raise ValueError("head counts and dimensions must be positive")
    if value_heads % qk_heads != 0:
        raise ValueError(
            f"value_heads ({value_heads}) must be divisible by qk_heads ({qk_heads})"
        )
    if alpha.shape != (value_heads,):
        raise ValueError(f"alpha must have shape [{value_heads}], got {alpha.shape}")
    if beta.shape != (value_heads,):
        raise ValueError(f"beta must have shape [{value_heads}], got {beta.shape}")
    if state_in.shape != (value_heads, key_dim, value_dim):
        raise ValueError(
            "state_in must have K-by-V shape "
            f"[{value_heads}, {key_dim}, {value_dim}], got {state_in.shape}"
        )
    if np.any(alpha < np.float32(0.0)) or np.any(alpha > np.float32(1.0)):
        raise ValueError("alpha must be in [0, 1]")
    if np.any(beta < np.float32(0.0)) or np.any(beta > np.float32(1.0)):
        raise ValueError("beta must be in [0, 1]")
    return qk_heads, value_heads, key_dim, value_dim


def derive_alpha_beta(
    a: object,
    b: object,
    a_log: object,
    dt_bias: object,
) -> Tuple[Array, Array]:
    """Derive `alpha=exp(g)` and `beta=sigmoid(b)` in FP32."""

    a_array = _as_float32("a", a)
    b_array = _as_float32("b", b)
    a_log_array = _as_float32("a_log", a_log)
    dt_bias_array = _as_float32("dt_bias", dt_bias)
    if not (a_array.shape == b_array.shape == a_log_array.shape == dt_bias_array.shape):
        raise ValueError("a, b, a_log, and dt_bias must have identical shapes")

    softplus_input = a_array + dt_bias_array
    softplus = np.maximum(softplus_input, np.float32(0.0)) + np.log1p(
        np.exp(-np.abs(softplus_input))
    )
    g = -np.exp(a_log_array) * softplus
    alpha = np.exp(g).astype(np.float32)

    beta = np.empty_like(b_array)
    nonnegative = b_array >= np.float32(0.0)
    beta[nonnegative] = np.float32(1.0) / (
        np.float32(1.0) + np.exp(-b_array[nonnegative])
    )
    exp_b = np.exp(b_array[~nonnegative])
    beta[~nonnegative] = exp_b / (np.float32(1.0) + exp_b)
    return alpha, beta.astype(np.float32)


def normalize_qk(
    q: object,
    k: object,
    *,
    eps: float = L2_EPS,
) -> Tuple[Array, Array]:
    """Normalize Q/K and apply the official `1/sqrt(key_dim)` query scale."""

    if not np.isfinite(eps) or eps <= 0.0:
        raise ValueError("eps must be finite and positive")
    q_array = _as_float32("q", q)
    k_array = _as_float32("k", k)
    if q_array.ndim != 2 or k_array.shape != q_array.shape:
        raise ValueError("q and k must have matching [qk_heads, key_dim] shapes")
    if q_array.shape[0] == 0 or q_array.shape[1] == 0:
        raise ValueError("q and k dimensions must be positive")

    eps32 = np.float32(eps)
    q_inverse_norm = np.float32(1.0) / np.sqrt(
        np.sum(q_array * q_array, axis=-1, keepdims=True, dtype=np.float32) + eps32
    )
    k_inverse_norm = np.float32(1.0) / np.sqrt(
        np.sum(k_array * k_array, axis=-1, keepdims=True, dtype=np.float32) + eps32
    )
    query_scale = np.float32(1.0 / np.sqrt(float(q_array.shape[-1])))
    return (
        (q_array * q_inverse_norm * query_scale).astype(np.float32),
        (k_array * k_inverse_norm).astype(np.float32),
    )


def gdn_recurrence_core_step(
    q_scaled: object,
    k_normalized: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
) -> Tuple[Array, Array]:
    """Execute one token at the frozen recurrence-core hardware boundary."""

    q_array = _as_float32("q_scaled", q_scaled)
    k_array = _as_float32("k_normalized", k_normalized)
    v_array = _as_float32("v", v)
    alpha_array = _as_float32("alpha", alpha)
    beta_array = _as_float32("beta", beta)
    state_array = _as_float32("state_in", state_in)
    qk_heads, value_heads, _, _ = _validate_step_shapes(
        q_array, k_array, v_array, alpha_array, beta_array, state_array
    )

    heads_per_qk = value_heads // qk_heads
    q_per_value_head = np.repeat(q_array, heads_per_qk, axis=0)
    k_per_value_head = np.repeat(k_array, heads_per_qk, axis=0)

    state_decay = (state_array * alpha_array[:, None, None]).astype(np.float32)
    prediction = np.einsum(
        "hk,hkv->hv", k_per_value_head, state_decay, dtype=np.float32
    )
    delta = ((v_array - prediction) * beta_array[:, None]).astype(np.float32)
    state_out = (
        state_decay + k_per_value_head[:, :, None] * delta[:, None, :]
    ).astype(np.float32)
    output = np.einsum(
        "hk,hkv->hv", q_per_value_head, state_out, dtype=np.float32
    ).astype(np.float32)
    return output, state_out


def gdn_decode_step(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
    *,
    eps: float = L2_EPS,
) -> Tuple[Array, Array]:
    """Normalize Q/K and execute one official Qwen3-Next GDN token."""

    q_scaled, k_normalized = normalize_qk(q, k, eps=eps)
    return gdn_recurrence_core_step(
        q_scaled, k_normalized, v, alpha, beta, state_in
    )


def gdn_decode_sequence(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
    *,
    eps: float = L2_EPS,
) -> Tuple[Array, Array]:
    """Execute contiguous tokens through the same recurrent step boundary."""

    q_array = _as_float32("q", q)
    k_array = _as_float32("k", k)
    v_array = _as_float32("v", v)
    alpha_array = _as_float32("alpha", alpha)
    beta_array = _as_float32("beta", beta)
    if q_array.ndim != 3:
        raise ValueError(f"q must have shape [tokens, qk_heads, key_dim], got {q_array.shape}")
    tokens = q_array.shape[0]
    if k_array.shape != q_array.shape:
        raise ValueError(f"k must match q shape {q_array.shape}, got {k_array.shape}")
    if v_array.ndim != 3 or v_array.shape[0] != tokens:
        raise ValueError("v must have shape [tokens, value_heads, value_dim]")
    if alpha_array.shape != v_array.shape[:2] or beta_array.shape != v_array.shape[:2]:
        raise ValueError("alpha and beta must have shape [tokens, value_heads]")

    state = _as_float32("state_in", state_in).copy()
    outputs = np.empty((tokens, v_array.shape[1], v_array.shape[2]), dtype=np.float32)
    for token in range(tokens):
        outputs[token], state = gdn_decode_step(
            q_array[token],
            k_array[token],
            v_array[token],
            alpha_array[token],
            beta_array[token],
            state,
            eps=eps,
        )
    return outputs, state


def state_kv_to_vk(state: object) -> Array:
    """Convert logical K-by-V state to an explicit V-by-K physical layout."""

    state_array = _as_float32("state", state)
    if state_array.ndim < 2:
        raise ValueError("state must have at least two dimensions")
    return np.swapaxes(state_array, -2, -1).copy()


def state_vk_to_kv(state: object) -> Array:
    """Convert V-by-K physical state back to logical K-by-V."""

    state_array = _as_float32("state", state)
    if state_array.ndim < 2:
        raise ValueError("state must have at least two dimensions")
    return np.swapaxes(state_array, -2, -1).copy()

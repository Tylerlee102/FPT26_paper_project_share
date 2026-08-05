"""Independent FP64 oracle for the Qwen3-Next GDN recurrence core.

This module intentionally does not import the production FP32 implementation.
The token recurrence uses explicit scalar loops. The sequence cross-check uses
an independently derived affine state transition.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


Array = np.ndarray
L2_EPS = 1e-6


def _as_finite_float64(name: str, value: object) -> Array:
    array = np.asarray(value, dtype=np.float64)
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
    if np.any(alpha < 0.0) or np.any(alpha > 1.0):
        raise ValueError("alpha must be in [0, 1]")
    if np.any(beta < 0.0) or np.any(beta > 1.0):
        raise ValueError("beta must be in [0, 1]")
    return qk_heads, value_heads, key_dim, value_dim


def _normalize_vector(vector: Array, eps: float) -> Array:
    squared_norm = 0.0
    for value in vector:
        squared_norm += float(value) * float(value)
    inverse_norm = 1.0 / np.sqrt(squared_norm + eps)
    return vector * inverse_norm


def derive_alpha_beta_fp64(
    a: object,
    b: object,
    a_log: object,
    dt_bias: object,
) -> Tuple[Array, Array]:
    """Derive official per-value-head alpha and beta in FP64."""

    a_array = _as_finite_float64("a", a)
    b_array = _as_finite_float64("b", b)
    a_log_array = _as_finite_float64("a_log", a_log)
    dt_bias_array = _as_finite_float64("dt_bias", dt_bias)
    if not (a_array.shape == b_array.shape == a_log_array.shape == dt_bias_array.shape):
        raise ValueError("a, b, a_log, and dt_bias must have identical shapes")

    softplus_input = a_array + dt_bias_array
    softplus = np.maximum(softplus_input, 0.0) + np.log1p(np.exp(-np.abs(softplus_input)))
    g = -np.exp(a_log_array) * softplus
    alpha = np.exp(g)

    beta = np.empty_like(b_array)
    nonnegative = b_array >= 0.0
    beta[nonnegative] = 1.0 / (1.0 + np.exp(-b_array[nonnegative]))
    exp_b = np.exp(b_array[~nonnegative])
    beta[~nonnegative] = exp_b / (1.0 + exp_b)
    return alpha, beta


def recurrence_step_fp64(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
    *,
    eps: float = L2_EPS,
) -> Tuple[Array, Array]:
    """Execute one official GDN token using explicit FP64 scalar loops.

    `q` and `k` are post-convolution tensors before recurrence normalization.
    The logical state is `[value_heads, key_dim, value_dim]` (K-by-V).
    """

    if not np.isfinite(eps) or eps <= 0.0:
        raise ValueError("eps must be finite and positive")
    q_array = _as_finite_float64("q", q)
    k_array = _as_finite_float64("k", k)
    v_array = _as_finite_float64("v", v)
    alpha_array = _as_finite_float64("alpha", alpha)
    beta_array = _as_finite_float64("beta", beta)
    state_array = _as_finite_float64("state_in", state_in)
    qk_heads, value_heads, key_dim, value_dim = _validate_step_shapes(
        q_array, k_array, v_array, alpha_array, beta_array, state_array
    )

    heads_per_qk = value_heads // qk_heads
    output = np.zeros((value_heads, value_dim), dtype=np.float64)
    state_out = np.empty_like(state_array)

    for value_head in range(value_heads):
        qk_head = value_head // heads_per_qk
        q_normalized = _normalize_vector(q_array[qk_head], eps) / np.sqrt(float(key_dim))
        k_normalized = _normalize_vector(k_array[qk_head], eps)

        decayed = np.empty((key_dim, value_dim), dtype=np.float64)
        for key_index in range(key_dim):
            for value_index in range(value_dim):
                decayed[key_index, value_index] = (
                    alpha_array[value_head] * state_array[value_head, key_index, value_index]
                )

        prediction = np.zeros(value_dim, dtype=np.float64)
        for value_index in range(value_dim):
            for key_index in range(key_dim):
                prediction[value_index] += (
                    k_normalized[key_index] * decayed[key_index, value_index]
                )

        delta = np.empty(value_dim, dtype=np.float64)
        for value_index in range(value_dim):
            delta[value_index] = beta_array[value_head] * (
                v_array[value_head, value_index] - prediction[value_index]
            )

        for key_index in range(key_dim):
            for value_index in range(value_dim):
                state_out[value_head, key_index, value_index] = (
                    decayed[key_index, value_index]
                    + k_normalized[key_index] * delta[value_index]
                )

        for value_index in range(value_dim):
            for key_index in range(key_dim):
                output[value_head, value_index] += (
                    q_normalized[key_index]
                    * state_out[value_head, key_index, value_index]
                )

    return output, state_out


def recurrence_sequence_fp64(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
    *,
    eps: float = L2_EPS,
) -> Tuple[Array, Array]:
    """Execute a sequence token-by-token using the scalar oracle."""

    q_array = _as_finite_float64("q", q)
    k_array = _as_finite_float64("k", k)
    v_array = _as_finite_float64("v", v)
    alpha_array = _as_finite_float64("alpha", alpha)
    beta_array = _as_finite_float64("beta", beta)
    if q_array.ndim != 3:
        raise ValueError(f"q must have shape [tokens, qk_heads, key_dim], got {q_array.shape}")
    tokens = q_array.shape[0]
    if k_array.shape != q_array.shape:
        raise ValueError(f"k must match q shape {q_array.shape}, got {k_array.shape}")
    if v_array.ndim != 3 or v_array.shape[0] != tokens:
        raise ValueError("v must have shape [tokens, value_heads, value_dim]")
    if alpha_array.shape != v_array.shape[:2] or beta_array.shape != v_array.shape[:2]:
        raise ValueError("alpha and beta must have shape [tokens, value_heads]")

    state = _as_finite_float64("state_in", state_in).copy()
    outputs = np.empty((tokens, v_array.shape[1], v_array.shape[2]), dtype=np.float64)
    for token in range(tokens):
        outputs[token], state = recurrence_step_fp64(
            q_array[token],
            k_array[token],
            v_array[token],
            alpha_array[token],
            beta_array[token],
            state,
            eps=eps,
        )
    return outputs, state


def affine_scan_sequence_fp64(
    q: object,
    k: object,
    v: object,
    alpha: object,
    beta: object,
    state_in: object,
    *,
    eps: float = L2_EPS,
) -> Tuple[Array, Array]:
    """Cross-check a sequence through independently derived affine operators.

    For each token, `S_t = A_t @ S_(t-1) + B_t`, where
    `A_t = alpha_t * (I - beta_t * k_t k_t^T)` and
    `B_t = beta_t * k_t v_t^T`.
    """

    q_array = _as_finite_float64("q", q)
    k_array = _as_finite_float64("k", k)
    v_array = _as_finite_float64("v", v)
    alpha_array = _as_finite_float64("alpha", alpha)
    beta_array = _as_finite_float64("beta", beta)
    state = _as_finite_float64("state_in", state_in).copy()
    if q_array.ndim != 3 or k_array.shape != q_array.shape:
        raise ValueError("q and k must have matching [tokens, qk_heads, key_dim] shapes")
    tokens, qk_heads, key_dim = q_array.shape
    if v_array.ndim != 3 or v_array.shape[0] != tokens:
        raise ValueError("v must have shape [tokens, value_heads, value_dim]")
    value_heads, value_dim = v_array.shape[1:]
    if value_heads % qk_heads != 0:
        raise ValueError("value_heads must be divisible by qk_heads")
    if alpha_array.shape != (tokens, value_heads) or beta_array.shape != (tokens, value_heads):
        raise ValueError("alpha and beta must have shape [tokens, value_heads]")
    if state.shape != (value_heads, key_dim, value_dim):
        raise ValueError("state_in has the wrong K-by-V shape")
    if np.any(alpha_array < 0.0) or np.any(alpha_array > 1.0):
        raise ValueError("alpha must be in [0, 1]")
    if np.any(beta_array < 0.0) or np.any(beta_array > 1.0):
        raise ValueError("beta must be in [0, 1]")

    heads_per_qk = value_heads // qk_heads
    outputs = np.empty((tokens, value_heads, value_dim), dtype=np.float64)
    identity = np.eye(key_dim, dtype=np.float64)
    for token in range(tokens):
        for value_head in range(value_heads):
            qk_head = value_head // heads_per_qk
            q_normalized = _normalize_vector(q_array[token, qk_head], eps) / np.sqrt(
                float(key_dim)
            )
            k_normalized = _normalize_vector(k_array[token, qk_head], eps)
            transition = alpha_array[token, value_head] * (
                identity - beta_array[token, value_head] * np.outer(k_normalized, k_normalized)
            )
            injection = beta_array[token, value_head] * np.outer(
                k_normalized, v_array[token, value_head]
            )
            state[value_head] = transition @ state[value_head] + injection
            outputs[token, value_head] = q_normalized @ state[value_head]
    return outputs, state


def state_kv_to_vk(state: object) -> Array:
    """Convert logical K-by-V state to a V-by-K physical view."""

    state_array = _as_finite_float64("state", state)
    if state_array.ndim < 2:
        raise ValueError("state must have at least two dimensions")
    return np.swapaxes(state_array, -2, -1).copy()


def state_vk_to_kv(state: object) -> Array:
    """Convert a V-by-K physical state back to logical K-by-V."""

    state_array = _as_finite_float64("state", state)
    if state_array.ndim < 2:
        raise ValueError("state must have at least two dimensions")
    return np.swapaxes(state_array, -2, -1).copy()

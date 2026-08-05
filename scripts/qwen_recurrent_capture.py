"""Reconstruct real Qwen3-Next layer-12 GDN recurrence inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import derive_alpha_beta
from scripts.hf_safetensors_range import (
    bf16_storage_to_float32,
    current_model_revision,
    extract_selected_tensors,
    sha256_file,
    validate_aliases,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "Qwen/Qwen3-Next-80B-A3B-Instruct"
SHARD = "model-00011-of-00041.safetensors"
DEFAULT_SOURCE = ROOT / "data" / "calibration" / "qwen3_next_80b_a3b_layer12.npz"
DEFAULT_WEIGHTS = (
    ROOT / "data" / "calibration" / "qwen3_next_80b_a3b_layer12_recurrence_weights.npz"
)
DEFAULT_OUTPUT = (
    ROOT / "data" / "calibration" / "qwen3_next_80b_a3b_layer12_recurrence.npz"
)

TENSOR_ALIASES = {
    "model.layers.12.input_layernorm.weight": "input_layernorm_weight",
    "model.layers.12.linear_attn.A_log": "a_log",
    "model.layers.12.linear_attn.conv1d.weight": "conv1d_weight",
    "model.layers.12.linear_attn.dt_bias": "dt_bias",
    "model.layers.12.linear_attn.in_proj_ba.weight": "in_proj_ba_weight",
    "model.layers.12.linear_attn.in_proj_qkvz.weight": "in_proj_qkvz_weight",
    "model.layers.12.linear_attn.norm.weight": "gated_norm_weight",
    "model.layers.12.linear_attn.out_proj.weight": "out_proj_weight",
}


def _stable_silu(x: np.ndarray) -> np.ndarray:
    values = np.asarray(x, dtype=np.float32)
    sigmoid = np.empty_like(values)
    positive = values >= 0
    sigmoid[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[~positive])
    sigmoid[~positive] = exp_values / (1.0 + exp_values)
    return (values * sigmoid).astype(np.float32)


def _rms_norm(x: np.ndarray, weight: np.ndarray, eps: float) -> np.ndarray:
    variance = np.mean(x * x, axis=-1, keepdims=True, dtype=np.float32)
    normalized = x * (np.float32(1.0) / np.sqrt(variance + np.float32(eps)))
    return (normalized * (np.float32(1.0) + weight)).astype(np.float32)


def _causal_depthwise_conv(x: np.ndarray, weight: np.ndarray) -> np.ndarray:
    if x.ndim != 3 or weight.ndim != 2 or x.shape[-1] != weight.shape[0]:
        raise ValueError("depthwise convolution shapes do not match")
    kernel = weight.shape[1]
    output = np.zeros_like(x, dtype=np.float32)
    tokens = x.shape[1]
    for tap in range(kernel):
        delay = kernel - 1 - tap
        if delay >= tokens:
            continue
        output[:, delay:, :] += x[:, : tokens - delay, :] * weight[None, None, :, tap]
    return _stable_silu(output)


def _characterize(array: np.ndarray) -> dict[str, float]:
    values = np.asarray(array, dtype=np.float32)
    absolute = np.abs(values).reshape(-1)
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "max_abs": float(np.max(absolute)),
        "p99_abs": float(np.quantile(absolute, 0.99)),
        "p999_abs": float(np.quantile(absolute, 0.999)),
    }


def ensure_weights(path: Path, *, revision: str | None = None) -> dict[str, object]:
    validate_aliases(TENSOR_ALIASES.values())
    if path.exists():
        with np.load(path, allow_pickle=False) as archive:
            metadata = json.loads(str(archive["metadata_json"]))
        metadata["output_sha256"] = sha256_file(path)
        return metadata
    resolved_revision = revision or current_model_revision(MODEL_ID)
    return extract_selected_tensors(
        model_id=MODEL_ID,
        revision=resolved_revision,
        shard=SHARD,
        tensor_aliases=TENSOR_ALIASES,
        output=path,
    )


def reconstruct(source: Path, weights: Path, output: Path) -> dict[str, object]:
    with np.load(source, allow_pickle=False) as capture:
        hidden = np.asarray(capture["layer_input"], dtype=np.float32)
        mask = np.asarray(capture["attention_mask"], dtype=np.int64)
        input_ids = np.asarray(capture["input_ids"], dtype=np.int64)
        source_metadata = json.loads(str(capture["metadata_json"]))

    with np.load(weights, allow_pickle=False) as archive:
        weight_metadata = json.loads(str(archive["metadata_json"]))
        tensors = {
            alias: bf16_storage_to_float32(np.asarray(archive[alias]))
            for alias in TENSOR_ALIASES.values()
        }

    if hidden.shape != (4, 18, 2048) or mask.shape != hidden.shape[:2]:
        raise ValueError(f"unexpected layer-12 capture shape: {hidden.shape}")
    normalized = _rms_norm(hidden, tensors["input_layernorm_weight"], 1e-6)
    normalized = np.where(mask[..., None] != 0, normalized, np.float32(0.0))

    qkvz = normalized @ tensors["in_proj_qkvz_weight"].T
    ba = normalized @ tensors["in_proj_ba_weight"].T

    batch, tokens, _ = qkvz.shape
    qkvz = qkvz.reshape(batch, tokens, 16, 768)
    q, k, v, z = np.split(qkvz, [128, 256, 512], axis=-1)
    v = v.reshape(batch, tokens, 32, 128)
    z = z.reshape(batch, tokens, 32, 128)

    ba = ba.reshape(batch, tokens, 16, 4)
    b, a = np.split(ba, [2], axis=-1)
    b = b.reshape(batch, tokens, 32)
    a = a.reshape(batch, tokens, 32)

    mixed = np.concatenate(
        [q.reshape(batch, tokens, 2048), k.reshape(batch, tokens, 2048), v.reshape(batch, tokens, 4096)],
        axis=-1,
    ).astype(np.float32)
    convolved = _causal_depthwise_conv(mixed, tensors["conv1d_weight"].reshape(8192, 4))
    q_conv, k_conv, v_conv = np.split(convolved, [2048, 4096], axis=-1)
    q_conv = q_conv.reshape(batch, tokens, 16, 128)
    k_conv = k_conv.reshape(batch, tokens, 16, 128)
    v_conv = v_conv.reshape(batch, tokens, 32, 128)

    broadcast_a_log = np.broadcast_to(tensors["a_log"], a.shape)
    broadcast_dt_bias = np.broadcast_to(tensors["dt_bias"], a.shape)
    alpha, beta = derive_alpha_beta(a, b, broadcast_a_log, broadcast_dt_bias)

    valid = mask.astype(bool)
    arrays = {
        "input_ids": input_ids,
        "attention_mask": mask,
        "q": q_conv.astype(np.float32),
        "k": k_conv.astype(np.float32),
        "v": v_conv.astype(np.float32),
        "alpha": alpha.astype(np.float32),
        "beta": beta.astype(np.float32),
        "a": a.astype(np.float32),
        "b": b.astype(np.float32),
        "z": z.astype(np.float32),
    }
    for name, array in arrays.items():
        if name not in {"input_ids", "attention_mask"} and not np.all(np.isfinite(array)):
            raise RuntimeError(f"reconstructed tensor {name} contains NaN or Inf")

    characterization = {
        name: _characterize(array[valid])
        for name, array in arrays.items()
        if name in {"q", "k", "v", "alpha", "beta"}
    }
    metadata = {
        "schema": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "real_qwen3_next_layer12_hidden_states_plus_checkpoint_projections",
        "model_id": MODEL_ID,
        "layer_index": 12,
        "recurrence_boundary": "post_causal_conv_pre_qk_normalization",
        "valid_tokens_per_prompt": mask.sum(axis=1).astype(int).tolist(),
        "total_valid_tokens": int(mask.sum()),
        "source_capture": source.as_posix(),
        "source_capture_sha256": sha256_file(source),
        "source_capture_metadata": source_metadata,
        "weights": weights.as_posix(),
        "weights_sha256": sha256_file(weights),
        "weights_revision": weight_metadata["revision"],
        "weights_shard": weight_metadata["shard"],
        "characterization": characterization,
        "limitations": [
            "The source capture records four short prompts, not a long contiguous decode.",
            "The source capture labeled the model revision as default; checkpoint weight history predates the capture.",
            "This artifact stops at the recurrence-core boundary and does not establish full-model perplexity.",
        ],
    }
    arrays["metadata_json"] = np.array(json.dumps(metadata, sort_keys=True))
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **arrays)
    digest = sha256_file(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.as_posix()}\n", encoding="utf-8"
    )
    metadata["output_sha256"] = digest
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--revision", help="Pinned Hugging Face model commit; defaults to current API SHA")
    args = parser.parse_args(argv)
    weights_metadata = ensure_weights(args.weights, revision=args.revision)
    capture_metadata = reconstruct(args.source, args.weights, args.output)
    print(json.dumps({"weights": weights_metadata, "capture": capture_metadata}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

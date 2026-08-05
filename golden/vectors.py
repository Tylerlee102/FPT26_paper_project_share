"""Deterministic vectors for the corrected GDN recurrence-core boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from .gdn_fp32 import gdn_decode_step


DEFAULT_SEED = int(os.environ.get("GDN_SEED", "0xFB72"), 0)
DEFAULT_NUM_VALUE_HEADS = 32
DEFAULT_NUM_QK_HEADS = 16
DEFAULT_HEAD_DIM = 128

# Retained for storage-only utilities that count value/state heads.
DEFAULT_NUM_HEADS = DEFAULT_NUM_VALUE_HEADS


@dataclass(frozen=True)
class DecodeVector:
    q: np.ndarray
    k: np.ndarray
    v: np.ndarray
    alpha: np.ndarray
    beta: np.ndarray
    state_in: np.ndarray
    output: np.ndarray
    state_out: np.ndarray
    seed: int
    index: int
    kind: str


def _rng(seed: int, index: int) -> np.random.Generator:
    return np.random.default_rng(seed + 0x9E3779B97F4A7C15 * (index + 1))


def generate_synthetic_vector(
    index: int,
    *,
    seed: int = DEFAULT_SEED,
    num_value_heads: int = DEFAULT_NUM_VALUE_HEADS,
    num_qk_heads: int = DEFAULT_NUM_QK_HEADS,
    head_dim: int = DEFAULT_HEAD_DIM,
) -> DecodeVector:
    """Generate one deterministic post-convolution recurrence input."""

    if num_qk_heads <= 0 or num_value_heads <= 0 or head_dim <= 0:
        raise ValueError("head counts and head_dim must be positive")
    if num_value_heads % num_qk_heads != 0:
        raise ValueError("num_value_heads must be divisible by num_qk_heads")

    generator = _rng(seed, index)
    q = generator.normal(0.0, 1.0, size=(num_qk_heads, head_dim)).astype(np.float32)
    k = generator.normal(0.0, 1.0, size=(num_qk_heads, head_dim)).astype(np.float32)
    v = generator.normal(0.0, 0.25, size=(num_value_heads, head_dim)).astype(np.float32)
    alpha = generator.uniform(0.85, 1.0, size=(num_value_heads,)).astype(np.float32)
    beta = generator.uniform(0.0, 1.0, size=(num_value_heads,)).astype(np.float32)
    state_in = generator.normal(
        0.0, 0.05, size=(num_value_heads, head_dim, head_dim)
    ).astype(np.float32)
    output, state_out = gdn_decode_step(q, k, v, alpha, beta, state_in)
    return DecodeVector(
        q,
        k,
        v,
        alpha,
        beta,
        state_in,
        output,
        state_out,
        seed,
        index,
        "synthetic_official_recurrence",
    )


def generate_vectors(
    count: int,
    *,
    kind: str = "synthetic_official_recurrence",
    seed: int = DEFAULT_SEED,
    num_value_heads: int = DEFAULT_NUM_VALUE_HEADS,
    num_qk_heads: int = DEFAULT_NUM_QK_HEADS,
    head_dim: int = DEFAULT_HEAD_DIM,
) -> Iterable[DecodeVector]:
    if count < 0:
        raise ValueError("count must be nonnegative")
    if kind != "synthetic_official_recurrence":
        raise NotImplementedError("Only corrected deterministic synthetic vectors are available.")
    for index in range(count):
        yield generate_synthetic_vector(
            index,
            seed=seed,
            num_value_heads=num_value_heads,
            num_qk_heads=num_qk_heads,
            head_dim=head_dim,
        )


def vector_digest(vector: DecodeVector) -> str:
    digest = hashlib.sha256()
    metadata = {
        "schema": 2,
        "kind": vector.kind,
        "seed": vector.seed,
        "index": vector.index,
        "num_qk_heads": int(vector.q.shape[0]),
        "num_value_heads": int(vector.v.shape[0]),
        "key_dim": int(vector.q.shape[1]),
        "value_dim": int(vector.v.shape[1]),
        "state_orientation": "KxV",
    }
    digest.update(json.dumps(metadata, sort_keys=True).encode("utf-8"))
    for array in (
        vector.q,
        vector.k,
        vector.v,
        vector.alpha,
        vector.beta,
        vector.state_in,
    ):
        digest.update(np.ascontiguousarray(array).view(np.uint8))
    return digest.hexdigest()


def save_vector(vector: DecodeVector, output_dir: str | Path) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    digest = vector_digest(vector)[:12]
    path = output / f"{vector.kind}_{vector.index:04d}_{digest}.npz"
    np.savez_compressed(
        path,
        schema=np.array(2, dtype=np.int32),
        q=vector.q,
        k=vector.k,
        v=vector.v,
        alpha=vector.alpha,
        beta=vector.beta,
        state_in=vector.state_in,
        output=vector.output,
        state_out=vector.state_out,
        state_orientation=np.array("KxV"),
        seed=np.array(vector.seed, dtype=np.uint64),
        index=np.array(vector.index, dtype=np.int32),
        kind=np.array(vector.kind),
    )
    return path


def load_vector(path: str | Path) -> DecodeVector:
    with np.load(path) as data:
        schema = int(data["schema"]) if "schema" in data.files else 1
        if schema != 2 or "alpha" not in data.files:
            raise ValueError("legacy vector schema is invalid for the corrected recurrence")
        if str(data["state_orientation"]) != "KxV":
            raise ValueError("vector state orientation must be KxV")
        return DecodeVector(
            q=data["q"],
            k=data["k"],
            v=data["v"],
            alpha=data["alpha"],
            beta=data["beta"],
            state_in=data["state_in"],
            output=data["output"],
            state_out=data["state_out"],
            seed=int(data["seed"]),
            index=int(data["index"]),
            kind=str(data["kind"]),
        )


def write_manifest(paths: list[Path], output_dir: str | Path) -> Path:
    manifest = {
        "schema": 2,
        "recurrence": "qwen3_next_v4.57.0_recurrent",
        "state_orientation": "KxV",
        "files": [
            {
                "path": str(path.as_posix()),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in paths
        ],
    }
    manifest_path = Path(output_dir) / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kind",
        default="synthetic_official_recurrence",
        choices=["synthetic_official_recurrence"],
    )
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--num-value-heads", type=int, default=DEFAULT_NUM_VALUE_HEADS)
    parser.add_argument("--num-qk-heads", type=int, default=DEFAULT_NUM_QK_HEADS)
    parser.add_argument("--head-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--output-dir", default="data/vectors_corrected")
    args = parser.parse_args(argv)

    paths = [
        save_vector(vector, args.output_dir)
        for vector in generate_vectors(
            args.count,
            kind=args.kind,
            seed=args.seed,
            num_value_heads=args.num_value_heads,
            num_qk_heads=args.num_qk_heads,
            head_dim=args.head_dim,
        )
    ]
    manifest = write_manifest(paths, args.output_dir)
    print(f"wrote {len(paths)} corrected vectors and {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

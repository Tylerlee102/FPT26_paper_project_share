"""Deterministic test vector generation and file I/O."""

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
DEFAULT_NUM_HEADS = 32
DEFAULT_HEAD_DIM = 128


@dataclass(frozen=True)
class DecodeVector:
    q: np.ndarray
    k: np.ndarray
    v: np.ndarray
    beta: np.ndarray
    gate: np.ndarray
    state_in: np.ndarray
    output: np.ndarray
    state_out: np.ndarray
    seed: int
    index: int
    kind: str


def _rng(seed: int, index: int) -> np.random.Generator:
    return np.random.default_rng(seed + 0x9E3779B97F4A7C15 * (index + 1))


def _unit_rows(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return (x / np.maximum(norms, eps)).astype(np.float32)


def generate_synthetic_vector(
    index: int,
    *,
    seed: int = DEFAULT_SEED,
    num_heads: int = DEFAULT_NUM_HEADS,
    head_dim: int = DEFAULT_HEAD_DIM,
) -> DecodeVector:
    """Generate one deterministic synthetic decode vector."""

    gen = _rng(seed, index)
    q = _unit_rows(gen.normal(0.0, 1.0, size=(num_heads, head_dim)).astype(np.float32))
    k = _unit_rows(gen.normal(0.0, 1.0, size=(num_heads, head_dim)).astype(np.float32))
    v = gen.normal(0.0, 0.25, size=(num_heads, head_dim)).astype(np.float32)
    beta = gen.uniform(0.0, 1.0, size=(num_heads,)).astype(np.float32)
    gate = gen.uniform(0.25, 1.0, size=(num_heads, head_dim)).astype(np.float32)
    state_in = gen.normal(0.0, 0.05, size=(num_heads, head_dim, head_dim)).astype(np.float32)
    output, state_out = gdn_decode_step(q, k, v, beta, gate, state_in)
    return DecodeVector(q, k, v, beta, gate, state_in, output, state_out, seed, index, "synthetic")


def generate_vectors(
    count: int,
    *,
    kind: str = "synthetic",
    seed: int = DEFAULT_SEED,
    num_heads: int = DEFAULT_NUM_HEADS,
    head_dim: int = DEFAULT_HEAD_DIM,
) -> Iterable[DecodeVector]:
    if kind != "synthetic":
        raise NotImplementedError("Only deterministic synthetic vectors are available in Phase 1.")
    for index in range(count):
        yield generate_synthetic_vector(
            index,
            seed=seed,
            num_heads=num_heads,
            head_dim=head_dim,
        )


def vector_digest(vector: DecodeVector) -> str:
    h = hashlib.sha256()
    metadata = {
        "kind": vector.kind,
        "seed": vector.seed,
        "index": vector.index,
        "num_heads": int(vector.q.shape[0]),
        "head_dim": int(vector.q.shape[1]),
    }
    h.update(json.dumps(metadata, sort_keys=True).encode("utf-8"))
    for arr in (vector.q, vector.k, vector.v, vector.beta, vector.gate, vector.state_in):
        h.update(np.ascontiguousarray(arr).view(np.uint8))
    return h.hexdigest()


def save_vector(vector: DecodeVector, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    digest = vector_digest(vector)[:12]
    path = out / f"{vector.kind}_{vector.index:04d}_{digest}.npz"
    np.savez_compressed(
        path,
        q=vector.q,
        k=vector.k,
        v=vector.v,
        beta=vector.beta,
        gate=vector.gate,
        state_in=vector.state_in,
        output=vector.output,
        state_out=vector.state_out,
        seed=np.array(vector.seed, dtype=np.uint64),
        index=np.array(vector.index, dtype=np.int32),
        kind=np.array(vector.kind),
    )
    return path


def load_vector(path: str | Path) -> DecodeVector:
    with np.load(path) as data:
        return DecodeVector(
            q=data["q"],
            k=data["k"],
            v=data["v"],
            beta=data["beta"],
            gate=data["gate"],
            state_in=data["state_in"],
            output=data["output"],
            state_out=data["state_out"],
            seed=int(data["seed"]),
            index=int(data["index"]),
            kind=str(data["kind"]),
        )


def write_manifest(paths: list[Path], output_dir: str | Path) -> Path:
    manifest = {
        "schema": 1,
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
    parser.add_argument("--kind", default="synthetic", choices=["synthetic"])
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--seed", type=lambda s: int(s, 0), default=DEFAULT_SEED)
    parser.add_argument("--num-heads", type=int, default=DEFAULT_NUM_HEADS)
    parser.add_argument("--head-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--output-dir", default="data/vectors")
    args = parser.parse_args(argv)

    paths = [
        save_vector(vector, args.output_dir)
        for vector in generate_vectors(
            args.count,
            kind=args.kind,
            seed=args.seed,
            num_heads=args.num_heads,
            head_dim=args.head_dim,
        )
    ]
    manifest = write_manifest(paths, args.output_dir)
    print(f"wrote {len(paths)} vectors and {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


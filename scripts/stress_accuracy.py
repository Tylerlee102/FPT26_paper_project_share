from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import gdn_decode_step as fp32_decode_step
from golden.gdn_mxfp4 import gdn_decode_step as mxfp_decode_step
from golden.mx_format import quantization_error
from golden.vectors import DEFAULT_HEAD_DIM, DEFAULT_NUM_HEADS, DEFAULT_SEED


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "reports" / "benchmark" / "stress_accuracy.csv"
DEFAULT_REPORT = ROOT / "reports" / "benchmark" / "stress_accuracy.md"


@dataclass(frozen=True)
class StateConfig:
    name: str
    precision: str
    block_size: int


CONFIGS = (
    StateConfig("state_mxfp4_b16", "mxfp4", 16),
    StateConfig("state_mxfp4_b32", "mxfp4", 32),
    StateConfig("state_mxfp8_b16", "mxfp8", 16),
    StateConfig("state_mxfp8_b32", "mxfp8", 32),
)

DISTRIBUTIONS = ("gaussian", "laplace", "outlier", "high_beta", "sparse_gate", "combined_stress")


def _rng(seed: int, index: int, distribution: str) -> np.random.Generator:
    dist_offset = sum((i + 1) * ord(ch) for i, ch in enumerate(distribution))
    return np.random.default_rng(seed + 0x9E3779B97F4A7C15 * (index + 1) + dist_offset)


def _unit_rows(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return (x / np.maximum(norms, eps)).astype(np.float32)


def _inject_outliers(gen: np.random.Generator, x: np.ndarray, *, fraction: float, multiplier: float) -> np.ndarray:
    out = np.array(x, dtype=np.float32, copy=True)
    flat = out.reshape(-1)
    count = max(1, int(flat.size * fraction))
    idx = gen.choice(flat.size, size=count, replace=False)
    signs = gen.choice(np.array([-1.0, 1.0], dtype=np.float32), size=count)
    flat[idx] = signs * multiplier * np.maximum(np.abs(flat[idx]), np.float32(1e-3))
    return out


def _arrays(
    *,
    seed: int,
    index: int,
    distribution: str,
    num_heads: int,
    head_dim: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    gen = _rng(seed, index, distribution)
    if distribution in {"laplace", "combined_stress"}:
        q_raw = gen.laplace(0.0, 1.0, size=(num_heads, head_dim)).astype(np.float32)
        k_raw = gen.laplace(0.0, 1.0, size=(num_heads, head_dim)).astype(np.float32)
        v = gen.laplace(0.0, 0.20, size=(num_heads, head_dim)).astype(np.float32)
        state = gen.laplace(0.0, 0.04, size=(num_heads, head_dim, head_dim)).astype(np.float32)
    else:
        q_raw = gen.normal(0.0, 1.0, size=(num_heads, head_dim)).astype(np.float32)
        k_raw = gen.normal(0.0, 1.0, size=(num_heads, head_dim)).astype(np.float32)
        v = gen.normal(0.0, 0.25, size=(num_heads, head_dim)).astype(np.float32)
        state = gen.normal(0.0, 0.05, size=(num_heads, head_dim, head_dim)).astype(np.float32)

    q = _unit_rows(q_raw)
    k = _unit_rows(k_raw)
    beta = gen.uniform(0.0, 1.0, size=(num_heads,)).astype(np.float32)
    gate = gen.uniform(0.25, 1.0, size=(num_heads, head_dim)).astype(np.float32)

    if distribution == "high_beta":
        beta = gen.uniform(0.85, 1.0, size=(num_heads,)).astype(np.float32)
    if distribution == "sparse_gate":
        keep = gen.random(size=gate.shape) > 0.80
        gate = np.where(keep, gate, np.float32(0.0)).astype(np.float32)
    if distribution in {"outlier", "combined_stress"}:
        q = _inject_outliers(gen, q, fraction=0.005, multiplier=8.0)
        k = _inject_outliers(gen, k, fraction=0.005, multiplier=8.0)
        v = _inject_outliers(gen, v, fraction=0.010, multiplier=16.0)
        state = _inject_outliers(gen, state, fraction=0.002, multiplier=16.0)
    if distribution == "combined_stress":
        beta = gen.uniform(0.85, 1.0, size=(num_heads,)).astype(np.float32)
        keep = gen.random(size=gate.shape) > 0.75
        gate = np.where(keep, gate, np.float32(0.0)).astype(np.float32)

    return q, k, v, beta, gate, state


def run_sweep(
    *,
    seeds: list[int],
    count: int,
    distributions: tuple[str, ...],
    num_heads: int,
    head_dim: int,
    activation_block_size: int,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for distribution in distributions:
        for seed in seeds:
            for config in CONFIGS:
                output_metrics: list[dict[str, float]] = []
                state_metrics: list[dict[str, float]] = []
                for index in range(count):
                    q, k, v, beta, gate, state = _arrays(
                        seed=seed,
                        index=index,
                        distribution=distribution,
                        num_heads=num_heads,
                        head_dim=head_dim,
                    )
                    ref_output, ref_state = fp32_decode_step(q, k, v, beta, gate, state)
                    got_output, got_state = mxfp_decode_step(
                        q,
                        k,
                        v,
                        beta,
                        gate,
                        state,
                        block_size=activation_block_size,
                        state_block_size=config.block_size,
                        state_precision=config.precision,
                    )
                    output_metrics.append(quantization_error(ref_output, got_output))
                    state_metrics.append(quantization_error(ref_state, got_state))

                rows.append(
                    {
                        "distribution": distribution,
                        "seed": seed,
                        "state_config": config.name,
                        "vectors": count,
                        "output_rel_l2_mean": float(np.mean([m["rel_l2"] for m in output_metrics])),
                        "output_rel_l2_worst": float(np.max([m["rel_l2"] for m in output_metrics])),
                        "output_cosine_mean": float(np.mean([m["cosine"] for m in output_metrics])),
                        "output_cosine_worst": float(np.min([m["cosine"] for m in output_metrics])),
                        "state_rel_l2_mean": float(np.mean([m["rel_l2"] for m in state_metrics])),
                        "state_rel_l2_worst": float(np.max([m["rel_l2"] for m in state_metrics])),
                    }
                )
    return rows


def _write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "distribution",
        "seed",
        "state_config",
        "vectors",
        "output_rel_l2_mean",
        "output_rel_l2_worst",
        "output_cosine_mean",
        "output_cosine_worst",
        "state_rel_l2_mean",
        "state_rel_l2_worst",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _aggregate(rows: list[dict[str, float | int | str]]) -> list[dict[str, float | str]]:
    grouped: dict[tuple[str, str], list[dict[str, float | int | str]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["distribution"]), str(row["state_config"]))].append(row)

    out: list[dict[str, float | str]] = []
    for (distribution, state_config), items in sorted(grouped.items()):
        out.append(
            {
                "distribution": distribution,
                "state_config": state_config,
                "mean_output_cosine": float(np.mean([float(item["output_cosine_mean"]) for item in items])),
                "worst_output_cosine": float(np.min([float(item["output_cosine_worst"]) for item in items])),
                "mean_output_rel_l2": float(np.mean([float(item["output_rel_l2_mean"]) for item in items])),
                "worst_output_rel_l2": float(np.max([float(item["output_rel_l2_worst"]) for item in items])),
                "mean_state_rel_l2": float(np.mean([float(item["state_rel_l2_mean"]) for item in items])),
                "worst_state_rel_l2": float(np.max([float(item["state_rel_l2_worst"]) for item in items])),
            }
        )
    return out


def _write_report(
    path: Path,
    *,
    csv_path: Path,
    rows: list[dict[str, float | int | str]],
    seeds: list[int],
    count: int,
    num_heads: int,
    head_dim: int,
    activation_block_size: int,
) -> None:
    agg = _aggregate(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Synthetic Stress Accuracy Sweep",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Seeds: {', '.join(hex(seed) for seed in seeds)}",
        f"Vectors per seed/distribution/config: {count}",
        f"Shape: num_heads={num_heads}, head_dim={head_dim}",
        f"Activation block size: {activation_block_size}",
        f"CSV: `{csv_path.relative_to(ROOT).as_posix()}`",
        "",
        "This is a one-step synthetic stress sweep. It broadens the numerical-fidelity evidence when real Qwen3-Next activation capture is unavailable; it is not a perplexity result.",
        "",
        "| Distribution | State config | Mean output cosine | Worst output cosine | Mean output rel L2 | Worst output rel L2 | Mean state rel L2 | Worst state rel L2 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in agg:
        lines.append(
            f"| {row['distribution']} | {row['state_config']} | "
            f"{float(row['mean_output_cosine']):.6f} | {float(row['worst_output_cosine']):.6f} | "
            f"{float(row['mean_output_rel_l2']):.6f} | {float(row['worst_output_rel_l2']):.6f} | "
            f"{float(row['mean_state_rel_l2']):.6f} | {float(row['worst_state_rel_l2']):.6f} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _parse_seeds(values: list[str] | None) -> list[int]:
    if not values:
        return [DEFAULT_SEED + offset for offset in range(5)]
    return [int(value, 0) for value in values]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one-step synthetic stress and multi-seed accuracy sweeps.")
    parser.add_argument("--seeds", nargs="*")
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--distributions", nargs="*", choices=DISTRIBUTIONS, default=list(DISTRIBUTIONS))
    parser.add_argument("--num-heads", type=int, default=DEFAULT_NUM_HEADS)
    parser.add_argument("--head-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--activation-block-size", type=int, choices=[16, 32], default=32)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    csv_path = args.csv if args.csv.is_absolute() else ROOT / args.csv
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    seeds = _parse_seeds(args.seeds)
    rows = run_sweep(
        seeds=seeds,
        count=args.count,
        distributions=tuple(args.distributions),
        num_heads=args.num_heads,
        head_dim=args.head_dim,
        activation_block_size=args.activation_block_size,
    )
    _write_csv(csv_path, rows)
    _write_report(
        report_path,
        csv_path=csv_path,
        rows=rows,
        seeds=seeds,
        count=args.count,
        num_heads=args.num_heads,
        head_dim=args.head_dim,
        activation_block_size=args.activation_block_size,
    )
    print(report_path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

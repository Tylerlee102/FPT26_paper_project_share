from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import gdn_decode_step as fp32_decode_step
from golden.gdn_mxfp4 import gdn_decode_step as mxfp4_decode_step
from golden.mx_format import quantization_error
from golden.vectors import DEFAULT_HEAD_DIM, DEFAULT_NUM_HEADS, DEFAULT_SEED


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "reports" / "benchmark" / "state_drift.csv"
DEFAULT_REPORT = ROOT / "reports" / "benchmark" / "state_drift.md"


@dataclass(frozen=True)
class DriftSummary:
    tokens: int
    final_output_cosine: float
    final_output_rel_l2: float
    final_state_rel_l2: float
    worst_output_cosine: float
    worst_state_rel_l2: float
    mean_output_cosine: float
    mean_state_rel_l2: float


def _mean(rows: list[dict[str, float]], key: str) -> float:
    return float(np.mean([row[key] for row in rows])) if rows else 0.0


def _min(rows: list[dict[str, float]], key: str) -> float:
    return float(np.min([row[key] for row in rows])) if rows else 0.0


def _max(rows: list[dict[str, float]], key: str) -> float:
    return float(np.max([row[key] for row in rows])) if rows else 0.0


def _summarize(rows: list[dict[str, float]], prefix: str) -> DriftSummary:
    final = rows[-1] if rows else {}
    return DriftSummary(
        tokens=len(rows),
        final_output_cosine=float(final.get(f"{prefix}_output_cosine", 0.0)),
        final_output_rel_l2=float(final.get(f"{prefix}_output_rel_l2", 0.0)),
        final_state_rel_l2=float(final.get(f"{prefix}_state_rel_l2", 0.0)),
        worst_output_cosine=_min(rows, f"{prefix}_output_cosine"),
        worst_state_rel_l2=_max(rows, f"{prefix}_state_rel_l2"),
        mean_output_cosine=_mean(rows, f"{prefix}_output_cosine"),
        mean_state_rel_l2=_mean(rows, f"{prefix}_state_rel_l2"),
    )


def _rng(seed: int, index: int) -> np.random.Generator:
    return np.random.default_rng(seed + 0x9E3779B97F4A7C15 * (index + 1))


def _unit_rows(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return (x / np.maximum(norms, eps)).astype(np.float32)


def _token_arrays(
    index: int,
    *,
    seed: int,
    num_heads: int,
    head_dim: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    gen = _rng(seed, index)
    q = _unit_rows(gen.normal(0.0, 1.0, size=(num_heads, head_dim)).astype(np.float32))
    k = _unit_rows(gen.normal(0.0, 1.0, size=(num_heads, head_dim)).astype(np.float32))
    v = gen.normal(0.0, 0.25, size=(num_heads, head_dim)).astype(np.float32)
    beta = gen.uniform(0.0, 1.0, size=(num_heads,)).astype(np.float32)
    gate = gen.uniform(0.25, 1.0, size=(num_heads, head_dim)).astype(np.float32)
    return q, k, v, beta, gate


def _initial_state(*, seed: int, num_heads: int, head_dim: int) -> np.ndarray:
    gen = _rng(seed, 0)
    # Advance past q/k/v/beta/gate draws so the initial state matches the
    # deterministic synthetic-vector distribution without doing unused work.
    gen.normal(0.0, 1.0, size=(num_heads, head_dim))
    gen.normal(0.0, 1.0, size=(num_heads, head_dim))
    gen.normal(0.0, 0.25, size=(num_heads, head_dim))
    gen.uniform(0.0, 1.0, size=(num_heads,))
    gen.uniform(0.25, 1.0, size=(num_heads, head_dim))
    return gen.normal(0.0, 0.05, size=(num_heads, head_dim, head_dim)).astype(np.float32)


def run_state_drift(
    *,
    tokens: int,
    seed: int,
    num_heads: int,
    head_dim: int,
    block_size: int,
    state_block_size: int,
) -> list[dict[str, float]]:
    initial = _initial_state(seed=seed, num_heads=num_heads, head_dim=head_dim)
    fp32_state = np.array(initial, dtype=np.float32, copy=True)
    mxfp4_state = np.array(initial, dtype=np.float32, copy=True)
    mxfp8_state = np.array(initial, dtype=np.float32, copy=True)

    rows: list[dict[str, float]] = []
    for index in range(tokens):
        q, k, v, beta, gate = _token_arrays(index, seed=seed, num_heads=num_heads, head_dim=head_dim)
        ref_output, fp32_state = fp32_decode_step(
            q,
            k,
            v,
            beta,
            gate,
            fp32_state,
        )
        mxfp4_output, mxfp4_state = mxfp4_decode_step(
            q,
            k,
            v,
            beta,
            gate,
            mxfp4_state,
            block_size=block_size,
            state_block_size=state_block_size,
            state_precision="mxfp4",
        )
        mxfp8_output, mxfp8_state = mxfp4_decode_step(
            q,
            k,
            v,
            beta,
            gate,
            mxfp8_state,
            block_size=block_size,
            state_block_size=state_block_size,
            state_precision="mxfp8",
        )

        out4 = quantization_error(ref_output, mxfp4_output)
        state4 = quantization_error(fp32_state, mxfp4_state)
        out8 = quantization_error(ref_output, mxfp8_output)
        state8 = quantization_error(fp32_state, mxfp8_state)
        rows.append(
            {
                "token": float(index + 1),
                "mxfp4_output_rel_l2": out4["rel_l2"],
                "mxfp4_output_max_abs": out4["max_abs"],
                "mxfp4_output_cosine": out4["cosine"],
                "mxfp4_state_rel_l2": state4["rel_l2"],
                "mxfp4_state_max_abs": state4["max_abs"],
                "mxfp4_state_cosine": state4["cosine"],
                "mxfp8_output_rel_l2": out8["rel_l2"],
                "mxfp8_output_max_abs": out8["max_abs"],
                "mxfp8_output_cosine": out8["cosine"],
                "mxfp8_state_rel_l2": state8["rel_l2"],
                "mxfp8_state_max_abs": state8["max_abs"],
                "mxfp8_state_cosine": state8["cosine"],
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "token",
        "mxfp4_output_rel_l2",
        "mxfp4_output_max_abs",
        "mxfp4_output_cosine",
        "mxfp4_state_rel_l2",
        "mxfp4_state_max_abs",
        "mxfp4_state_cosine",
        "mxfp8_output_rel_l2",
        "mxfp8_output_max_abs",
        "mxfp8_output_cosine",
        "mxfp8_state_rel_l2",
        "mxfp8_state_max_abs",
        "mxfp8_state_cosine",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_report(
    path: Path,
    *,
    csv_path: Path,
    rows: list[dict[str, float]],
    seed: int,
    num_heads: int,
    head_dim: int,
    block_size: int,
    state_block_size: int,
) -> None:
    mxfp4 = _summarize(rows, "mxfp4")
    mxfp8 = _summarize(rows, "mxfp8")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Long-Token Synthetic State Drift",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Source: deterministic synthetic token stream, seed `{hex(seed)}`",
        f"Shape: num_heads={num_heads}, head_dim={head_dim}",
        f"Tokens: {len(rows)}",
        f"MXFP4 activation block size: {block_size}",
        f"State block size: {state_block_size}",
        f"CSV: `{csv_path.relative_to(ROOT).as_posix()}`",
        "",
        "This run reuses one evolving FP32 state, one evolving MXFP4-state path, and one evolving MXFP8-state path over the same synthetic token stream. It is a stress test for recurrent-state error accumulation, not a Qwen3-Next perplexity result.",
        "",
        "| State path | Final output cosine | Final output rel L2 | Final state rel L2 | Worst output cosine | Worst state rel L2 | Mean output cosine | Mean state rel L2 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| MXFP4 state | {mxfp4.final_output_cosine:.6f} | {mxfp4.final_output_rel_l2:.6f} | "
            f"{mxfp4.final_state_rel_l2:.6f} | {mxfp4.worst_output_cosine:.6f} | "
            f"{mxfp4.worst_state_rel_l2:.6f} | {mxfp4.mean_output_cosine:.6f} | {mxfp4.mean_state_rel_l2:.6f} |"
        ),
        (
            f"| MXFP8 state | {mxfp8.final_output_cosine:.6f} | {mxfp8.final_output_rel_l2:.6f} | "
            f"{mxfp8.final_state_rel_l2:.6f} | {mxfp8.worst_output_cosine:.6f} | "
            f"{mxfp8.worst_state_rel_l2:.6f} | {mxfp8.mean_output_cosine:.6f} | {mxfp8.mean_state_rel_l2:.6f} |"
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a long synthetic recurrent-state drift test.")
    parser.add_argument("--tokens", type=int, default=1024)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--num-heads", type=int, default=DEFAULT_NUM_HEADS)
    parser.add_argument("--head-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--block-size", type=int, choices=[16, 32], default=32)
    parser.add_argument("--state-block-size", type=int, choices=[16, 32], default=16)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    csv_path = args.csv if args.csv.is_absolute() else ROOT / args.csv
    report_path = args.report if args.report.is_absolute() else ROOT / args.report

    rows = run_state_drift(
        tokens=args.tokens,
        seed=args.seed,
        num_heads=args.num_heads,
        head_dim=args.head_dim,
        block_size=args.block_size,
        state_block_size=args.state_block_size,
    )
    _write_csv(csv_path, rows)
    _write_report(
        report_path,
        csv_path=csv_path,
        rows=rows,
        seed=args.seed,
        num_heads=args.num_heads,
        head_dim=args.head_dim,
        block_size=args.block_size,
        state_block_size=args.state_block_size,
    )
    print(report_path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

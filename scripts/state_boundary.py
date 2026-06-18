from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import gdn_decode_step as fp32_decode_step
from golden.gdn_mxfp4 import gdn_decode_step as mxfp_decode_step
from golden.mx_format import quantization_error
from golden.vectors import DEFAULT_HEAD_DIM, DEFAULT_NUM_HEADS, DEFAULT_SEED
from scripts.stress_accuracy import CONFIGS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "reports" / "benchmark" / "state_boundary.csv"
DEFAULT_REPORT = ROOT / "reports" / "benchmark" / "state_boundary.md"


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
    gen.normal(0.0, 1.0, size=(num_heads, head_dim))
    gen.normal(0.0, 1.0, size=(num_heads, head_dim))
    gen.normal(0.0, 0.25, size=(num_heads, head_dim))
    gen.uniform(0.0, 1.0, size=(num_heads,))
    gen.uniform(0.25, 1.0, size=(num_heads, head_dim))
    return gen.normal(0.0, 0.05, size=(num_heads, head_dim, head_dim)).astype(np.float32)


def run_boundary(
    *,
    tokens: int,
    seed: int,
    checkpoints: list[int],
    num_heads: int,
    head_dim: int,
    activation_block_size: int,
) -> list[dict[str, float | int | str]]:
    checkpoint_set = set(checkpoints)
    fp32_state = _initial_state(seed=seed, num_heads=num_heads, head_dim=head_dim)
    states = {config.name: np.array(fp32_state, dtype=np.float32, copy=True) for config in CONFIGS}
    rows: list[dict[str, float | int | str]] = []
    for index in range(tokens):
        q, k, v, beta, gate = _token_arrays(index, seed=seed, num_heads=num_heads, head_dim=head_dim)
        ref_output, fp32_state = fp32_decode_step(q, k, v, beta, gate, fp32_state)
        for config in CONFIGS:
            got_output, got_state = mxfp_decode_step(
                q,
                k,
                v,
                beta,
                gate,
                states[config.name],
                block_size=activation_block_size,
                state_block_size=config.block_size,
                state_precision=config.precision,
            )
            states[config.name] = got_state
            if index + 1 in checkpoint_set:
                out = quantization_error(ref_output, got_output)
                state = quantization_error(fp32_state, got_state)
                rows.append(
                    {
                        "checkpoint_token": index + 1,
                        "state_config": config.name,
                        "output_rel_l2": out["rel_l2"],
                        "output_cosine": out["cosine"],
                        "state_rel_l2": state["rel_l2"],
                        "state_cosine": state["cosine"],
                    }
                )
    return rows


def _write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["checkpoint_token", "state_config", "output_rel_l2", "output_cosine", "state_rel_l2", "state_cosine"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: Path,
    *,
    csv_path: Path,
    rows: list[dict[str, float | int | str]],
    seed: int,
    tokens: int,
    checkpoints: list[int],
    num_heads: int,
    head_dim: int,
    activation_block_size: int,
) -> None:
    grouped: dict[int, list[dict[str, float | int | str]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["checkpoint_token"])].append(row)

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Recurrent-State Precision Boundary",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Source: deterministic synthetic token stream, seed `{hex(seed)}`",
        f"Shape: num_heads={num_heads}, head_dim={head_dim}",
        f"Tokens simulated: {tokens}",
        f"Checkpoints: {', '.join(str(item) for item in checkpoints)}",
        f"Activation block size: {activation_block_size}",
        f"CSV: `{csv_path.relative_to(ROOT).as_posix()}`",
        "",
        "This recurrent test compares MXFP4 and MXFP8 state storage at block sizes 16 and 32. It is synthetic fidelity evidence, not a Qwen3-Next perplexity result.",
        "",
    ]
    for checkpoint in checkpoints:
        lines.extend(
            [
                f"## Token {checkpoint}",
                "",
                "| State config | Output cosine | Output rel L2 | State cosine | State rel L2 |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in sorted(grouped[checkpoint], key=lambda item: str(item["state_config"])):
            lines.append(
                f"| {row['state_config']} | {float(row['output_cosine']):.6f} | "
                f"{float(row['output_rel_l2']):.6f} | {float(row['state_cosine']):.6f} | "
                f"{float(row['state_rel_l2']):.6f} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _parse_checkpoints(values: list[str] | None, tokens: int) -> list[int]:
    if values:
        parsed = sorted({int(value, 0) for value in values})
    else:
        parsed = [64, 256, 1024]
    return [value for value in parsed if 1 <= value <= tokens]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare recurrent-state precision choices over a token stream.")
    parser.add_argument("--tokens", type=int, default=256)
    parser.add_argument("--checkpoints", nargs="*")
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--num-heads", type=int, default=DEFAULT_NUM_HEADS)
    parser.add_argument("--head-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--activation-block-size", type=int, choices=[16, 32], default=32)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    csv_path = args.csv if args.csv.is_absolute() else ROOT / args.csv
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    checkpoints = _parse_checkpoints(args.checkpoints, args.tokens)
    rows = run_boundary(
        tokens=args.tokens,
        seed=args.seed,
        checkpoints=checkpoints,
        num_heads=args.num_heads,
        head_dim=args.head_dim,
        activation_block_size=args.activation_block_size,
    )
    _write_csv(csv_path, rows)
    _write_report(
        report_path,
        csv_path=csv_path,
        rows=rows,
        seed=args.seed,
        tokens=args.tokens,
        checkpoints=checkpoints,
        num_heads=args.num_heads,
        head_dim=args.head_dim,
        activation_block_size=args.activation_block_size,
    )
    print(report_path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

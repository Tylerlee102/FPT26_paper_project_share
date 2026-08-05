from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from pathlib import Path

from golden.vectors import DEFAULT_HEAD_DIM, DEFAULT_NUM_HEADS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "reports" / "benchmark" / "offchip_state_traffic.csv"
DEFAULT_REPORT = ROOT / "reports" / "benchmark" / "offchip_state_traffic.md"


@dataclass(frozen=True)
class TrafficRow:
    format: str
    block_size: str
    state_bytes: int
    one_read_write_bytes: int
    naive_three_pass_bytes: int
    persistent_steady_state_bytes: int
    traffic_reduction_vs_three_pass_pct: float


def _bytes_for_bits(bits: int) -> int:
    return ceil(bits / 8)


def _state_bytes(num_heads: int, head_dim: int, *, element_bits: int, block_size: int | None) -> int:
    elements = num_heads * head_dim * head_dim
    scale_bits = 0
    if block_size is not None:
        scale_blocks = num_heads * head_dim * ceil(head_dim / block_size)
        scale_bits = scale_blocks * 8
    return _bytes_for_bits(elements * element_bits + scale_bits)


def _rows(num_heads: int, head_dim: int) -> list[TrafficRow]:
    specs = [
        ("FP32", "none", _state_bytes(num_heads, head_dim, element_bits=32, block_size=None)),
        ("BF16/FP16", "none", _state_bytes(num_heads, head_dim, element_bits=16, block_size=None)),
        ("INT8", "none", _state_bytes(num_heads, head_dim, element_bits=8, block_size=None)),
        ("MXFP4", "16", _state_bytes(num_heads, head_dim, element_bits=4, block_size=16)),
        ("MXFP4", "32", _state_bytes(num_heads, head_dim, element_bits=4, block_size=32)),
    ]
    rows: list[TrafficRow] = []
    for name, block_size, state_bytes in specs:
        three_pass = state_bytes * 3
        rows.append(
            TrafficRow(
                format=name,
                block_size=block_size,
                state_bytes=state_bytes,
                one_read_write_bytes=state_bytes * 2,
                naive_three_pass_bytes=three_pass,
                persistent_steady_state_bytes=0,
                traffic_reduction_vs_three_pass_pct=100.0,
            )
        )
    return rows


def _write_csv(path: Path, rows: list[TrafficRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "format",
        "block_size",
        "state_bytes",
        "one_read_write_bytes",
        "naive_three_pass_bytes",
        "persistent_steady_state_bytes",
        "traffic_reduction_vs_three_pass_pct",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _write_report(path: Path, *, csv_path: Path, rows: list[TrafficRow], num_heads: int, head_dim: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Off-Chip Recurrent-State Traffic Estimate",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Shape: num_heads={num_heads}, head_dim={head_dim}",
        f"CSV: `{csv_path.relative_to(ROOT).as_posix()}`",
        "",
        "This estimate counts recurrent-state traffic only. The naive three-pass case reads old state for prediction, writes updated state, then reads updated state for output. The persistent-state datapath keeps state resident on chip after initialization, so steady-state off-chip recurrent-state traffic is zero.",
        "",
        "| Format | Block size | State bytes | Read+write bytes/token | Naive three-pass bytes/token | Persistent steady-state bytes/token |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.format} | {row.block_size} | {row.state_bytes} | {row.one_read_write_bytes} | "
            f"{row.naive_three_pass_bytes} | {row.persistent_steady_state_bytes} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate off-chip recurrent-state traffic avoided by persistence.")
    parser.add_argument("--num-heads", type=int, default=DEFAULT_NUM_HEADS)
    parser.add_argument("--head-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    csv_path = args.csv if args.csv.is_absolute() else ROOT / args.csv
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    rows = _rows(args.num_heads, args.head_dim)
    _write_csv(csv_path, rows)
    _write_report(report_path, csv_path=csv_path, rows=rows, num_heads=args.num_heads, head_dim=args.head_dim)
    print(report_path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

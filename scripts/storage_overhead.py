from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from pathlib import Path

from golden.vectors import DEFAULT_HEAD_DIM, DEFAULT_NUM_HEADS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "reports" / "benchmark" / "storage_overhead.csv"
DEFAULT_REPORT = ROOT / "reports" / "benchmark" / "storage_overhead.md"


@dataclass(frozen=True)
class StorageRow:
    format: str
    block_size: str
    element_bits: float
    scale_bits_per_block: int
    total_bytes: int
    relative_to_mxfp4_b32: float
    reduction_vs_fp32_pct: float
    reduction_vs_bf16_pct: float


def _bytes_for_bits(bits: int) -> int:
    return ceil(bits / 8)


def _rows(num_heads: int, head_dim: int) -> list[StorageRow]:
    elements = num_heads * head_dim * head_dim
    scale_blocks_b16 = num_heads * head_dim * ceil(head_dim / 16)
    scale_blocks_b32 = num_heads * head_dim * ceil(head_dim / 32)
    fp32_bytes = _bytes_for_bits(elements * 32)
    bf16_bytes = _bytes_for_bits(elements * 16)
    mxfp4_b32_bytes = _bytes_for_bits(elements * 4 + scale_blocks_b32 * 8)

    specs = [
        ("FP32", "none", 32.0, 0, fp32_bytes),
        ("BF16/FP16", "none", 16.0, 0, bf16_bytes),
        ("INT8", "none", 8.0, 0, _bytes_for_bits(elements * 8)),
        ("Flat INT4", "none", 4.0, 0, _bytes_for_bits(elements * 4)),
        ("MXFP4", "16", 4.0, 8, _bytes_for_bits(elements * 4 + scale_blocks_b16 * 8)),
        ("MXFP4", "32", 4.0, 8, mxfp4_b32_bytes),
    ]
    return [
        StorageRow(
            format=name,
            block_size=block_size,
            element_bits=element_bits,
            scale_bits_per_block=scale_bits,
            total_bytes=total_bytes,
            relative_to_mxfp4_b32=total_bytes / mxfp4_b32_bytes,
            reduction_vs_fp32_pct=(1.0 - total_bytes / fp32_bytes) * 100.0,
            reduction_vs_bf16_pct=(1.0 - total_bytes / bf16_bytes) * 100.0,
        )
        for name, block_size, element_bits, scale_bits, total_bytes in specs
    ]


def _write_csv(path: Path, rows: list[StorageRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "format",
        "block_size",
        "element_bits",
        "scale_bits_per_block",
        "total_bytes",
        "relative_to_mxfp4_b32",
        "reduction_vs_fp32_pct",
        "reduction_vs_bf16_pct",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _write_report(path: Path, *, csv_path: Path, rows: list[StorageRow], num_heads: int, head_dim: int) -> None:
    elements = num_heads * head_dim * head_dim
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Recurrent-State Storage Overhead",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Shape: num_heads={num_heads}, head_dim={head_dim}, elements={elements}",
        f"CSV: `{csv_path.relative_to(ROOT).as_posix()}`",
        "",
        "MXFP4 includes E8M0 scale metadata in this accounting. Scales are counted per block along the innermost state dimension.",
        "",
        "| Format | Block size | Element bits | Scale bits/block | Total bytes | Relative to MXFP4 B=32 | Reduction vs FP32 | Reduction vs BF16 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.format} | {row.block_size} | {row.element_bits:.1f} | {row.scale_bits_per_block} | "
            f"{row.total_bytes} | {row.relative_to_mxfp4_b32:.3f}x | "
            f"{row.reduction_vs_fp32_pct:.3f}% | {row.reduction_vs_bf16_pct:.3f}% |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute recurrent-state storage including MXFP4 scale overhead.")
    parser.add_argument("--num-heads", type=int, default=DEFAULT_NUM_HEADS)
    parser.add_argument("--head-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    rows = _rows(args.num_heads, args.head_dim)
    _write_csv(args.csv, rows)
    _write_report(args.report, csv_path=args.csv, rows=rows, num_heads=args.num_heads, head_dim=args.head_dim)
    print(args.report.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

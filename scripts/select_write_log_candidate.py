"""Generate the development-only write-log candidate freeze record."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "benchmark" / "corrected"
DENSE_CSV = REPORT_DIR / "write_log_development_checkpoints.csv"
SELECTED_CSV = REPORT_DIR / "write_log_selected_development_checkpoints.csv"
BASELINE_CSV = REPORT_DIR / "long_trace_checkpoints.csv"
OUTPUT_CSV = REPORT_DIR / "write_log_selection.csv"
OUTPUT_JSON = REPORT_DIR / "write_log_selection.json"
OUTPUT_MD = ROOT / "docs" / "write_log_selection.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _final_candidates(path: Path) -> list[dict[str, str]]:
    rows = [row for row in _read(path) if row["variant"] != "fp32"]
    final_token = max(int(row["token_index"]) for row in rows)
    return [row for row in rows if int(row["token_index"]) == final_token]


def _baseline_bytes() -> dict[str, int]:
    value_heads = 32
    key_dim = 128
    value_dim = 128
    blocks = value_dim // 32
    return {
        "bf16_state": value_heads * key_dim * value_dim * 2,
        "mxfp8_e4m3_b32_state": value_heads * key_dim * blocks * 33,
        "mxfp4_b32_state": value_heads * key_dim * blocks * 17,
    }


def main() -> int:
    sources = [DENSE_CSV, SELECTED_CSV, BASELINE_CSV]
    for path in sources:
        if not path.is_file():
            raise FileNotFoundError(path)
    storage = _baseline_bytes()
    rows: list[dict[str, object]] = []
    for source in (DENSE_CSV, SELECTED_CSV):
        all_rows = _read(source)
        required_tokens = sorted({int(row["token_index"]) for row in all_rows})
        for final in _final_candidates(source):
            variant = final["variant"]
            variant_rows = [row for row in all_rows if row["variant"] == variant]
            gate_pass = (
                all(float(row["output_cosine_fp32"]) >= 0.99 for row in variant_rows)
                and float(final["state_rel_l2"]) <= 0.10
                and all(int(row["dropped_entries"]) == 0 for row in variant_rows)
            )
            logical_bytes = int(final["logical_state_bytes"])
            rows.append(
                {
                    "variant": variant,
                    "source": source.relative_to(ROOT).as_posix(),
                    "tokens": int(final["token_index"]),
                    "required_checkpoint_count": len(required_tokens),
                    "output_cosine_fp32": float(final["output_cosine_fp32"]),
                    "state_rel_l2": float(final["state_rel_l2"]),
                    "state_max_abs": float(final["state_max_abs"]),
                    "dropped_entries": int(final["dropped_entries"]),
                    "logical_state_bytes": logical_bytes,
                    "reduction_vs_bf16_percent": 100.0
                    * (1.0 - logical_bytes / storage["bf16_state"]),
                    "reduction_vs_mxfp8_percent": 100.0
                    * (1.0 - logical_bytes / storage["mxfp8_e4m3_b32_state"]),
                    "synthetic_gate": "PASS" if gate_pass else "FAIL",
                    "physical_evidence": "NOT_RUN",
                }
            )

    eligible = [
        row
        for row in rows
        if row["synthetic_gate"] == "PASS"
        and int(row["tokens"]) == 8192
        and int(row["logical_state_bytes"]) < storage["mxfp8_e4m3_b32_state"]
    ]
    if len(eligible) != 1:
        raise RuntimeError(f"expected one held-out-eligible candidate, found {len(eligible)}")
    selected = eligible[0]

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "schema": 1,
        "status": "PASS",
        "scope": "development-only configuration freeze for held-out synthetic runs",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "selected_variant": selected["variant"],
        "selected_configuration": {
            "activation_stack_depth": 2,
            "base_stack_depth": 2,
            "base_residual_blocks_per_row": 3,
            "base_blocks_per_row": 4,
            "base_residual_block_fraction": 0.75,
            "log_precision": "mxfp8_e4m3",
            "log_capacity": 7,
            "fold_policy": "fixed_atomic_all_head",
            "activation_block_size": 32,
            "state_block_size": 32,
            "num_value_heads": 32,
            "num_qk_heads": 16,
            "key_dim": 128,
            "value_dim": 128,
        },
        "logical_baseline_bytes": storage,
        "selection_row": selected,
        "source_hashes": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in sources
        },
        "output_csv": OUTPUT_CSV.relative_to(ROOT).as_posix(),
        "limitations": [
            "selection uses one development seed and synthetic nominal inputs",
            "held-out synthetic traces are not yet evaluated",
            "logical bytes are not physical BRAM/URAM allocation",
            "latency, energy, RTL, board, and closed-loop model evidence are NOT_RUN",
        ],
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Write-Log Candidate Selection",
        "",
        "Status: **PASS** for a development-only configuration freeze. This is not a paper-readiness or hardware gate.",
        "",
        f"Selected variant: `{selected['variant']}`.",
        "",
        "| Variant | Tokens | Output cosine | State rel L2 | Logical bytes | vs BF16 | vs MXFP8 | Synthetic gate | Physical evidence |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['variant']} | {row['tokens']} | "
            f"{float(row['output_cosine_fp32']):.6f} | "
            f"{float(row['state_rel_l2']):.6f} | "
            f"{row['logical_state_bytes']} | "
            f"{float(row['reduction_vs_bf16_percent']):.3f}% | "
            f"{float(row['reduction_vs_mxfp8_percent']):.3f}% | "
            f"{row['synthetic_gate']} | {row['physical_evidence']} |"
        )
    lines.extend(
        [
            "",
            "The selected point is the only tested full-8192 candidate that clears the frozen synthetic checkpoint gate while using fewer logical recurrent-state bytes than uniform MXFP8-B32. The seven-entry capacity is a development-tuned knee and must not be retuned after held-out access.",
            "",
            "The dense R=4/8/16 comparison remains required evidence. Sparse 1/4 and 2/4 residual-base variants and sparse 3/4 R=4 failed and remain preserved in the benchmark directory.",
            "",
            "Physical allocation, average and p99 service latency, energy, RTL parity, real-model quality, and board measurements remain `NOT_RUN` or `BLOCKED_EXTERNAL`. Logical storage does not establish a hardware Pareto result.",
            "",
            f"Machine-readable selection: `{OUTPUT_JSON.relative_to(ROOT).as_posix()}`.",
            f"Comparison CSV: `{OUTPUT_CSV.relative_to(ROOT).as_posix()}`.",
            "",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT_JSON.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Aggregate verified held-out write-log matrices without retuning."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CORRECTED = ROOT / "reports" / "benchmark" / "corrected"
MATRIX_MANIFESTS = (
    CORRECTED / "write_log_held_out_random" / "matrix_manifest.json",
    CORRECTED / "write_log_held_out_zero" / "matrix_manifest.json",
)
OUTPUT_SUMMARY = CORRECTED / "write_log_held_out_summary.csv"
OUTPUT_STATS = CORRECTED / "write_log_held_out_checkpoint_stats.csv"
OUTPUT_MANIFEST = CORRECTED / "write_log_held_out_manifest.json"
OUTPUT_REPORT = CORRECTED / "write_log_held_out.md"


SUMMARY_FIELDS = [
    "split",
    "seed",
    "trace_family",
    "initial_state_mode",
    "token_index",
    "variant",
    "output_cosine_fp32",
    "output_rel_l2",
    "state_rel_l2",
    "state_max_abs",
    "folds",
    "dropped_entries",
    "logical_state_bytes",
    "run_status",
    "run_manifest",
    "run_verification",
]
STATS_FIELDS = [
    "token_index",
    "metric",
    "count",
    "mean",
    "median",
    "p05",
    "p95",
    "minimum",
    "maximum",
    "worst",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    manifests = []
    summary_rows: list[dict[str, str]] = []
    selection_hashes = set()
    for path in MATRIX_MANIFESTS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS":
            raise RuntimeError(f"matrix is not PASS: {path}")
        summary = ROOT / str(payload["summary_csv"])
        if _sha256(summary) != payload["summary_sha256"]:
            raise RuntimeError(f"summary hash mismatch: {summary}")
        for run in payload["runs"]:
            if run["status"] != "PASS" or not run["gate_pass"]:
                raise RuntimeError(f"nonpassing run in {path}: {run['stem']}")
            verification = ROOT / str(run["verification"])
            if _sha256(verification) != run["verification_sha256"]:
                raise RuntimeError(f"verification hash mismatch: {verification}")
        selection_hashes.add(payload["selection_sha256"])
        manifests.append(payload)
        summary_rows.extend(_read_csv(summary))
    if len(selection_hashes) != 1:
        raise RuntimeError("held-out matrices used different selection freezes")

    keys = set()
    for row in summary_rows:
        key = (
            row["seed"],
            row["trace_family"],
            row["initial_state_mode"],
            row["token_index"],
        )
        if key in keys:
            raise RuntimeError(f"duplicate held-out checkpoint row: {key}")
        keys.add(key)
        if row["run_status"] != "PASS" or int(row["dropped_entries"]) != 0:
            raise RuntimeError(f"nonpassing held-out row: {key}")

    with OUTPUT_SUMMARY.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)

    grouped: dict[tuple[int, str], list[float]] = defaultdict(list)
    for row in summary_rows:
        token = int(row["token_index"])
        for metric in ("output_cosine_fp32", "state_rel_l2", "state_max_abs"):
            grouped[(token, metric)].append(float(row[metric]))
    stats_rows: list[dict[str, object]] = []
    for (token, metric), values in sorted(grouped.items()):
        array = np.asarray(values, dtype=np.float64)
        worst = float(np.min(array)) if metric == "output_cosine_fp32" else float(np.max(array))
        stats_rows.append(
            {
                "token_index": token,
                "metric": metric,
                "count": array.size,
                "mean": float(np.mean(array)),
                "median": float(np.median(array)),
                "p05": float(np.percentile(array, 5)),
                "p95": float(np.percentile(array, 95)),
                "minimum": float(np.min(array)),
                "maximum": float(np.max(array)),
                "worst": worst,
            }
        )
    with OUTPUT_STATS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=STATS_FIELDS)
        writer.writeheader()
        writer.writerows(stats_rows)

    cosine_values = [float(row["output_cosine_fp32"]) for row in summary_rows]
    final_rows = [row for row in summary_rows if int(row["token_index"]) == 8192]
    final_state_values = [float(row["state_rel_l2"]) for row in final_rows]
    gate_pass = (
        len(summary_rows) == 6 * 5
        and len(final_rows) == 6
        and min(cosine_values) >= 0.99
        and max(final_state_values) <= 0.10
        and all(int(row["dropped_entries"]) == 0 for row in summary_rows)
    )
    status = "PASS" if gate_pass else "FAIL"
    payload = {
        "schema": 1,
        "status": status,
        "scope": "held-out nominal synthetic engineering gate",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "selection_sha256": next(iter(selection_hashes)),
        "matrix_manifests": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in MATRIX_MANIFESTS
        },
        "trace_count": 6,
        "checkpoint_count_per_trace": 5,
        "seeds": [0xA11CE, 0xC0FFEE, 0x5EED5],
        "initial_states": ["random", "zero"],
        "trace_family": "nominal",
        "tokens": 8192,
        "worst_checkpoint_output_cosine_fp32": min(cosine_values),
        "worst_final_state_rel_l2": max(final_state_values),
        "maximum_dropped_entries": max(int(row["dropped_entries"]) for row in summary_rows),
        "outputs": {
            OUTPUT_SUMMARY.relative_to(ROOT).as_posix(): _sha256(OUTPUT_SUMMARY),
            OUTPUT_STATS.relative_to(ROOT).as_posix(): _sha256(OUTPUT_STATS),
        },
        "limitations": [
            "synthetic nominal inputs only",
            "floating Q/DQ candidate, not encoded-integer or RTL evidence",
            "no saturation/overflow telemetry from the encoded datapath",
            "not closed-loop Qwen quality evidence",
            "logical storage only; physical allocation remains NOT_RUN",
        ],
    }
    OUTPUT_MANIFEST.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# Held-Out Synthetic Write-Log Stability",
        "",
        f"Status: **{status}** for the preregistered nominal synthetic engineering gate.",
        "",
        "Configuration was frozen by `reports/benchmark/corrected/write_log_selection.json` before held-out access. Six traces cover three held-out seeds and both random and zero initial recurrent states.",
        "",
        "| Initial state | Seed | Token 8192 cosine | Token 8192 state rel L2 | State max abs | Drops |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(final_rows, key=lambda item: (item["initial_state_mode"], int(item["seed"]))):
        lines.append(
            f"| {row['initial_state_mode']} | {row['seed']} | "
            f"{float(row['output_cosine_fp32']):.6f} | "
            f"{float(row['state_rel_l2']):.6f} | "
            f"{float(row['state_max_abs']):.6f} | {row['dropped_entries']} |"
        )
    lines.extend(
        [
            "",
            f"Worst output cosine over all 30 required checkpoints: `{min(cosine_values):.6f}`.",
            f"Worst token-8192 state relative L2 over six traces: `{max(final_state_values):.6f}`.",
            "",
            "This passes the synthetic engineering threshold but does not establish encoded arithmetic parity, physical FPGA fit/energy, perplexity, downstream accuracy, or realistic closed-loop model quality.",
            "",
            f"Summary CSV: `{OUTPUT_SUMMARY.relative_to(ROOT).as_posix()}`.",
            f"Statistics CSV: `{OUTPUT_STATS.relative_to(ROOT).as_posix()}`.",
            f"Manifest: `{OUTPUT_MANIFEST.relative_to(ROOT).as_posix()}`.",
            "",
        ]
    )
    OUTPUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT_MANIFEST.relative_to(ROOT).as_posix())
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate and aggregate full-shape synthetic long-trace stress evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
STRESS_ROOT = ROOT / "reports" / "benchmark" / "corrected" / "stress"
DEFAULT_INPUTS = {
    "dynamic_range": STRESS_ROOT / "dynamic_range_8192_manifest.json",
    "cancellation": STRESS_ROOT / "cancellation_8192_manifest.json",
}
DEFAULT_CSV = STRESS_ROOT / "long_trace_stress_summary.csv"
DEFAULT_REPORT = STRESS_ROOT / "long_trace_stress_summary.md"
DEFAULT_MANIFEST = STRESS_ROOT / "long_trace_stress_summary_manifest.json"

CHECKPOINTS = (64, 256, 1024, 4096, 8192)
TOKENS = 8192
SEED = 0xFB72
VARIANTS = (
    "fp32",
    "bf16_qdq_fp32_accum_state_bf16",
    "mxfp4_qdq_act_b32_state_b32",
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32",
    "flat_int4_qdq",
)
VARIANT_LABELS = {
    "fp32": "FP32 reference",
    "bf16_qdq_fp32_accum_state_bf16": "BF16 state/operands, FP32 reductions",
    "mxfp4_qdq_act_b32_state_b32": "MXFP4 Q/DQ",
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32": "MXFP4 Q/DQ + MXFP8 state",
    "flat_int4_qdq": "Flat INT4 Q/DQ",
}
EXPECTED_CONFIGURATION = {
    "activation_block_size": 32,
    "checkpoints": list(CHECKPOINTS),
    "key_dim": 128,
    "num_qk_heads": 16,
    "num_value_heads": 32,
    "seed": SEED,
    "split": "development",
    "state_block_size": 32,
    "tokens": TOKENS,
    "value_dim": 128,
}
SUMMARY_FIELDS = (
    "trace_family",
    "variant",
    "variant_label",
    "tokens",
    "final_output_cosine_fp32",
    "final_state_rel_l2",
    "final_state_max_abs",
    "worst_output_cosine_fp32",
    "worst_output_cosine_token",
    "worst_state_rel_l2",
    "worst_state_rel_l2_token",
    "first_output_cosine_below_0p99",
    "first_state_rel_l2_above_0p10",
    "full_trace_threshold_status",
)


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_manifest(family: str, path: Path) -> tuple[dict[str, object], Path, Path]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    _require(payload.get("schema") == 1, f"{family}: manifest schema must be 1")
    _require(payload.get("status") == "PASS", f"{family}: manifest is not PASS")
    _require(
        payload.get("evidence_scope") == "synthetic_floating_qdq_diagnostic",
        f"{family}: wrong evidence scope",
    )
    configuration = payload.get("configuration")
    _require(isinstance(configuration, dict), f"{family}: missing configuration")
    for key, expected in EXPECTED_CONFIGURATION.items():
        _require(
            configuration.get(key) == expected,
            f"{family}: configuration {key} is {configuration.get(key)!r}, expected {expected!r}",
        )
    _require(
        configuration.get("trace_family") == family,
        f"{family}: trace-family label mismatch",
    )

    execution = payload.get("execution")
    _require(isinstance(execution, dict), f"{family}: missing execution record")
    command = str(execution.get("command", ""))
    _require(
        f"--trace-family {family}" in command,
        f"{family}: execution command does not bind the trace family",
    )
    _require(execution.get("exit_code") == 0, f"{family}: execution exit code is not zero")

    outputs = payload.get("outputs")
    _require(isinstance(outputs, dict), f"{family}: missing output hashes")
    token_key = f"reports/benchmark/corrected/stress/{family}_8192_tokens.csv"
    checkpoint_key = f"reports/benchmark/corrected/stress/{family}_8192_checkpoints.csv"
    for relative in (token_key, checkpoint_key):
        artifact = ROOT / relative
        _require(artifact.is_file(), f"{family}: missing {relative}")
        _require(outputs.get(relative) == _sha256(artifact), f"{family}: stale hash for {relative}")

    source_hashes = payload.get("source_hashes")
    _require(isinstance(source_hashes, dict), f"{family}: missing source hashes")
    for relative, expected_hash in source_hashes.items():
        source = ROOT / str(relative)
        _require(source.is_file(), f"{family}: missing source {relative}")
        _require(_sha256(source) == expected_hash, f"{family}: source hash drift for {relative}")

    return payload, ROOT / token_key, ROOT / checkpoint_key


def _metric(row: dict[str, str], field: str, *, family: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{family}: invalid {field} at token {row.get('token_index')}") from error
    _require(math.isfinite(value), f"{family}: non-finite {field}")
    return value


def _validate_rows(
    family: str,
    token_rows: list[dict[str, str]],
    checkpoint_rows: list[dict[str, str]],
) -> dict[tuple[int, str], dict[str, str]]:
    expected_count = TOKENS * len(VARIANTS)
    _require(len(token_rows) == expected_count, f"{family}: expected {expected_count} token rows")
    expected_run_id = f"synthetic_{SEED:08x}_{family}"
    indexed: dict[tuple[int, str], dict[str, str]] = {}
    for row in token_rows:
        token = int(row["token_index"])
        variant = row["variant"]
        key = (token, variant)
        _require(1 <= token <= TOKENS, f"{family}: token out of range")
        _require(variant in VARIANTS, f"{family}: unexpected variant {variant}")
        _require(key not in indexed, f"{family}: duplicate row {key}")
        _require(row["run_id"] == expected_run_id, f"{family}: run_id mismatch")
        _require(row["trace_family"] == family, f"{family}: row family mismatch")
        _require(row["split"] == "development", f"{family}: split mismatch")
        _require(int(row["seed"]) == SEED, f"{family}: seed mismatch")
        _require(int(row["layer_id"]) == 0, f"{family}: layer mismatch")
        cosine = _metric(row, "output_cosine_fp32", family=family)
        state_rel_l2 = _metric(row, "state_rel_l2", family=family)
        _metric(row, "state_max_abs", family=family)
        _require(-1.000001 <= cosine <= 1.000001, f"{family}: cosine out of range")
        _require(state_rel_l2 >= 0.0, f"{family}: negative state error")
        if variant == "fp32":
            _require(cosine == 1.0, f"{family}: FP32 cosine is not exact")
            _require(state_rel_l2 == 0.0, f"{family}: FP32 state error is not exact")
            _require(row["event_metrics_status"] == "PASS", f"{family}: FP32 events not PASS")
        else:
            _require(
                row["event_metrics_status"] == "NOT_RUN",
                f"{family}: Q/DQ event counters must remain NOT_RUN",
            )
        indexed[key] = row

    for token in range(1, TOKENS + 1):
        for variant in VARIANTS:
            _require((token, variant) in indexed, f"{family}: missing row {(token, variant)}")

    expected_checkpoint_count = len(CHECKPOINTS) * len(VARIANTS)
    _require(
        len(checkpoint_rows) == expected_checkpoint_count,
        f"{family}: expected {expected_checkpoint_count} checkpoint rows",
    )
    checkpoint_index: dict[tuple[int, str], dict[str, str]] = {}
    for row in checkpoint_rows:
        key = (int(row["token_index"]), row["variant"])
        _require(key[0] in CHECKPOINTS, f"{family}: unexpected checkpoint {key[0]}")
        _require(key not in checkpoint_index, f"{family}: duplicate checkpoint {key}")
        _require(row == indexed[key], f"{family}: checkpoint is not an exact token-row projection")
        checkpoint_index[key] = row
    for token in CHECKPOINTS:
        for variant in VARIANTS:
            _require((token, variant) in checkpoint_index, f"{family}: missing checkpoint {(token, variant)}")
    return indexed


def _summary_rows(family: str, indexed: dict[tuple[int, str], dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        trace = [indexed[(token, variant)] for token in range(1, TOKENS + 1)]
        final = trace[-1]
        cosines = [_metric(row, "output_cosine_fp32", family=family) for row in trace]
        state_errors = [_metric(row, "state_rel_l2", family=family) for row in trace]
        worst_cosine_index = min(range(TOKENS), key=cosines.__getitem__)
        worst_state_index = max(range(TOKENS), key=state_errors.__getitem__)
        first_cosine = next((index + 1 for index, value in enumerate(cosines) if value < 0.99), "")
        first_state = next((index + 1 for index, value in enumerate(state_errors) if value > 0.10), "")
        rows.append(
            {
                "trace_family": family,
                "variant": variant,
                "variant_label": VARIANT_LABELS[variant],
                "tokens": TOKENS,
                "final_output_cosine_fp32": _metric(final, "output_cosine_fp32", family=family),
                "final_state_rel_l2": _metric(final, "state_rel_l2", family=family),
                "final_state_max_abs": _metric(final, "state_max_abs", family=family),
                "worst_output_cosine_fp32": cosines[worst_cosine_index],
                "worst_output_cosine_token": worst_cosine_index + 1,
                "worst_state_rel_l2": state_errors[worst_state_index],
                "worst_state_rel_l2_token": worst_state_index + 1,
                "first_output_cosine_below_0p99": first_cosine,
                "first_state_rel_l2_above_0p10": first_state,
                "full_trace_threshold_status": (
                    "PASS" if min(cosines) >= 0.99 and max(state_errors) <= 0.10 else "FAIL"
                ),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: Path, rows: list[dict[str, object]], generated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Full-Shape Synthetic Long-Trace Stress Summary",
        "",
        f"Generated: `{generated_at}`",
        "",
        "Status: `PASS` for artifact validation; threshold outcomes are reported per row.",
        "",
        "| Trace | Variant | Token-8192 cosine | Token-8192 state rel L2 | Worst cosine | Worst state rel L2 | Diagnostic |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {trace_family} | {variant_label} | {final_output_cosine_fp32:.6f} | "
            "{final_state_rel_l2:.6f} | {worst_output_cosine_fp32:.6f} | "
            "{worst_state_rel_l2:.6f} | {full_trace_threshold_status} |".format(**row)
        )
    lines.extend(
        [
            "",
            "The thresholds are output cosine at least 0.99 and state relative L2 at most 0.10 at every token.",
            "These are synthetic floating-Q/DQ diagnostics, not native encoded arithmetic, closed-loop model quality, or real-activation outlier evidence.",
            "Event counters remain `NOT_RUN` for every Q/DQ comparator.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def aggregate(
    *,
    inputs: dict[str, Path],
    csv_path: Path,
    report_path: Path,
    manifest_path: Path,
    execution_command: str,
) -> dict[str, object]:
    _require(set(inputs) == set(DEFAULT_INPUTS), "inputs must contain dynamic_range and cancellation")
    generated_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, object]] = []
    input_hashes: dict[str, str] = {}
    revisions: set[str] = set()
    for family in ("dynamic_range", "cancellation"):
        manifest_file = _resolve(inputs[family])
        _require(manifest_file.is_file(), f"{family}: missing input manifest")
        payload, token_csv, checkpoint_csv = _validate_manifest(family, manifest_file)
        revisions.add(str(payload.get("source_revision")))
        indexed = _validate_rows(family, _read_csv(token_csv), _read_csv(checkpoint_csv))
        rows.extend(_summary_rows(family, indexed))
        for artifact in (manifest_file, token_csv, checkpoint_csv):
            input_hashes[_relative(artifact)] = _sha256(artifact)
    _require(len(revisions) == 1, "input source revisions do not match")

    csv_path = _resolve(csv_path)
    report_path = _resolve(report_path)
    manifest_path = _resolve(manifest_path)
    _write_csv(csv_path, rows)
    _write_report(report_path, rows, generated_at)
    source_identity = describe_source_files(
        [ROOT / "scripts" / "aggregate_long_trace_stress.py"]
    )
    manifest = {
        "schema": 1,
        "status": "PASS",
        "timestamp": generated_at,
        "source_revision": next(iter(revisions)),
        "evidence_scope": "supplemental_synthetic_floating_qdq_stress",
        "configuration": {
            **EXPECTED_CONFIGURATION,
            "trace_families": ["dynamic_range", "cancellation"],
            "variants": list(VARIANTS),
        },
        "row_count": len(rows),
        "input_sha256": input_hashes,
        "outputs": {
            _relative(csv_path): _sha256(csv_path),
            _relative(report_path): _sha256(report_path),
        },
        "execution": {"command": execution_command, "exit_code": 0},
        "source_identity": source_identity,
        "limitations": [
            "synthetic deterministic traces",
            "floating Q/DQ rather than native encoded arithmetic",
            "not fitted to model-derived activation distributions",
            "not closed-loop model-quality evidence",
            "integer event counters are NOT_RUN",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dynamic-range-manifest", type=Path, default=DEFAULT_INPUTS["dynamic_range"])
    parser.add_argument("--cancellation-manifest", type=Path, default=DEFAULT_INPUTS["cancellation"])
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    aggregate(
        inputs={
            "dynamic_range": args.dynamic_range_manifest,
            "cancellation": args.cancellation_manifest,
        },
        csv_path=args.csv,
        report_path=args.report,
        manifest_path=args.manifest,
        execution_command=subprocess.list2cmdline(
            ["python", "-m", "scripts.aggregate_long_trace_stress", *sys.argv[1:]]
        ),
    )
    print(_relative(_resolve(args.report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

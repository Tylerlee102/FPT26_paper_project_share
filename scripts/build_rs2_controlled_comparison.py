"""Join controlled floating baselines with the exact RS2/R3 MXFP4 trace."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.evidence_source_snapshot import describe_source_files
from scripts.long_sequence_stability import (
    ROOT,
    TOKEN_FIELDS,
    TraceConfiguration,
    _initial_state,
    _token_inputs,
    _update_input_hash,
)
from scripts.rs2_encoded_stability import (
    COUNTER_FIELDS,
    VARIANT as RS2_VARIANT,
)
from scripts.write_log_stability import _trace_initial_state, _trace_inputs


DEFAULT_DIR = ROOT / "reports" / "benchmark" / "corrected" / "rs2_controlled"
DEFAULT_BASELINE_TOKENS = DEFAULT_DIR / "high_retention_random_baselines_tokens.csv"
DEFAULT_BASELINE_MANIFEST = DEFAULT_DIR / "high_retention_random_baselines_manifest.json"
DEFAULT_RS2_TOKENS = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_encoded"
    / "extended_development"
    / "high_retention_0000fb72_random_8192_tokens.csv"
)
DEFAULT_RS2_MANIFEST = DEFAULT_RS2_TOKENS.with_name(
    "high_retention_0000fb72_random_8192_manifest.json"
)
DEFAULT_OUTPUT_TOKENS = DEFAULT_DIR / "controlled_long_trace_tokens.csv"
DEFAULT_OUTPUT_CHECKPOINTS = DEFAULT_DIR / "controlled_long_trace_checkpoints.csv"
DEFAULT_OUTPUT_MANIFEST = DEFAULT_DIR / "controlled_long_trace_manifest.json"
DEFAULT_OUTPUT_REPORT = DEFAULT_DIR / "controlled_long_trace.md"

CONFIG_FIELDS = (
    "tokens",
    "split",
    "seed",
    "trace_family",
    "num_value_heads",
    "num_qk_heads",
    "key_dim",
    "value_dim",
    "activation_block_size",
    "state_block_size",
)
EXTRA_FIELDS = (
    "initial_state_mode",
    *(f"cumulative_{name}" for name in COUNTER_FIELDS),
    "folded",
    "folds",
    "live_entries",
    "logical_state_bytes",
    "evidence_source",
)
OUTPUT_FIELDS = tuple(dict.fromkeys((*TOKEN_FIELDS, *EXTRA_FIELDS)))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV contains no rows: {path}")
    return rows


def _manifest_output_hash(manifest: dict[str, object], path: Path) -> str:
    relative = _relative(path)
    record = manifest.get("outputs", {}).get(relative)
    if isinstance(record, dict):
        record = record.get("sha256")
    if not isinstance(record, str) or len(record) != 64:
        raise ValueError(f"manifest does not bind output: {relative}")
    return record.lower()


def _configuration(payload: dict[str, object]) -> TraceConfiguration:
    raw = payload["configuration"]
    return TraceConfiguration(
        tokens=int(raw["tokens"]),
        checkpoints=tuple(int(value) for value in raw["checkpoints"]),
        seed=int(raw["seed"]),
        split=str(raw["split"]),
        trace_family=str(raw["trace_family"]),
        num_value_heads=int(raw["num_value_heads"]),
        num_qk_heads=int(raw["num_qk_heads"]),
        key_dim=int(raw["key_dim"]),
        value_dim=int(raw["value_dim"]),
        activation_block_size=int(raw["activation_block_size"]),
        state_block_size=int(raw["state_block_size"]),
    )


def _verify_configuration(
    baseline: TraceConfiguration, candidate: TraceConfiguration
) -> None:
    for field in CONFIG_FIELDS:
        if getattr(baseline, field) != getattr(candidate, field):
            raise ValueError(f"controlled configuration mismatch: {field}")
    if baseline.checkpoints != candidate.checkpoints:
        raise ValueError("controlled configuration mismatch: checkpoints")


def _recompute_trace_hashes(config: TraceConfiguration) -> dict[str, str]:
    baseline_initial = _initial_state(config)
    candidate_initial = _trace_initial_state(config, "random")
    if not np.array_equal(baseline_initial, candidate_initial):
        raise ValueError("baseline and RS2 initial states differ")

    labelled = hashlib.sha256()
    raw = hashlib.sha256()
    _update_input_hash(labelled, "initial_state", baseline_initial)
    raw.update(np.ascontiguousarray(candidate_initial).tobytes())
    for token_index in range(config.tokens):
        baseline_arrays = _token_inputs(config, token_index)
        candidate_arrays = _trace_inputs(config, token_index)
        for name, baseline_array, candidate_array in zip(
            ("q", "k", "v", "alpha", "beta"),
            baseline_arrays,
            candidate_arrays,
            strict=True,
        ):
            if not np.array_equal(baseline_array, candidate_array):
                raise ValueError(
                    f"baseline and RS2 input differ at token {token_index}: {name}"
                )
            _update_input_hash(labelled, name, baseline_array)
            raw.update(np.ascontiguousarray(candidate_array).tobytes())
    return {
        "labelled_input_sha256": labelled.hexdigest(),
        "raw_input_sha256": raw.hexdigest(),
        "initial_state_sha256": hashlib.sha256(
            np.ascontiguousarray(baseline_initial).tobytes()
        ).hexdigest(),
    }


def _normalized(
    row: dict[str, str], *, initial_state_mode: str, evidence_source: str
) -> dict[str, object]:
    normalized: dict[str, object] = {field: row.get(field, "") for field in OUTPUT_FIELDS}
    normalized["initial_state_mode"] = initial_state_mode
    normalized["evidence_source"] = evidence_source
    return normalized


def _validate_rows(
    rows: list[dict[str, str]],
    *,
    config: TraceConfiguration,
    variants: set[str],
) -> None:
    expected_tokens = set(range(1, config.tokens + 1))
    observed_variants = {row["variant"] for row in rows}
    if observed_variants != variants:
        raise ValueError(
            f"variant mismatch: expected {sorted(variants)}, got {sorted(observed_variants)}"
        )
    for variant in variants:
        variant_rows = [row for row in rows if row["variant"] == variant]
        observed_tokens = {int(row["token_index"]) for row in variant_rows}
        if len(variant_rows) != config.tokens or observed_tokens != expected_tokens:
            raise ValueError(f"token coverage mismatch: {variant}")
    for row in rows:
        if (
            int(row["seed"]) != config.seed
            or row["split"] != config.split
            or row["trace_family"] != config.trace_family
        ):
            raise ValueError("row metadata does not match controlled configuration")
        for field in ("output_cosine_fp32", "state_rel_l2", "state_max_abs"):
            if not np.isfinite(float(row[field])):
                raise ValueError(f"nonfinite metric in {field}")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: Path,
    *,
    config: TraceConfiguration,
    checkpoint_rows: list[dict[str, object]],
    variants: list[str],
) -> None:
    by_key = {
        (str(row["variant"]), int(row["token_index"])): row
        for row in checkpoint_rows
    }
    lines = [
        "# Controlled RS2/R3 Long-Sequence Comparison",
        "",
        "Status: `PASS`",
        "",
        (
            f"All paths use the same `{config.trace_family}` synthetic trace, random "
            f"initial state, seed `0x{config.seed:08X}`, GDN layer shape, B32 block size, "
            "and FP32 recurrence reference."
        ),
        "",
        "| Token | Variant | Output cosine | State relative L2 | State max abs |",
        "|---:|---|---:|---:|---:|",
    ]
    for token_index in config.checkpoints:
        for variant in variants:
            row = by_key[(variant, token_index)]
            lines.append(
                f"| {token_index} | {variant} | "
                f"{float(row['output_cosine_fp32']):.6f} | "
                f"{float(row['state_rel_l2']):.6f} | "
                f"{float(row['state_max_abs']):.6f} |"
            )
    lines.extend(
        [
            "",
            "The exact RS2/R3 row carries encoded arithmetic event counters. Floating "
            "Q/DQ rows remain diagnostic and do not claim encoded hardware parity.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build(
    baseline_tokens: Path,
    baseline_manifest_path: Path,
    rs2_tokens: Path,
    rs2_manifest_path: Path,
    output_tokens: Path,
    output_checkpoints: Path,
    output_manifest: Path,
    output_report: Path,
    *,
    execution_command: str = "library call: build_rs2_controlled_comparison",
) -> dict[str, object]:
    baseline_manifest = _read_json(baseline_manifest_path)
    rs2_manifest = _read_json(rs2_manifest_path)
    if baseline_manifest.get("status") != "PASS":
        raise ValueError("floating baseline manifest is not PASS")
    if rs2_manifest.get("status") != "PASS":
        raise ValueError("RS2/R3 manifest is not PASS")
    if rs2_manifest.get("initial_state_mode") != "random":
        raise ValueError("controlled comparison requires the random initial-state run")
    if rs2_manifest.get("variant") != RS2_VARIANT:
        raise ValueError("RS2/R3 manifest has the wrong candidate")
    if not rs2_manifest.get("gate", {}).get("gate_pass"):
        raise ValueError("RS2/R3 quality gate did not pass")

    if _manifest_output_hash(baseline_manifest, baseline_tokens) != _sha256(
        baseline_tokens
    ):
        raise ValueError("floating baseline CSV hash mismatch")
    if _manifest_output_hash(rs2_manifest, rs2_tokens) != _sha256(rs2_tokens):
        raise ValueError("RS2/R3 CSV hash mismatch")

    baseline_config = _configuration(baseline_manifest)
    rs2_config = _configuration(rs2_manifest)
    _verify_configuration(baseline_config, rs2_config)
    hashes = _recompute_trace_hashes(baseline_config)
    if baseline_manifest.get("input_sha256", "").lower() != hashes[
        "labelled_input_sha256"
    ]:
        raise ValueError("floating baseline input-stream hash mismatch")
    if baseline_manifest.get("initial_state_sha256", "").lower() != hashes[
        "initial_state_sha256"
    ]:
        raise ValueError("floating baseline initial-state hash mismatch")
    if rs2_manifest.get("input_stream_sha256", "").lower() != hashes[
        "raw_input_sha256"
    ]:
        raise ValueError("RS2/R3 input-stream hash mismatch")

    baseline_rows = _read_rows(baseline_tokens)
    rs2_rows_all = _read_rows(rs2_tokens)
    baseline_variants = {row["variant"] for row in baseline_rows}
    _validate_rows(
        baseline_rows,
        config=baseline_config,
        variants=baseline_variants,
    )
    rs2_rows = [row for row in rs2_rows_all if row["variant"] == RS2_VARIANT]
    _validate_rows(
        rs2_rows,
        config=baseline_config,
        variants={RS2_VARIANT},
    )
    if RS2_VARIANT in baseline_variants:
        raise ValueError("RS2/R3 candidate is duplicated in floating baseline CSV")

    combined = [
        _normalized(
            row,
            initial_state_mode="random",
            evidence_source=_relative(baseline_tokens),
        )
        for row in baseline_rows
    ]
    combined.extend(
        _normalized(
            row,
            initial_state_mode="random",
            evidence_source=_relative(rs2_tokens),
        )
        for row in rs2_rows
    )
    combined.sort(key=lambda row: (int(row["token_index"]), str(row["variant"])))
    checkpoints = set(baseline_config.checkpoints)
    checkpoint_rows = [
        row for row in combined if int(row["token_index"]) in checkpoints
    ]
    _write_csv(output_tokens, combined)
    _write_csv(output_checkpoints, checkpoint_rows)
    variants = sorted(baseline_variants | {RS2_VARIANT})
    _write_report(
        output_report,
        config=baseline_config,
        checkpoint_rows=checkpoint_rows,
        variants=variants,
    )

    source_identity = describe_source_files(
        [
            Path(__file__).resolve(),
            ROOT / "scripts" / "long_sequence_stability.py",
            ROOT / "scripts" / "rs2_encoded_stability.py",
            ROOT / "scripts" / "write_log_stability.py",
        ]
    )
    payload = {
        "schema": 1,
        "status": "PASS",
        "evidence_scope": "controlled_synthetic_fp32_bf16_mxfp4_mxfp8_int4_comparison",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            **baseline_config.__dict__,
            "initial_state_mode": "random",
            "variants": variants,
        },
        "trace_identity": {
            **hashes,
            "status": "PASS",
            "method": (
                "Regenerated every initial-state and token tensor through both input "
                "entry points; asserted bitwise equality and matched each upstream "
                "manifest's native digest convention."
            ),
        },
        "upstream": {
            "floating_baseline_manifest": {
                "path": _relative(baseline_manifest_path),
                "sha256": _sha256(baseline_manifest_path),
            },
            "rs2_encoded_manifest": {
                "path": _relative(rs2_manifest_path),
                "sha256": _sha256(rs2_manifest_path),
            },
        },
        "execution": {"command": execution_command, "exit_code": 0},
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "outputs": {
            _relative(output_tokens): _sha256(output_tokens),
            _relative(output_checkpoints): _sha256(output_checkpoints),
            _relative(output_report): _sha256(output_report),
        },
        "limitations": [
            "single deterministic layer-level high-retention synthetic trace",
            "floating Q/DQ baselines do not expose encoded arithmetic event counters",
            "not closed-loop model quality, board telemetry, or measured board energy",
        ],
    }
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-tokens", type=Path, default=DEFAULT_BASELINE_TOKENS)
    parser.add_argument(
        "--baseline-manifest", type=Path, default=DEFAULT_BASELINE_MANIFEST
    )
    parser.add_argument("--rs2-tokens", type=Path, default=DEFAULT_RS2_TOKENS)
    parser.add_argument("--rs2-manifest", type=Path, default=DEFAULT_RS2_MANIFEST)
    parser.add_argument("--output-tokens", type=Path, default=DEFAULT_OUTPUT_TOKENS)
    parser.add_argument(
        "--output-checkpoints", type=Path, default=DEFAULT_OUTPUT_CHECKPOINTS
    )
    parser.add_argument("--output-manifest", type=Path, default=DEFAULT_OUTPUT_MANIFEST)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_OUTPUT_REPORT)
    args = parser.parse_args(argv)
    command = subprocess.list2cmdline(
        [sys.executable, "-m", "scripts.build_rs2_controlled_comparison", *sys.argv[1:]]
    )
    payload = build(
        _resolve(args.baseline_tokens),
        _resolve(args.baseline_manifest),
        _resolve(args.rs2_tokens),
        _resolve(args.rs2_manifest),
        _resolve(args.output_tokens),
        _resolve(args.output_checkpoints),
        _resolve(args.output_manifest),
        _resolve(args.output_report),
        execution_command=command,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "manifest": _relative(_resolve(args.output_manifest)),
                "variants": payload["configuration"]["variants"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

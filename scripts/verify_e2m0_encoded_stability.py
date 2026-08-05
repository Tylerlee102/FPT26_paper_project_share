"""Verify and optionally recompute one encoded E2M0 stability artifact."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.e2m0_encoded_stability import (
    CAPACITY,
    FIELDS,
    ROOT,
    VARIANT,
    logical_encoded_state_bytes,
    run_encoded_trace,
)
from scripts.long_sequence_stability import TraceConfiguration


INTEGER_FIELDS = {
    "seed",
    "token_index",
    "element_saturations",
    "accumulator_saturations",
    "scale_clamps",
    "alignment_underflows",
    "state_scale_changes",
    "e2m0_residual_clips",
    "cumulative_element_saturations",
    "cumulative_accumulator_saturations",
    "cumulative_scale_clamps",
    "cumulative_alignment_underflows",
    "cumulative_state_scale_changes",
    "cumulative_e2m0_residual_clips",
    "folded",
    "folds",
    "live_entries",
    "logical_state_bytes",
}
FLOAT_FIELDS = {
    "output_cosine_fp32",
    "output_rel_l2",
    "output_max_abs",
    "state_rel_l2",
    "state_max_abs",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _resolve(relative: str) -> Path:
    path = Path(relative)
    return path if path.is_absolute() else ROOT / path


def _rows_equal(actual: dict[str, str], expected: dict[str, object]) -> bool:
    for field in FIELDS:
        if field in INTEGER_FIELDS:
            if int(actual[field]) != int(expected[field]):
                return False
        elif field in FLOAT_FIELDS:
            if float(actual[field]) != float(expected[field]):
                return False
        elif str(actual[field]) != str(expected[field]):
            return False
    return True


def verify_manifest(
    manifest_path: Path,
    *,
    recompute: bool,
) -> dict[str, object]:
    failures: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = TraceConfiguration(**manifest["configuration"])
    if manifest.get("variant") != VARIANT:
        failures.append("variant mismatch")
    contract = manifest.get("arithmetic_contract", {})
    if contract.get("accumulator_bits") != 32 or contract.get(
        "alignment_guard_bits"
    ) != 5:
        failures.append("arithmetic contract mismatch")
    if int(contract.get("capacity", -1)) != CAPACITY:
        failures.append("capacity mismatch")
    expected_bytes = logical_encoded_state_bytes(config)
    if int(manifest.get("logical_state_bytes", -1)) != expected_bytes:
        failures.append("logical state byte mismatch")

    for relative, expected_hash in manifest.get("source_sha256", {}).items():
        path = _resolve(relative)
        if not path.is_file() or _sha256(path) != str(expected_hash).upper():
            failures.append(f"source hash mismatch: {relative}")
    output_paths: dict[str, Path] = {}
    for relative, expected_hash in manifest.get("outputs", {}).items():
        path = _resolve(relative)
        output_paths[relative] = path
        if not path.is_file() or _sha256(path) != str(expected_hash).upper():
            failures.append(f"output hash mismatch: {relative}")
    csv_paths = [path for path in output_paths.values() if path.suffix == ".csv"]
    token_candidates = [path for path in csv_paths if path.name.endswith("_tokens.csv")]
    checkpoint_candidates = [
        path for path in csv_paths if path.name.endswith("_checkpoints.csv")
    ]
    if len(token_candidates) != 1 or len(checkpoint_candidates) != 1:
        failures.append("manifest must name one token and one checkpoint CSV")
        token_rows: list[dict[str, str]] = []
        checkpoint_rows: list[dict[str, str]] = []
    else:
        token_fields, token_rows = _read_rows(token_candidates[0])
        checkpoint_fields, checkpoint_rows = _read_rows(checkpoint_candidates[0])
        if token_fields != FIELDS or checkpoint_fields != FIELDS:
            failures.append("CSV schema mismatch")

    if len(token_rows) != config.tokens * 2:
        failures.append("token row count mismatch")
    candidate_rows = [row for row in token_rows if row.get("variant") == VARIANT]
    fp32_rows = [row for row in token_rows if row.get("variant") == "fp32"]
    if len(candidate_rows) != config.tokens or len(fp32_rows) != config.tokens:
        failures.append("variant row count mismatch")
    token_projection = {
        (int(row["token_index"]), row["variant"]): row for row in token_rows
    }
    expected_checkpoint_keys = {
        (token, variant)
        for token in config.checkpoints
        for variant in ("fp32", VARIANT)
    }
    actual_checkpoint_keys = {
        (int(row["token_index"]), row["variant"]) for row in checkpoint_rows
    }
    if actual_checkpoint_keys != expected_checkpoint_keys:
        failures.append("checkpoint key mismatch")
    for row in checkpoint_rows:
        if token_projection.get((int(row["token_index"]), row["variant"])) != row:
            failures.append("checkpoint projection mismatch")
            break

    running = {
        "element_saturations": 0,
        "accumulator_saturations": 0,
        "scale_clamps": 0,
        "alignment_underflows": 0,
        "state_scale_changes": 0,
        "e2m0_residual_clips": 0,
    }
    for expected_token, row in enumerate(candidate_rows, start=1):
        if int(row["token_index"]) != expected_token:
            failures.append("candidate token sequence mismatch")
            break
        expected_fold = int(expected_token % CAPACITY == 0)
        expected_folds = expected_token // CAPACITY
        expected_live = expected_token % CAPACITY
        if (
            int(row["folded"]) != expected_fold
            or int(row["folds"]) != expected_folds
            or int(row["live_entries"]) != expected_live
        ):
            failures.append(f"fold schedule mismatch at token {expected_token}")
            break
        if int(row["logical_state_bytes"]) != expected_bytes:
            failures.append(f"logical byte mismatch at token {expected_token}")
            break
        for name in running:
            running[name] += int(row[name])
            if int(row[f"cumulative_{name}"]) != running[name]:
                failures.append(
                    f"counter prefix mismatch at token {expected_token}: {name}"
                )
                break

    candidate_checkpoints = [
        row for row in checkpoint_rows if row.get("variant") == VARIANT
    ]
    final = [
        row
        for row in candidate_checkpoints
        if int(row["token_index"]) == config.tokens
    ]
    derived_gate = (
        bool(candidate_checkpoints)
        and all(float(row["output_cosine_fp32"]) >= 0.99 for row in candidate_checkpoints)
        and len(final) == 1
        and float(final[0]["state_rel_l2"]) <= 0.10
        and running["element_saturations"] == 0
        and running["accumulator_saturations"] == 0
        and running["scale_clamps"] == 0
    )
    declared_gate = bool(manifest.get("gate", {}).get("gate_pass"))
    if derived_gate != declared_gate:
        failures.append("declared gate does not match rows")
    expected_status = "PASS" if derived_gate else "FAIL"
    if manifest.get("status") != expected_status:
        failures.append("manifest status does not match derived gate")

    recomputed = False
    if recompute and not failures:
        repeated = run_encoded_trace(
            config,
            initial_state_mode=str(manifest["initial_state_mode"]),
        )
        recomputed = True
        if repeated.input_stream_sha256.upper() != str(
            manifest["input_stream_sha256"]
        ).upper():
            failures.append("recomputed input stream hash mismatch")
        if repeated.gate_pass != declared_gate:
            failures.append("recomputed gate mismatch")
        if len(repeated.token_rows) != len(token_rows) or any(
            not _rows_equal(actual, expected)
            for actual, expected in zip(token_rows, repeated.token_rows)
        ):
            failures.append("recomputed token rows mismatch")
        if len(repeated.checkpoint_rows) != len(checkpoint_rows) or any(
            not _rows_equal(actual, expected)
            for actual, expected in zip(checkpoint_rows, repeated.checkpoint_rows)
        ):
            failures.append("recomputed checkpoint rows mismatch")

    return {
        "schema": 1,
        "status": "PASS" if not failures else "FAIL",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": manifest_path.relative_to(ROOT).as_posix()
        if manifest_path.is_relative_to(ROOT)
        else str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "candidate_gate": expected_status,
        "recomputed": recomputed,
        "token_rows": len(token_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "cumulative_counters": running,
        "failures": failures,
        "independent_checks": [
            "source and output hashes",
            "CSV schemas and row counts",
            "checkpoint projection",
            "fixed fold/live-entry schedule",
            "counter prefix sums",
            "quality and arithmetic-event gate",
            "full deterministic rerun and fieldwise equality" if recompute else "rerun NOT_RUN",
            "scalar/vectorized bit-exact tests are separate pytest evidence",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--recompute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    result = verify_manifest(manifest, recompute=args.recompute)
    output = args.output
    if output is None:
        output = manifest.with_name(manifest.stem.replace("_manifest", "") + "_verification.json")
    elif not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidate_gate": result["candidate_gate"],
                "recomputed": result["recomputed"],
                "failures": len(result["failures"]),
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())


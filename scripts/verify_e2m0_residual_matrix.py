"""Independently verify all preregistered E2M0 residual candidate matrices."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "reports" / "benchmark" / "corrected" / "e2m0_residual"
REGISTRATION = (
    ROOT / "reports" / "benchmark" / "corrected" / "e2m0_residual_preregistration.json"
)
MATRICES = {
    "development_robustness": REPORT_ROOT / "development_robustness" / "matrix_manifest.json",
    "extended_development": REPORT_ROOT / "extended_development" / "matrix_manifest.json",
    "held_out": REPORT_ROOT / "held_out" / "matrix_manifest.json",
}
OUTPUT_JSON = REPORT_ROOT / "e2m0_residual_evidence_summary.json"
OUTPUT_MD = REPORT_ROOT / "e2m0_residual_evidence_summary.md"
VARIANT = "mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7"
EXPECTED_BYTES = 538_256


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _expected_specs(
    gate: str,
    registration: dict[str, object],
) -> tuple[str, int, tuple[int, ...], list[tuple[int, str, str]]]:
    if gate == "development_robustness":
        rule = dict(registration["development_robustness_gate"])
        seeds = [int(value) for value in rule["high_retention_seeds"]]
        states = [str(value) for value in rule["initial_states"]]
        specs = [
            (seeds[0], str(family), state)
            for family in rule["families_for_seed_0xfb72"]
            for state in states
        ]
        specs += [
            (seed, "high_retention", state)
            for seed in seeds[1:]
            for state in states
        ]
        return (
            "development",
            int(rule["tokens"]),
            tuple(int(value) for value in rule["checkpoints"]),
            specs,
        )
    if gate == "extended_development":
        rule = dict(registration["extended_development_gate"])
        specs = [
            (int(rule["seed"]), str(rule["trace_family"]), str(state))
            for state in rule["initial_states"]
        ]
        return (
            "development",
            int(rule["tokens"]),
            tuple(int(value) for value in rule["checkpoints"]),
            specs,
        )
    rule = dict(registration["held_out_gate"])
    specs = [
        (int(seed), str(family), str(state))
        for seed in rule["seeds"]
        for family in rule["families"]
        for state in rule["initial_states"]
    ]
    return (
        "held_out",
        int(rule["tokens"]),
        tuple(int(value) for value in rule["checkpoints"]),
        specs,
    )


def _expected_summary_row(
    gate: str,
    split: str,
    seed: int,
    family: str,
    initial_state: str,
    row: dict[str, str],
    manifest: Path,
    verification: Path,
) -> dict[str, str]:
    return {
        "gate": gate,
        "split": split,
        "seed": str(seed),
        "trace_family": family,
        "initial_state_mode": initial_state,
        "token_index": row["token_index"],
        "variant": row["variant"],
        "output_cosine_fp32": row["output_cosine_fp32"],
        "output_rel_l2": row["output_rel_l2"],
        "state_rel_l2": row["state_rel_l2"],
        "state_max_abs": row["state_max_abs"],
        "folds": row["folds"],
        "dropped_entries": row["dropped_entries"],
        "logical_state_bytes": row["logical_state_bytes"],
        "run_status": "PASS",
        "run_manifest": manifest.relative_to(ROOT).as_posix(),
        "run_verification": verification.relative_to(ROOT).as_posix(),
    }


def verify_all() -> dict[str, object]:
    failures: list[str] = []
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    registration_hash = _sha256(REGISTRATION)
    if registration.get("registration_status") != "PASS":
        failures.append("registration status is not PASS")
    if registration.get("candidate_evidence_status") != "NOT_RUN":
        failures.append("frozen registration was edited after execution")
    if registration.get("candidate_name") != VARIANT:
        failures.append("registered candidate name mismatch")
    if int(registration["logical_state_bytes"]["candidate"]) != EXPECTED_BYTES:
        failures.append("registered logical byte count mismatch")
    if EXPECTED_BYTES >= int(
        registration["logical_state_bytes"]["uniform_mxfp8_e4m3_b32"]
    ):
        failures.append("candidate does not beat uniform MXFP8 logical bytes")
    for relative, expected in dict(registration["source_hashes"]).items():
        source = ROOT / relative
        if not source.is_file() or _sha256(source) != str(expected).upper():
            failures.append(f"frozen source mismatch: {relative}")

    matrix_results: dict[str, dict[str, object]] = {}
    total_token_rows = 0
    total_checkpoint_rows = 0
    all_input_hashes: list[str] = []
    held_out_seeds = set(int(value) for value in registration["held_out_gate"]["seeds"])
    development_seeds = set(
        int(value)
        for value in registration["development_robustness_gate"]["high_retention_seeds"]
    )
    if held_out_seeds & development_seeds:
        failures.append("held-out and development seeds overlap")

    for gate, matrix_path in MATRICES.items():
        gate_failure_start = len(failures)
        if not matrix_path.is_file():
            failures.append(f"missing matrix manifest: {gate}")
            continue
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        split, tokens, checkpoints, specs = _expected_specs(gate, registration)
        if matrix.get("status") != "PASS":
            failures.append(f"matrix status is not PASS: {gate}")
        if matrix.get("gate") != gate or matrix.get("split") != split:
            failures.append(f"matrix identity mismatch: {gate}")
        if int(matrix.get("tokens", -1)) != tokens:
            failures.append(f"matrix token length mismatch: {gate}")
        if tuple(int(value) for value in matrix.get("checkpoints", [])) != checkpoints:
            failures.append(f"matrix checkpoint mismatch: {gate}")
        if str(matrix.get("registration_sha256", "")).upper() != registration_hash:
            failures.append(f"matrix registration hash mismatch: {gate}")

        records = list(matrix.get("runs", []))
        expected_stems = [
            f"{split}_seed{seed:08x}_{family}_{initial_state}"
            for seed, family, initial_state in specs
        ]
        if [str(record.get("stem")) for record in records] != expected_stems:
            failures.append(f"matrix run order/specification mismatch: {gate}")
        summary_path = ROOT / str(matrix.get("summary_csv", ""))
        if not summary_path.is_file() or _sha256(summary_path) != str(
            matrix.get("summary_sha256", "")
        ).upper():
            failures.append(f"matrix summary hash mismatch: {gate}")
            summary_rows: list[dict[str, str]] = []
        else:
            summary_rows = _rows(summary_path)

        expected_summary: list[dict[str, str]] = []
        gate_cosines: list[float] = []
        final_state_errors: list[float] = []
        gate_max_errors: list[float] = []
        for record, (seed, family, initial_state) in zip(records, specs):
            if record.get("status") != "PASS" or record.get("gate_pass") is not True:
                failures.append(f"run status/gate failure: {record.get('stem')}")
            manifest = ROOT / str(record.get("manifest", ""))
            verification = ROOT / str(record.get("verification", ""))
            if not manifest.is_file() or _sha256(manifest) != str(
                record.get("manifest_sha256", "")
            ).upper():
                failures.append(f"run manifest hash mismatch: {record.get('stem')}")
                continue
            if not verification.is_file() or _sha256(verification) != str(
                record.get("verification_sha256", "")
            ).upper():
                failures.append(f"run verification hash mismatch: {record.get('stem')}")
                continue
            run_manifest = json.loads(manifest.read_text(encoding="utf-8"))
            run_verification = json.loads(verification.read_text(encoding="utf-8"))
            if run_verification.get("status") != "PASS" or run_verification.get(
                "gate_pass"
            ) is not True:
                failures.append(f"independent run verification failed: {record.get('stem')}")
            if str(run_verification.get("manifest_sha256", "")).upper() != _sha256(
                manifest
            ):
                failures.append(f"verification/manifest mismatch: {record.get('stem')}")
            if run_manifest.get("variant") != VARIANT:
                failures.append(f"run candidate mismatch: {record.get('stem')}")
            if int(run_manifest.get("logical_state_bytes", -1)) != EXPECTED_BYTES:
                failures.append(f"run logical byte mismatch: {record.get('stem')}")
            if str(run_manifest.get("input_stream_sha256", "")) != str(
                record.get("input_stream_sha256", "")
            ):
                failures.append(f"run input hash mismatch: {record.get('stem')}")
            all_input_hashes.append(str(record.get("input_stream_sha256", "")))

            outputs = dict(run_manifest.get("outputs", {}))
            token_path = next(
                (ROOT / name for name in outputs if name.endswith("_tokens.csv")), None
            )
            checkpoint_path = next(
                (ROOT / name for name in outputs if name.endswith("_checkpoints.csv")),
                None,
            )
            if token_path is None or checkpoint_path is None:
                failures.append(f"run output paths missing: {record.get('stem')}")
                continue
            for path in (token_path, checkpoint_path):
                expected_hash = outputs[path.relative_to(ROOT).as_posix()]
                if not path.is_file() or _sha256(path) != str(expected_hash).upper():
                    failures.append(f"run CSV hash mismatch: {path}")
            token_rows = _rows(token_path)
            checkpoint_rows = _rows(checkpoint_path)
            total_token_rows += len(token_rows)
            total_checkpoint_rows += len(checkpoint_rows)
            if len(token_rows) != tokens * 2:
                failures.append(f"run token row count mismatch: {record.get('stem')}")
            if len(checkpoint_rows) != len(checkpoints) * 2:
                failures.append(f"run checkpoint row count mismatch: {record.get('stem')}")
            token_map = {
                (int(row["token_index"]), row["variant"]): row for row in token_rows
            }
            if len(token_map) != len(token_rows):
                failures.append(f"duplicate token rows: {record.get('stem')}")
            candidates = [row for row in token_rows if row["variant"] == VARIANT]
            for row in candidates:
                token = int(row["token_index"])
                if int(row["folds"]) != token // 7:
                    failures.append(f"fold schedule mismatch: {record.get('stem')}:{token}")
                if int(row["live_entries"]) != token % 7:
                    failures.append(f"live log mismatch: {record.get('stem')}:{token}")
                if int(row["dropped_entries"]) != 0:
                    failures.append(f"dropped write: {record.get('stem')}:{token}")
                if int(row["logical_state_bytes"]) != EXPECTED_BYTES:
                    failures.append(f"row logical bytes mismatch: {record.get('stem')}:{token}")
            candidate_checkpoints = [
                row for row in checkpoint_rows if row["variant"] == VARIANT
            ]
            for row in checkpoint_rows:
                key = (int(row["token_index"]), row["variant"])
                if token_map.get(key) != row:
                    failures.append(f"checkpoint projection mismatch: {record.get('stem')}:{key}")
            for row in candidate_checkpoints:
                cosine = float(row["output_cosine_fp32"])
                if not math.isfinite(cosine) or cosine < 0.99:
                    failures.append(f"cosine gate failure: {record.get('stem')}")
                gate_cosines.append(cosine)
                gate_max_errors.append(float(row["state_max_abs"]))
                expected_summary.append(
                    _expected_summary_row(
                        gate,
                        split,
                        seed,
                        family,
                        initial_state,
                        row,
                        manifest,
                        verification,
                    )
                )
            final = [
                row for row in candidate_checkpoints if int(row["token_index"]) == tokens
            ]
            if len(final) != 1 or float(final[0]["state_rel_l2"]) > 0.10:
                failures.append(f"state gate failure: {record.get('stem')}")
            elif final:
                final_state_errors.append(float(final[0]["state_rel_l2"]))

        if summary_rows != expected_summary:
            failures.append(f"matrix summary projection mismatch: {gate}")
        matrix_results[gate] = {
            "status": "PASS" if len(failures) == gate_failure_start else "FAIL",
            "runs": len(records),
            "tokens_per_run": tokens,
            "checkpoint_count": len(checkpoints),
            "minimum_checkpoint_output_cosine": min(gate_cosines) if gate_cosines else None,
            "maximum_final_state_relative_l2": max(final_state_errors) if final_state_errors else None,
            "maximum_checkpoint_state_abs_error": max(gate_max_errors) if gate_max_errors else None,
            "matrix_manifest": matrix_path.relative_to(ROOT).as_posix(),
            "matrix_manifest_sha256": _sha256(matrix_path),
            "summary_sha256": _sha256(summary_path) if summary_path.is_file() else None,
        }

    expected_runs = sum(result["runs"] for result in matrix_results.values())
    if len(all_input_hashes) != expected_runs:
        failures.append("aggregate input hash count mismatch")
    if len(set(all_input_hashes)) != len(all_input_hashes):
        # The extended traces intentionally share prefixes but their full-stream
        # hashes differ because their lengths differ.
        failures.append("duplicate full input-stream hashes")

    return {
        "schema": 1,
        "status": "PASS" if not failures else "FAIL",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "candidate": VARIANT,
        "candidate_software_stability": "PASS" if not failures else "FAIL",
        "selected_method_hardware_pareto": "NOT_RUN",
        "logical_state_bytes": EXPECTED_BYTES,
        "uniform_mxfp8_state_bytes": 540_672,
        "logical_reduction_vs_uniform_mxfp8_percent": 100.0
        * (1.0 - EXPECTED_BYTES / 540_672),
        "registration": REGISTRATION.relative_to(ROOT).as_posix(),
        "registration_sha256": registration_hash,
        "matrices": matrix_results,
        "run_count": expected_runs,
        "token_row_count": total_token_rows,
        "checkpoint_row_count": total_checkpoint_rows,
        "failures": failures,
        "limitations": [
            "layer-level deterministic synthetic traces only",
            "floating quantize/dequantize model, not encoded-integer or RTL",
            "logical storage only; physical allocation and service rate are NOT_RUN",
            "post-route timing, power, energy, and board parity are NOT_RUN or BLOCKED_EXTERNAL",
            "closed-loop Qwen quality is BLOCKED_EXTERNAL",
        ],
    }


def _write_markdown(result: dict[str, object]) -> None:
    lines = [
        "# E2M0 Fold-Residual Evidence Summary",
        "",
        f"Status: `{result['status']}`",
        f"Candidate software stability: `{result['candidate_software_stability']}`",
        f"Selected-method hardware Pareto: `{result['selected_method_hardware_pareto']}`",
        f"Logical state bytes: `{result['logical_state_bytes']}`",
        (
            "Logical reduction versus uniform MXFP8: "
            f"`{float(result['logical_reduction_vs_uniform_mxfp8_percent']):.6f}%`"
        ),
        "",
        "| Gate | Runs | Tokens/run | Minimum checkpoint cosine | Maximum final state rel L2 | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for gate, item in dict(result["matrices"]).items():
        lines.append(
            f"| {gate} | {item['runs']} | {item['tokens_per_run']} | "
            f"{float(item['minimum_checkpoint_output_cosine']):.6f} | "
            f"{float(item['maximum_final_state_relative_l2']):.6f} | {item['status']} |"
        )
    lines.extend(
        [
            "",
            "The software result does not establish encoded arithmetic parity, physical fit, latency, energy, board behavior, or closed-loop model quality.",
            "",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    result = verify_all()
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_markdown(result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "runs": result["run_count"],
                "failures": len(result["failures"]),
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

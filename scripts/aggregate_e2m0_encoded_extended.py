"""Aggregate preregistered 8K corrected-candidate development traces."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRATION = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "e2m0_encoded_preregistration.json"
)
DEFAULT_INPUT_DIR = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "e2m0_encoded"
    / "extended_development"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _stem(trace_family: str, seed: int, mode: str, tokens: int) -> str:
    return f"{trace_family}_{seed:08x}_{mode}_{tokens}"


def _status(run_status: str, replay_status: str) -> str:
    if "FAIL" in (run_status, replay_status):
        return "FAIL"
    if run_status == replay_status == "PASS":
        return "PASS"
    return "NOT_RUN"


def aggregate(
    *,
    root: Path = ROOT,
    registration_path: Path = DEFAULT_REGISTRATION,
    input_dir: Path = DEFAULT_INPUT_DIR,
) -> dict[str, object]:
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    gate = registration["extended_development_gate"]
    failures: list[str] = []

    if registration.get("registration_status") != "PASS":
        failures.append("registration status is not PASS")
    if gate.get("status") != "NOT_RUN":
        failures.append("frozen extended-development status was edited")
    for relative, expected in registration["frozen_source_sha256"].items():
        path = root / relative
        if not path.is_file() or _sha256(path) != expected:
            failures.append(f"frozen source hash mismatch: {relative}")

    seed = int(gate["seed"])
    modes = list(gate["initial_state_modes"])
    tokens = int(gate["tokens"])
    checkpoints = tuple(int(value) for value in gate["checkpoints"])
    trace_family = str(gate["trace_family"])
    records: list[dict[str, object]] = []
    manifest_hashes: dict[str, str] = {}
    verification_hashes: dict[str, str] = {}
    missing_runs: list[str] = []
    missing_replays: list[str] = []

    for mode in modes:
        stem = _stem(trace_family, seed, mode, tokens)
        manifest_path = input_dir / f"{stem}_manifest.json"
        token_path = input_dir / f"{stem}_tokens.csv"
        checkpoint_path = input_dir / f"{stem}_checkpoints.csv"
        verification_path = input_dir / f"{stem}_verification.json"
        if not all(path.is_file() for path in (manifest_path, token_path, checkpoint_path)):
            missing_runs.append(stem)
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        configuration = manifest.get("configuration", {})
        declared_gate_pass = bool(manifest.get("gate", {}).get("gate_pass"))
        quality_status = "PASS" if declared_gate_pass else "FAIL"
        identity_ok = (
            manifest.get("status") == quality_status
            and manifest.get("initial_state_mode") == mode
            and int(configuration.get("seed", -1)) == seed
            and configuration.get("split") == "extended_development"
            and configuration.get("trace_family") == trace_family
            and int(configuration.get("tokens", -1)) == tokens
            and tuple(configuration.get("checkpoints", [])) == checkpoints
            and manifest.get("variant") == registration["candidate_name"]
        )
        if not identity_ok:
            failures.append(f"manifest identity or declared gate mismatch: {stem}")

        for relative, expected in manifest.get("outputs", {}).items():
            output_path = root / relative
            if not output_path.is_file() or _sha256(output_path) != expected:
                failures.append(f"manifest output hash mismatch: {relative}")

        token_rows = _read_rows(token_path)
        checkpoint_rows = _read_rows(checkpoint_path)
        candidate_rows = [row for row in token_rows if row["variant"] != "fp32"]
        candidate_checkpoints = [
            row for row in checkpoint_rows if row["variant"] != "fp32"
        ]
        final_rows = [
            row for row in candidate_rows if int(row["token_index"]) == tokens
        ]
        if len(candidate_rows) != tokens or len(final_rows) != 1:
            failures.append(f"candidate token sequence mismatch: {stem}")
            continue
        if tuple(int(row["token_index"]) for row in candidate_checkpoints) != checkpoints:
            failures.append(f"candidate checkpoint sequence mismatch: {stem}")
            continue

        recomputed = False
        replay_status = "NOT_RUN"
        verification_relative = None
        verification_sha256 = None
        if verification_path.is_file():
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
            verification_relative = verification_path.relative_to(root).as_posix()
            verification_sha256 = _sha256(verification_path)
            verification_hashes[verification_relative] = verification_sha256
            replay_ok = (
                verification.get("status") == "PASS"
                and verification.get("candidate_gate") == quality_status
                and verification.get("failures") == []
                and verification.get("manifest_sha256") == _sha256(manifest_path)
            )
            if not replay_ok:
                replay_status = "FAIL"
                failures.append(f"independent verification mismatch: {stem}")
            elif bool(verification.get("recomputed")):
                recomputed = True
                replay_status = "PASS"
            else:
                missing_replays.append(stem)
        else:
            missing_replays.append(stem)

        last = final_rows[0]
        manifest_relative = manifest_path.relative_to(root).as_posix()
        manifest_sha256 = _sha256(manifest_path)
        manifest_hashes[manifest_relative] = manifest_sha256
        records.append(
            {
                "seed": seed,
                "seed_hex": f"0x{seed:08X}",
                "initial_state_mode": mode,
                "run_status": quality_status if identity_ok else "FAIL",
                "artifact_integrity_status": "PASS" if identity_ok else "FAIL",
                "quality_gate_status": quality_status,
                "replay_status": replay_status,
                "recomputed": recomputed,
                "minimum_checkpoint_output_cosine": min(
                    float(row["output_cosine_fp32"]) for row in candidate_checkpoints
                ),
                "final_output_cosine": float(last["output_cosine_fp32"]),
                "final_state_relative_l2": float(last["state_rel_l2"]),
                "minimum_all_token_output_cosine": min(
                    float(row["output_cosine_fp32"]) for row in candidate_rows
                ),
                "maximum_all_token_state_relative_l2": max(
                    float(row["state_rel_l2"]) for row in candidate_rows
                ),
                "maximum_all_token_state_abs_error": max(
                    float(row["state_max_abs"]) for row in candidate_rows
                ),
                "element_saturations": int(last["cumulative_element_saturations"]),
                "accumulator_saturations": int(
                    last["cumulative_accumulator_saturations"]
                ),
                "scale_clamps": int(last["cumulative_scale_clamps"]),
                "alignment_underflows": int(
                    last["cumulative_alignment_underflows"]
                ),
                "e2m0_residual_clips": int(
                    last["cumulative_e2m0_residual_clips"]
                ),
                "folds": int(last["folds"]),
                "logical_state_bytes": int(last["logical_state_bytes"]),
                "input_stream_sha256": manifest["input_stream_sha256"],
                "manifest": manifest_relative,
                "manifest_sha256": manifest_sha256,
                "verification": verification_relative,
                "verification_sha256": verification_sha256,
            }
        )

    expected_runs = len(modes)
    if missing_runs:
        run_status = "NOT_RUN"
    elif failures or len(records) != expected_runs or any(
        record["artifact_integrity_status"] != "PASS" for record in records
    ):
        run_status = "FAIL"
    elif any(record["quality_gate_status"] == "FAIL" for record in records):
        run_status = "FAIL"
    else:
        run_status = "PASS"

    replay_values = [str(record["replay_status"]) for record in records]
    if "FAIL" in replay_values:
        replay_status = "FAIL"
    elif len(records) == expected_runs and all(value == "PASS" for value in replay_values):
        replay_status = "PASS"
    else:
        replay_status = "NOT_RUN"

    result: dict[str, object] = {
        "schema": 1,
        "status": _status(run_status, replay_status),
        "extended_run_gate": run_status,
        "full_deterministic_recompute": replay_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registration": registration_path.relative_to(root).as_posix(),
        "registration_sha256": _sha256(registration_path),
        "candidate": registration["candidate_name"],
        "tokens": tokens,
        "checkpoints": list(checkpoints),
        "run_count": len(records),
        "expected_run_count": expected_runs,
        "recomputed_run_count": sum(bool(record["recomputed"]) for record in records),
        "minimum_checkpoint_output_cosine": min(
            (record["minimum_checkpoint_output_cosine"] for record in records),
            default=None,
        ),
        "maximum_final_state_relative_l2": max(
            (record["final_state_relative_l2"] for record in records), default=None
        ),
        "minimum_all_token_output_cosine": min(
            (record["minimum_all_token_output_cosine"] for record in records),
            default=None,
        ),
        "maximum_all_token_state_relative_l2": max(
            (record["maximum_all_token_state_relative_l2"] for record in records),
            default=None,
        ),
        "maximum_all_token_state_abs_error": max(
            (record["maximum_all_token_state_abs_error"] for record in records),
            default=None,
        ),
        "total_element_saturations": sum(
            int(record["element_saturations"]) for record in records
        ),
        "total_accumulator_saturations": sum(
            int(record["accumulator_saturations"]) for record in records
        ),
        "total_scale_clamps": sum(int(record["scale_clamps"]) for record in records),
        "total_alignment_underflows": sum(
            int(record["alignment_underflows"]) for record in records
        ),
        "total_e2m0_residual_clips": sum(
            int(record["e2m0_residual_clips"]) for record in records
        ),
        "total_folds": sum(int(record["folds"]) for record in records),
        "records": records,
        "manifest_sha256": manifest_hashes,
        "verification_sha256": verification_hashes,
        "missing_runs": missing_runs,
        "missing_replays": sorted(set(missing_replays)),
        "failures": failures,
        "limitations": [
            "development-only layer-level synthetic high-retention traces",
            "PASS requires full deterministic recomputation of both 8192-token runs",
            "closed-loop model, RTL, physical fit, post-route, and board evidence remain separate gates",
        ],
    }
    return result


def write_outputs(result: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "extended_summary.csv"
    fields = list(result["records"][0]) if result["records"] else ["run_status"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result["records"])
    result["summary_csv"] = csv_path.relative_to(ROOT).as_posix()
    result["summary_csv_sha256"] = _sha256(csv_path)
    (output_dir / "extended_summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Corrected Candidate Extended Development Summary",
        "",
        f"8K run gate: `{result['extended_run_gate']}`",
        f"Full deterministic recomputation: `{result['full_deterministic_recompute']}`",
        f"Aggregate status: `{result['status']}`",
        f"Total alignment underflows: {result['total_alignment_underflows']}",
        f"Total deliberate E2M0 residual clips: {result['total_e2m0_residual_clips']}",
        "",
        "| Initial state | Min checkpoint cosine | Final state rel L2 | Min all-token cosine | Max all-token state rel L2 | Replay |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for record in result["records"]:
        lines.append(
            f"| {record['initial_state_mode']} | "
            f"{record['minimum_checkpoint_output_cosine']:.6f} | "
            f"{record['final_state_relative_l2']:.6f} | "
            f"{record['minimum_all_token_output_cosine']:.6f} | "
            f"{record['maximum_all_token_state_relative_l2']:.6f} | "
            f"{record['replay_status']} |"
        )
    (output_dir / "extended_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_INPUT_DIR)
    args = parser.parse_args(argv)
    registration = _resolve(args.registration)
    input_dir = _resolve(args.input_dir)
    output_dir = _resolve(args.output_dir)
    result = aggregate(
        root=ROOT, registration_path=registration, input_dir=input_dir
    )
    write_outputs(result, output_dir)
    print(
        json.dumps(
            {
                "status": result["status"],
                "run_gate": result["extended_run_gate"],
                "full_recompute": result["full_deterministic_recompute"],
                "runs": result["run_count"],
                "failures": len(result["failures"]),
            },
            sort_keys=True,
        )
    )
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

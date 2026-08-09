"""Independently verify preregistered residual-stack MXFP4 evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "mxfp4_rs2_candidate_preregistration.json"
)
EVIDENCE = ROOT / "reports" / "benchmark" / "corrected" / "mxfp4_rs2_candidate"
OUTPUT_JSON = EVIDENCE / "mxfp4_rs2_candidate_summary.json"
OUTPUT_CSV = EVIDENCE / "mxfp4_rs2_candidate_summary.csv"
OUTPUT_MD = EVIDENCE / "mxfp4_rs2_candidate_summary.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _specs(registration: dict[str, object]) -> list[dict[str, object]]:
    held_out = registration["held_out_gate"]
    extended = registration["extended_development_gate"]
    specs: list[dict[str, object]] = []
    for seed in held_out["seeds"]:
        for initial_state in held_out["initial_state_modes"]:
            specs.append(
                {
                    "gate": "held_out",
                    "split": held_out["split"],
                    "seed": int(seed),
                    "initial_state": initial_state,
                    "tokens": int(held_out["tokens"]),
                    "checkpoints": tuple(int(value) for value in held_out["checkpoints"]),
                    "stem": f"seed_{int(seed):08x}_{initial_state}",
                }
            )
    for initial_state in extended["initial_state_modes"]:
        specs.append(
            {
                "gate": "extended_development",
                "split": "development",
                "seed": int(extended["seed"]),
                "initial_state": initial_state,
                "tokens": int(extended["tokens"]),
                "checkpoints": tuple(
                    int(value) for value in extended["checkpoints"]
                ),
                "stem": f"seed_{int(extended['seed']):08x}_{initial_state}",
            }
        )
    return specs


def _verify_run(
    spec: dict[str, object],
    registration: dict[str, object],
) -> dict[str, object]:
    directory = EVIDENCE / str(spec["gate"])
    stem = str(spec["stem"])
    paths = {
        "tokens": directory / f"{stem}_tokens.csv",
        "checkpoints": directory / f"{stem}_checkpoints.csv",
        "manifest": directory / f"{stem}_manifest.json",
        "report": directory / f"{stem}.md",
    }
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    configuration = manifest["configuration"]
    expected = registration["controlled_configuration"]
    if (
        manifest["log_precision"] != "mxfp4_rs2"
        or manifest["activation_stack_depth"] != expected["activation_stack_depth"]
        or manifest["base_stack_depth"] != expected["base_stack_depth"]
        or manifest["capacities"] != [expected["log_capacity"]]
        or manifest["initial_state_mode"] != spec["initial_state"]
        or configuration["tokens"] != spec["tokens"]
        or configuration["seed"] != spec["seed"]
        or configuration["trace_family"] != "high_retention"
    ):
        raise ValueError(f"run configuration mismatch: {stem}")

    for relative, expected_hash in manifest["source_hashes"].items():
        source = ROOT / relative
        if not source.is_file() or _sha256(source) != str(expected_hash).upper():
            raise ValueError(f"run source hash mismatch: {relative}")
    for relative, expected_hash in manifest["outputs"].items():
        output = ROOT / relative
        if not output.is_file() or _sha256(output) != str(expected_hash).upper():
            raise ValueError(f"run output hash mismatch: {relative}")

    token_rows = _rows(paths["tokens"])
    checkpoint_rows = _rows(paths["checkpoints"])
    candidate = registration["candidate_name"]
    candidate_tokens = [row for row in token_rows if row["variant"] == candidate]
    candidate_checkpoints = [
        row for row in checkpoint_rows if row["variant"] == candidate
    ]
    if len(token_rows) != 2 * int(spec["tokens"]) or len(candidate_tokens) != int(
        spec["tokens"]
    ):
        raise ValueError(f"token row count mismatch: {stem}")
    if [int(row["token_index"]) for row in candidate_tokens] != list(
        range(1, int(spec["tokens"]) + 1)
    ):
        raise ValueError(f"token ordering mismatch: {stem}")
    if [int(row["token_index"]) for row in candidate_checkpoints] != list(
        spec["checkpoints"]
    ):
        raise ValueError(f"checkpoint ordering mismatch: {stem}")
    for row in candidate_tokens:
        token = int(row["token_index"])
        if int(row["folds"]) != token // 2 or int(row["live_entries"]) != token % 2:
            raise ValueError(f"fold schedule mismatch: {stem}:{token}")
        if int(row["dropped_entries"]) != 0:
            raise ValueError(f"dropped log entry: {stem}:{token}")
        for field in ("output_cosine_fp32", "state_rel_l2", "state_max_abs"):
            if not math.isfinite(float(row[field])):
                raise ValueError(f"nonfinite metric: {stem}:{token}:{field}")

    gate = registration["quality_gate"]
    minimum_all_cosine = min(
        float(row["output_cosine_fp32"]) for row in candidate_tokens
    )
    maximum_all_state = max(float(row["state_rel_l2"]) for row in candidate_tokens)
    minimum_checkpoint_cosine = min(
        float(row["output_cosine_fp32"]) for row in candidate_checkpoints
    )
    final = candidate_checkpoints[-1]
    final_state = float(final["state_rel_l2"])
    status = (
        "PASS"
        if minimum_all_cosine >= gate["minimum_all_token_output_cosine"]
        and maximum_all_state <= gate["maximum_all_token_state_relative_l2"]
        and minimum_checkpoint_cosine
        >= gate["minimum_checkpoint_output_cosine"]
        and final_state <= gate["maximum_final_state_relative_l2"]
        else "FAIL"
    )
    return {
        "gate": spec["gate"],
        "split": spec["split"],
        "seed": spec["seed"],
        "initial_state_mode": spec["initial_state"],
        "tokens": spec["tokens"],
        "status": status,
        "minimum_all_token_output_cosine": minimum_all_cosine,
        "maximum_all_token_state_relative_l2": maximum_all_state,
        "minimum_checkpoint_output_cosine": minimum_checkpoint_cosine,
        "final_output_cosine": float(final["output_cosine_fp32"]),
        "final_state_relative_l2": final_state,
        "maximum_state_absolute_error": max(
            float(row["state_max_abs"]) for row in candidate_tokens
        ),
        "folds": int(final["folds"]),
        "dropped_entries": 0,
        "logical_state_bytes": int(final["logical_state_bytes"]),
        "input_stream_sha256": manifest["input_stream_sha256"].upper(),
        "evidence": {_relative(path): _sha256(path) for path in paths.values()},
    }


def aggregate() -> dict[str, object]:
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    if (
        registration["registration_status"] != "PASS"
        or registration["candidate_evidence_status"] != "NOT_RUN"
    ):
        raise ValueError("candidate registration is not frozen")
    for relative, expected in registration["frozen_source_sha256"].items():
        if _sha256(ROOT / relative) != str(expected).upper():
            raise ValueError(f"frozen source mismatch: {relative}")

    runs = [_verify_run(spec, registration) for spec in _specs(registration)]
    gate_results: dict[str, dict[str, object]] = {}
    for gate_name in ("held_out", "extended_development"):
        gate_runs = [run for run in runs if run["gate"] == gate_name]
        gate_results[gate_name] = {
            "status": "PASS" if all(run["status"] == "PASS" for run in gate_runs) else "FAIL",
            "run_count": len(gate_runs),
            "minimum_all_token_output_cosine": min(
                run["minimum_all_token_output_cosine"] for run in gate_runs
            ),
            "maximum_all_token_state_relative_l2": max(
                run["maximum_all_token_state_relative_l2"] for run in gate_runs
            ),
            "minimum_checkpoint_output_cosine": min(
                run["minimum_checkpoint_output_cosine"] for run in gate_runs
            ),
            "maximum_final_state_relative_l2": max(
                run["final_state_relative_l2"] for run in gate_runs
            ),
        }
    status = (
        "PASS"
        if all(result["status"] == "PASS" for result in gate_results.values())
        else "FAIL"
    )
    payload: dict[str, object] = {
        "schema": 1,
        "status": status,
        "candidate_evidence_status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_name": registration["candidate_name"],
        "registration": _relative(REGISTRATION),
        "registration_sha256": _sha256(REGISTRATION),
        "quality_gate": registration["quality_gate"],
        "gate_results": gate_results,
        "runs": runs,
        "limitations": [
            "synthetic layer-level evidence",
            "floating Q/DQ until encoded-integer and HLS parity are established",
            "not closed-loop model quality or board energy evidence",
        ],
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    fields = [
        "gate",
        "split",
        "seed",
        "initial_state_mode",
        "tokens",
        "status",
        "minimum_all_token_output_cosine",
        "maximum_all_token_state_relative_l2",
        "minimum_checkpoint_output_cosine",
        "final_output_cosine",
        "final_state_relative_l2",
        "maximum_state_absolute_error",
        "folds",
        "dropped_entries",
        "logical_state_bytes",
        "input_stream_sha256",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(runs)
    payload["summary_csv"] = _relative(OUTPUT_CSV)
    payload["summary_csv_sha256"] = _sha256(OUTPUT_CSV)
    OUTPUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Residual-Stack MXFP4 Candidate Evidence",
        "",
        f"Status: `{status}`",
        f"Candidate: `{registration['candidate_name']}`",
        "",
        "| Gate | Runs | Min all-token cosine | Max all-token state rel. L2 | Max final state rel. L2 |",
        "|---|---:|---:|---:|---:|",
    ]
    for gate_name, result in gate_results.items():
        lines.append(
            f"| {gate_name} | {result['run_count']} | "
            f"{result['minimum_all_token_output_cosine']:.6f} | "
            f"{result['maximum_all_token_state_relative_l2']:.6f} | "
            f"{result['maximum_final_state_relative_l2']:.6f} |"
        )
    lines.extend(
        [
            "",
            "This is synthetic layer-level floating Q/DQ evidence. Encoded-integer, RTL, routed, board-energy, and closed-loop model claims require separate evidence.",
            "",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def main() -> int:
    payload = aggregate()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "held_out": payload["gate_results"]["held_out"]["status"],
                "extended": payload["gate_results"]["extended_development"]["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

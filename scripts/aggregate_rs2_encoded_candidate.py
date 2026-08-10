"""Verify and aggregate preregistered encoded RS2/R3 stability evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from scripts.register_rs2_encoded_candidate import OUTPUT as REGISTRATION
from scripts.rs2_encoded_stability import ROOT, VARIANT
from scripts.verify_rs2_encoded_stability import verify_manifest


EVIDENCE = ROOT / "reports" / "benchmark" / "corrected" / "rs2_encoded"
OUTPUT_JSON = EVIDENCE / "rs2_encoded_candidate_summary.json"
OUTPUT_CSV = EVIDENCE / "rs2_encoded_candidate_summary.csv"
OUTPUT_MD = EVIDENCE / "rs2_encoded_candidate_summary.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _specs(registration: dict[str, object]) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for gate_name, directory_name in (
        ("held_out", "held_out"),
        ("extended_development", "extended_development"),
    ):
        gate = registration[f"{gate_name}_gate"]
        seeds = gate.get("seeds", [gate.get("seed")])
        for seed in seeds:
            for initial_state in gate["initial_state_modes"]:
                tokens = int(gate["tokens"])
                specs.append(
                    {
                        "gate": gate_name,
                        "directory": directory_name,
                        "split": gate.get("split", "development"),
                        "seed": int(seed),
                        "initial_state": str(initial_state),
                        "tokens": tokens,
                        "checkpoints": tuple(int(v) for v in gate["checkpoints"]),
                        "stem": (
                            f"high_retention_{int(seed):08x}_{initial_state}_{tokens}"
                        ),
                    }
                )
    return specs


def _manifest_paths(spec: dict[str, object]) -> tuple[Path, Path, Path]:
    directory = EVIDENCE / str(spec["directory"])
    stem = str(spec["stem"])
    return (
        directory / f"{stem}_manifest.json",
        directory / f"{stem}_tokens.csv",
        directory / f"{stem}_checkpoints.csv",
    )


def _verify_run(
    spec: dict[str, object], registration: dict[str, object]
) -> dict[str, object] | None:
    manifest_path, token_path, checkpoint_path = _manifest_paths(spec)
    if not any(path.exists() for path in (manifest_path, token_path, checkpoint_path)):
        return None
    if not all(path.is_file() for path in (manifest_path, token_path, checkpoint_path)):
        raise FileNotFoundError(f"incomplete evidence set for {spec['stem']}")
    verification = verify_manifest(manifest_path, recompute=False)
    if verification["status"] != "PASS" or verification["candidate_gate"] != "PASS":
        raise ValueError(f"manifest verification failed: {spec['stem']}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = manifest["configuration"]
    expected = registration["controlled_configuration"]
    if (
        manifest["variant"] != registration["candidate_name"]
        or manifest["variant"] != VARIANT
        or manifest["initial_state_mode"] != spec["initial_state"]
        or config["tokens"] != spec["tokens"]
        or config["seed"] != spec["seed"]
        or config["split"] != spec["split"]
        or config["trace_family"] != "high_retention"
        or config["num_value_heads"] != expected["num_value_heads"]
        or config["num_qk_heads"] != expected["num_qk_heads"]
        or config["key_dim"] != expected["key_dim"]
        or config["value_dim"] != expected["value_dim"]
    ):
        raise ValueError(f"run configuration mismatch: {spec['stem']}")

    token_rows = _rows(token_path)
    checkpoint_rows = _rows(checkpoint_path)
    candidate_tokens = [row for row in token_rows if row["variant"] == VARIANT]
    candidate_checkpoints = [
        row for row in checkpoint_rows if row["variant"] == VARIANT
    ]
    if len(candidate_tokens) != int(spec["tokens"]):
        raise ValueError(f"candidate row count mismatch: {spec['stem']}")
    if [int(row["token_index"]) for row in candidate_checkpoints] != list(
        spec["checkpoints"]
    ):
        raise ValueError(f"checkpoint ordering mismatch: {spec['stem']}")
    for row in candidate_tokens:
        for field in ("output_cosine_fp32", "state_rel_l2", "state_max_abs"):
            if not math.isfinite(float(row[field])):
                raise ValueError(f"nonfinite metric: {spec['stem']}:{field}")

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
    counters = {
        name: int(final[f"cumulative_{name}"])
        for name in (
            "element_saturations",
            "accumulator_saturations",
            "scale_clamps",
            "alignment_underflows",
            "state_scale_changes",
        )
    }
    status = (
        "PASS"
        if minimum_all_cosine >= gate["minimum_all_token_output_cosine"]
        and maximum_all_state <= gate["maximum_all_token_state_relative_l2"]
        and minimum_checkpoint_cosine >= gate["minimum_checkpoint_output_cosine"]
        and final_state <= gate["maximum_final_state_relative_l2"]
        and counters["element_saturations"] == 0
        and counters["accumulator_saturations"] == 0
        and counters["scale_clamps"] == 0
        else "FAIL"
    )
    return {
        "gate": spec["gate"],
        "split": spec["split"],
        "seed": spec["seed"],
        "seed_hex": f"0x{int(spec['seed']):08X}",
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
        "logical_state_bytes": int(final["logical_state_bytes"]),
        **{f"cumulative_{name}": value for name, value in counters.items()},
        "input_stream_sha256": manifest["input_stream_sha256"].upper(),
        "evidence": {
            _relative(path): _sha256(path)
            for path in (manifest_path, token_path, checkpoint_path)
        },
    }


def aggregate(
    *, require_extended: bool = False, write_outputs: bool = True
) -> dict[str, object]:
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    if (
        registration["registration_status"] != "PASS"
        or registration["candidate_evidence_status"] != "NOT_RUN"
    ):
        raise ValueError("candidate registration is not frozen")
    for relative, expected_hash in registration["frozen_source_sha256"].items():
        source = ROOT / relative
        if not source.is_file() or _sha256(source) != str(expected_hash).upper():
            raise ValueError(f"frozen source mismatch: {relative}")

    verified = [
        _verify_run(spec, registration) for spec in _specs(registration)
    ]
    runs = [run for run in verified if run is not None]
    gate_results: dict[str, dict[str, object]] = {}
    expected_counts = {"held_out": 6, "extended_development": 2}
    for gate_name, expected_count in expected_counts.items():
        gate_runs = [run for run in runs if run["gate"] == gate_name]
        if not gate_runs:
            gate_results[gate_name] = {
                "status": "NOT_RUN",
                "run_count": 0,
                "expected_run_count": expected_count,
            }
            continue
        complete = len(gate_runs) == expected_count
        gate_results[gate_name] = {
            "status": (
                "PASS"
                if complete and all(run["status"] == "PASS" for run in gate_runs)
                else "FAIL" if complete else "PARTIAL"
            ),
            "run_count": len(gate_runs),
            "expected_run_count": expected_count,
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
            "maximum_state_absolute_error": max(
                run["maximum_state_absolute_error"] for run in gate_runs
            ),
            "cumulative_element_saturations": sum(
                run["cumulative_element_saturations"] for run in gate_runs
            ),
            "cumulative_accumulator_saturations": sum(
                run["cumulative_accumulator_saturations"] for run in gate_runs
            ),
            "cumulative_scale_clamps": sum(
                run["cumulative_scale_clamps"] for run in gate_runs
            ),
        }
    if require_extended and gate_results["extended_development"]["status"] != "PASS":
        raise RuntimeError("extended-development evidence is incomplete")
    statuses = {result["status"] for result in gate_results.values()}
    status = "PASS" if statuses == {"PASS"} else "FAIL" if "FAIL" in statuses else "PARTIAL"
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
            "synthetic layer-level encoded-integer evidence",
            "not closed-loop model quality or board energy evidence",
        ],
    }
    fields = [
        "gate",
        "split",
        "seed",
        "seed_hex",
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
        "logical_state_bytes",
        "cumulative_element_saturations",
        "cumulative_accumulator_saturations",
        "cumulative_scale_clamps",
        "cumulative_alignment_underflows",
        "cumulative_state_scale_changes",
        "input_stream_sha256",
    ]
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(runs)
    csv_bytes = csv_buffer.getvalue().encode("utf-8")
    payload["summary_csv"] = _relative(OUTPUT_CSV)
    payload["summary_csv_sha256"] = hashlib.sha256(csv_bytes).hexdigest().upper()
    lines = [
        "# Encoded RS2/R3 Candidate Evidence",
        "",
        f"Status: `{status}`",
        f"Candidate: `{registration['candidate_name']}`",
        "",
        "| Gate | Status | Runs | Min all-token cosine | Max all-token state rel. L2 | Max final state rel. L2 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for gate_name, result in gate_results.items():
        if result["run_count"]:
            lines.append(
                f"| {gate_name} | {result['status']} | {result['run_count']} | "
                f"{result['minimum_all_token_output_cosine']:.6f} | "
                f"{result['maximum_all_token_state_relative_l2']:.6f} | "
                f"{result['maximum_final_state_relative_l2']:.6f} |"
            )
        else:
            lines.append(f"| {gate_name} | NOT_RUN | 0 | - | - | - |")
    lines.extend(
        [
            "",
            "This is synthetic layer-level encoded-integer evidence. Closed-loop model quality and board energy require separate evidence.",
            "",
        ]
    )
    if write_outputs:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        OUTPUT_CSV.write_bytes(csv_bytes)
        OUTPUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-extended", action="store_true")
    args = parser.parse_args(argv)
    payload = aggregate(require_extended=args.require_extended)
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
    return 0 if payload["gate_results"]["held_out"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Aggregate the preregistered encoded E2M0 held-out matrix."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.long_sequence_stability import TraceConfiguration
from scripts.write_log_stability import _trace_initial_state, _trace_inputs


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "e2m0_encoded_preregistration.json"
)
HELD_OUT_DIR = (
    ROOT / "reports" / "benchmark" / "corrected" / "e2m0_encoded" / "held_out"
)
SUMMARY_CSV = HELD_OUT_DIR / "held_out_summary.csv"
SUMMARY_JSON = HELD_OUT_DIR / "held_out_summary.json"
SUMMARY_MD = HELD_OUT_DIR / "held_out_summary.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _stem(seed: int, mode: str, tokens: int) -> str:
    return f"high_retention_{seed:08x}_{mode}_{tokens}"


def _separated_input_hashes(
    configuration: dict[str, object], initial_state_mode: str
) -> dict[str, str]:
    config = TraceConfiguration(
        tokens=int(configuration["tokens"]),
        checkpoints=tuple(int(value) for value in configuration["checkpoints"]),
        seed=int(configuration["seed"]),
        split=str(configuration["split"]),
        trace_family=str(configuration["trace_family"]),
        num_value_heads=int(configuration["num_value_heads"]),
        num_qk_heads=int(configuration["num_qk_heads"]),
        key_dim=int(configuration["key_dim"]),
        value_dim=int(configuration["value_dim"]),
        activation_block_size=int(configuration["activation_block_size"]),
        state_block_size=int(configuration["state_block_size"]),
    )
    initial = np.ascontiguousarray(_trace_initial_state(config, initial_state_mode))
    initial_digest = hashlib.sha256(initial.tobytes())
    token_digest = hashlib.sha256()
    combined_digest = hashlib.sha256(initial.tobytes())
    for token_zero_based in range(config.tokens):
        for array in _trace_inputs(config, token_zero_based):
            payload = np.ascontiguousarray(array).tobytes()
            token_digest.update(payload)
            combined_digest.update(payload)
    return {
        "initial_state_sha256": initial_digest.hexdigest().upper(),
        "token_stream_sha256": token_digest.hexdigest().upper(),
        "combined_input_sha256": combined_digest.hexdigest().upper(),
    }


def aggregate() -> dict[str, object]:
    failures: list[str] = []
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    if registration.get("registration_status") != "PASS":
        failures.append("registration status is not PASS")
    if registration.get("candidate_evidence_status") != "NOT_RUN":
        failures.append("registration was edited after held-out execution")
    held_out = registration["held_out_gate"]
    if held_out.get("status") != "NOT_RUN":
        failures.append("frozen held-out registration status was edited")
    for relative, expected in registration["frozen_source_sha256"].items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            failures.append(f"frozen source hash mismatch: {relative}")
    for category in ("verified_manifests", "verification_sha256"):
        for relative, expected in registration["development_gate"][category].items():
            path = ROOT / relative
            if not path.is_file() or _sha256(path) != expected:
                failures.append(f"development evidence hash mismatch: {relative}")

    seeds = [int(value) for value in held_out["seeds"]]
    modes = list(held_out["initial_state_modes"])
    tokens = int(held_out["tokens"])
    if registration["development_gate"]["seed"] in seeds:
        failures.append("development seed overlaps held-out seeds")
    records: list[dict[str, object]] = []
    all_input_hashes: list[str] = []
    token_hashes_by_seed: dict[int, set[str]] = {seed: set() for seed in seeds}
    recomputed_count = 0
    manifest_hashes: dict[str, str] = {}
    verification_hashes: dict[str, str] = {}

    for seed in seeds:
        for mode in modes:
            stem = _stem(seed, mode, tokens)
            manifest_path = HELD_OUT_DIR / f"{stem}_manifest.json"
            verification_path = HELD_OUT_DIR / f"{stem}_verification.json"
            token_path = HELD_OUT_DIR / f"{stem}_tokens.csv"
            checkpoint_path = HELD_OUT_DIR / f"{stem}_checkpoints.csv"
            required = (manifest_path, verification_path, token_path, checkpoint_path)
            if any(not path.is_file() for path in required):
                failures.append(f"missing held-out artifact: {stem}")
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
            manifest_relative = manifest_path.relative_to(ROOT).as_posix()
            verification_relative = verification_path.relative_to(ROOT).as_posix()
            manifest_hashes[manifest_relative] = _sha256(manifest_path)
            verification_hashes[verification_relative] = _sha256(verification_path)
            configuration = manifest.get("configuration", {})
            expected_identity = (
                manifest.get("status") == "PASS"
                and manifest.get("initial_state_mode") == mode
                and int(configuration.get("seed", -1)) == seed
                and configuration.get("split") == held_out["split"]
                and configuration.get("trace_family") == held_out["trace_family"]
                and int(configuration.get("tokens", -1)) == tokens
                and tuple(configuration.get("checkpoints", []))
                == tuple(held_out["checkpoints"])
            )
            if not expected_identity:
                failures.append(f"manifest identity/gate mismatch: {stem}")
            if (
                verification.get("status") != "PASS"
                or verification.get("candidate_gate") != "PASS"
                or verification.get("failures") != []
                or verification.get("manifest_sha256") != _sha256(manifest_path)
            ):
                failures.append(f"verification mismatch: {stem}")
            recomputed = bool(verification.get("recomputed"))
            recomputed_count += int(recomputed)
            input_hash = str(manifest.get("input_stream_sha256", ""))
            all_input_hashes.append(input_hash)
            separated_hashes = _separated_input_hashes(configuration, mode)
            if separated_hashes["combined_input_sha256"] != input_hash.upper():
                failures.append(f"reconstructed input hash mismatch: {stem}")
            token_hashes_by_seed[seed].add(separated_hashes["token_stream_sha256"])
            token_rows = _read_rows(token_path)
            checkpoint_rows = _read_rows(checkpoint_path)
            candidate_rows = [row for row in token_rows if row["variant"] != "fp32"]
            candidate_checkpoints = [
                row for row in checkpoint_rows if row["variant"] != "fp32"
            ]
            final = [row for row in candidate_rows if int(row["token_index"]) == tokens]
            if len(candidate_rows) != tokens or len(final) != 1:
                failures.append(f"candidate row sequence mismatch: {stem}")
                continue
            last = final[0]
            records.append(
                {
                    "seed": seed,
                    "seed_hex": f"0x{seed:08X}",
                    "initial_state_mode": mode,
                    "status": "PASS" if expected_identity else "FAIL",
                    "recomputed": recomputed,
                    "minimum_checkpoint_output_cosine": min(
                        float(row["output_cosine_fp32"])
                        for row in candidate_checkpoints
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
                    "input_artifact_sha256": input_hash,
                    "token_stream_sha256": separated_hashes["token_stream_sha256"],
                    "initial_state_sha256": separated_hashes["initial_state_sha256"],
                    "manifest": manifest_relative,
                    "manifest_sha256": _sha256(manifest_path),
                    "verification": verification_relative,
                    "verification_sha256": _sha256(verification_path),
                }
            )

    expected_runs = int(held_out["run_count"])
    if len(records) != expected_runs:
        failures.append("held-out run count mismatch")
    if len(all_input_hashes) != len(set(all_input_hashes)):
        failures.append("paired input artifacts are not unique")
    if any(len(hashes) != 1 for hashes in token_hashes_by_seed.values()):
        failures.append("paired initial-state conditions do not share a token stream")
    unique_token_hashes = {next(iter(hashes)) for hashes in token_hashes_by_seed.values() if hashes}
    if len(unique_token_hashes) != len(seeds):
        failures.append("test seed blocks do not produce unique token streams")
    registered_gate = not failures and all(record["status"] == "PASS" for record in records)
    replay_status = "PASS" if recomputed_count == expected_runs else "NOT_RUN"
    return {
        "schema": 1,
        "status": "PASS" if registered_gate and replay_status == "PASS" else "NOT_RUN"
        if registered_gate
        else "FAIL",
        "registered_held_out_gate": "PASS" if registered_gate else "FAIL",
        "full_deterministic_recompute": replay_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registration": REGISTRATION.relative_to(ROOT).as_posix(),
        "registration_sha256": _sha256(REGISTRATION),
        "candidate": registration["candidate_name"],
        "run_count": len(records),
        "seed_block_count": len(seeds),
        "paired_condition_count": len(records),
        "statistical_unit": "seed block; initial-state mode is a paired condition",
        "recomputed_run_count": recomputed_count,
        "logical_state_bytes": 537744,
        "uniform_mxfp8_state_bytes": 540672,
        "bytes_below_uniform_mxfp8": 2928,
        "percent_below_uniform_mxfp8": 100.0 * 2928 / 540672,
        "minimum_registered_checkpoint_output_cosine": min(
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
        "records": records,
        "manifest_sha256": manifest_hashes,
        "verification_sha256": verification_hashes,
        "failures": failures,
        "limitations": [
            "layer-level deterministic synthetic high-retention traces only",
            "three independent token-stream seed blocks are crossed with two paired initial-state conditions",
            "the original local registration was not externally timestamped and omitted part of the execution dependency closure",
            "full deterministic recomputation remains NOT_RUN until every verification records recomputed=true"
            if replay_status != "PASS"
            else "every paired test condition was deterministically recomputed field for field",
            "HLS, RTL, physical allocation, post-route timing, board energy, and closed-loop model quality are NOT_RUN",
            "logical bytes below MXFP8 do not establish physical Pareto advantage",
        ],
    }


def _write_summary_csv(records: list[dict[str, object]]) -> None:
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = list(records[0]) if records else ["status"]
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def _write_markdown(result: dict[str, object]) -> None:
    lines = [
        "# Encoded E2M0 Held-Out Summary",
        "",
        f"Registered held-out gate: `{result['registered_held_out_gate']}`",
        f"Full deterministic recomputation: `{result['full_deterministic_recompute']}`",
        f"Aggregate evidence status: `{result['status']}`",
        f"Statistical unit: `{result['statistical_unit']}` "
        f"({result['seed_block_count']} seed blocks, "
        f"{result['paired_condition_count']} paired conditions)",
        "",
        "| Seed | Initial state | Min checkpoint cosine | Final state rel L2 | Min all-token cosine | Max all-token state rel L2 | Recomputed |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for record in result["records"]:
        lines.append(
            f"| {record['seed_hex']} | {record['initial_state_mode']} | "
            f"{record['minimum_checkpoint_output_cosine']:.6f} | "
            f"{record['final_state_relative_l2']:.6f} | "
            f"{record['minimum_all_token_output_cosine']:.6f} | "
            f"{record['maximum_all_token_state_relative_l2']:.6f} | "
            f"{str(record['recomputed']).upper()} |"
        )
    lines.extend(
        [
            "",
            f"Logical state bytes: `{result['logical_state_bytes']}` "
            f"(`{result['bytes_below_uniform_mxfp8']}` bytes below uniform MXFP8-B32).",
            "",
            "This is encoded software evidence. Hardware Pareto, closed-loop model, and board gates remain `NOT_RUN` or `BLOCKED_EXTERNAL`.",
        ]
    )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    result = aggregate()
    _write_summary_csv(result["records"])
    result["summary_csv"] = SUMMARY_CSV.relative_to(ROOT).as_posix()
    result["summary_csv_sha256"] = _sha256(SUMMARY_CSV)
    SUMMARY_JSON.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_markdown(result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "registered_gate": result["registered_held_out_gate"],
                "full_recompute": result["full_deterministic_recompute"],
                "runs": result["run_count"],
                "failures": len(result["failures"]),
            },
            sort_keys=True,
        )
    )
    return 0 if result["registered_held_out_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

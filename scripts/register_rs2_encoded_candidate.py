"""Freeze the exact encoded RS2/R3 candidate before held-out execution."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.rs2_encoded_stability import (
    CAPACITY,
    OUTPUT_COSINE_MINIMUM,
    ROOT,
    STATE_RELATIVE_L2_MAXIMUM,
    VARIANT,
    logical_encoded_state_bytes,
)
from scripts.long_sequence_stability import TraceConfiguration
from scripts.verify_rs2_encoded_stability import verify_manifest


EVIDENCE = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_encoded"
    / "r3_development"
)
R2_FAILURE = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_encoded"
    / "development"
    / "high_retention_0000fb72_random_1024_manifest.json"
)
OUTPUT = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_encoded_candidate_preregistration.json"
)
DEVELOPMENT_MANIFESTS = {
    mode: EVIDENCE / f"high_retention_0000fb72_{mode}_1024_manifest.json"
    for mode in ("random", "zero")
}
SOURCE_FILES = (
    ROOT / "golden" / "gdn_rs2_encoded.py",
    ROOT / "golden" / "gdn_rs2_encoded_vectorized.py",
    ROOT / "golden" / "gdn_e2m0_encoded.py",
    ROOT / "golden" / "gdn_e2m0_encoded_vectorized.py",
    ROOT / "golden" / "gdn_mxfp4_encoded.py",
    ROOT / "golden" / "gdn_mxfp4_encoded_vectorized.py",
    ROOT / "scripts" / "rs2_encoded_stability.py",
    ROOT / "scripts" / "verify_rs2_encoded_stability.py",
    Path(__file__).resolve(),
)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _csv_path(manifest: dict[str, object], suffix: str) -> Path:
    candidates = [
        ROOT / relative
        for relative in manifest["outputs"]
        if str(relative).endswith(suffix)
    ]
    if len(candidates) != 1:
        raise ValueError(f"manifest must contain one {suffix} output")
    return candidates[0]


def _candidate_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["variant"] == VARIANT]
    if not rows:
        raise ValueError(f"candidate rows are absent from {_relative(path)}")
    return rows


def _development_summary() -> tuple[dict[str, object], TraceConfiguration]:
    summaries: dict[str, object] = {}
    configurations: list[TraceConfiguration] = []
    for initial_state, manifest_path in DEVELOPMENT_MANIFESTS.items():
        verification = verify_manifest(manifest_path, recompute=False)
        if verification["status"] != "PASS" or verification["candidate_gate"] != "PASS":
            raise ValueError(f"development verification failed for {initial_state}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        config = TraceConfiguration(**manifest["configuration"])
        configurations.append(config)
        if (
            config.tokens != 1024
            or config.seed != 0xFB72
            or config.trace_family != "high_retention"
            or manifest["initial_state_mode"] != initial_state
            or manifest["variant"] != VARIANT
        ):
            raise ValueError(f"unexpected development configuration for {initial_state}")
        token_path = _csv_path(manifest, "_tokens.csv")
        checkpoint_path = _csv_path(manifest, "_checkpoints.csv")
        token_rows = _candidate_rows(token_path)
        checkpoint_rows = _candidate_rows(checkpoint_path)
        final_rows = [row for row in checkpoint_rows if int(row["token_index"]) == 1024]
        if len(final_rows) != 1:
            raise ValueError(f"missing final checkpoint for {initial_state}")
        gate_metrics = manifest["gate"]["metrics"]
        summaries[initial_state] = {
            "minimum_all_token_output_cosine": min(
                float(row["output_cosine_fp32"]) for row in token_rows
            ),
            "maximum_all_token_state_relative_l2": max(
                float(row["state_rel_l2"]) for row in token_rows
            ),
            "minimum_checkpoint_output_cosine": min(
                float(row["output_cosine_fp32"]) for row in checkpoint_rows
            ),
            "final_state_relative_l2": float(final_rows[0]["state_rel_l2"]),
            "cumulative_element_saturations": int(
                gate_metrics["cumulative_element_saturations"]
            ),
            "cumulative_accumulator_saturations": int(
                gate_metrics["cumulative_accumulator_saturations"]
            ),
            "cumulative_scale_clamps": int(gate_metrics["cumulative_scale_clamps"]),
            "input_stream_sha256": manifest["input_stream_sha256"].upper(),
            "evidence_sha256": {
                _relative(path): _sha256(path)
                for path in (manifest_path, token_path, checkpoint_path)
            },
        }
    if any(config != configurations[0] for config in configurations[1:]):
        raise ValueError("development runs disagree on controlled configuration")
    return summaries, configurations[0]


def _mitigation_record() -> dict[str, object]:
    manifest = json.loads(R2_FAILURE.read_text(encoding="utf-8"))
    metrics = manifest["gate"]["metrics"]
    if manifest["status"] != "FAIL" or float(
        metrics["all_token_state_relative_l2_max"]
    ) <= STATE_RELATIVE_L2_MAXIMUM:
        raise ValueError("expected retained R2 encoded state-error failure")
    return {
        "candidate": manifest["variant"],
        "status": manifest["status"],
        "reason": "all-token state relative L2 exceeded the frozen 0.10 limit",
        "all_token_output_cosine_min": metrics["all_token_output_cosine_min"],
        "all_token_state_relative_l2_max": metrics[
            "all_token_state_relative_l2_max"
        ],
        "element_saturations": metrics["cumulative_element_saturations"],
        "accumulator_saturations": metrics["cumulative_accumulator_saturations"],
        "scale_clamps": metrics["cumulative_scale_clamps"],
        "manifest": _relative(R2_FAILURE),
        "manifest_sha256": _sha256(R2_FAILURE),
        "single_change": "increase fixed write-log capacity from two to three entries",
    }


def generate_registration(output: Path = OUTPUT) -> dict[str, object]:
    summaries, config = _development_summary()
    mitigation = _mitigation_record()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    encoded_bytes = logical_encoded_state_bytes(config)
    payload: dict[str, object] = {
        "schema": 1,
        "registration_status": "PASS",
        "candidate_evidence_status": "NOT_RUN",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": revision,
        "candidate_name": VARIANT,
        "scope": "encoded-integer native-MXFP4 layer-level synthetic recurrent stability",
        "controlled_configuration": {
            "num_value_heads": config.num_value_heads,
            "num_qk_heads": config.num_qk_heads,
            "key_dim": config.key_dim,
            "value_dim": config.value_dim,
            "activation_block_size": config.activation_block_size,
            "state_block_size": config.state_block_size,
            "activation_stack_depth": 2,
            "base_stack_depth": 2,
            "log_stack_depth": 2,
            "log_capacity": CAPACITY,
            "element_format": "E2M1",
            "shared_scale_format": "E8M0",
            "fold_policy": "fixed atomic all-head fold after three writes",
            "coefficient_format": "Q1.15",
            "accumulator_bits": 32,
            "alignment_guard_bits": 5,
            "target": "AMD Alveo U55C xcu55c-fsvh2892-2L-e",
        },
        "quality_gate": {
            "minimum_checkpoint_output_cosine": OUTPUT_COSINE_MINIMUM,
            "maximum_final_state_relative_l2": STATE_RELATIVE_L2_MAXIMUM,
            "minimum_all_token_output_cosine": OUTPUT_COSINE_MINIMUM,
            "maximum_all_token_state_relative_l2": STATE_RELATIVE_L2_MAXIMUM,
            "encoded_element_saturations_required": 0,
            "encoded_accumulator_saturations_required": 0,
            "encoded_scale_clamps_required": 0,
        },
        "mitigation_history": [mitigation],
        "development_gate": {
            "status": "PASS",
            "seed": 0xFB72,
            "seed_hex": "0xFB72",
            "trace_family": "high_retention",
            "initial_state_modes": ["random", "zero"],
            "tokens": 1024,
            "checkpoints": [64, 256, 1024],
            "results": summaries,
        },
        "held_out_gate": {
            "status": "NOT_RUN",
            "split": "rs2_encoded_held_out",
            "seeds": [0xA17E5EED, 0xC4D3B2A1, 0x06E5A1D0],
            "seed_hex": ["0xA17E5EED", "0xC4D3B2A1", "0x06E5A1D0"],
            "trace_family": "high_retention",
            "initial_state_modes": ["random", "zero"],
            "tokens": 1024,
            "checkpoints": [64, 256, 1024],
            "run_count": 6,
            "execution_order": "seed order as registered; random then zero within each seed",
            "aggregate_rule": "all six runs must pass every registered quality threshold",
        },
        "extended_development_gate": {
            "status": "NOT_RUN",
            "seed": 0xFB72,
            "seed_hex": "0xFB72",
            "trace_family": "high_retention",
            "initial_state_modes": ["random", "zero"],
            "tokens": 8192,
            "checkpoints": [64, 256, 1024, 4096, 8192],
            "rule": "both runs must pass every registered quality threshold",
        },
        "logical_state_bytes": {
            "encoded_candidate": encoded_bytes,
            "uniform_bf16": 1_048_576,
            "uniform_mxfp8_e4m3_b32": 540_672,
        },
        "frozen_source_sha256": {
            _relative(path): _sha256(path) for path in SOURCE_FILES
        },
        "stopping_rule": (
            "Do not alter the registered candidate after held-out execution. "
            "Retain every failed run and report the aggregate failure."
        ),
        "limitations": [
            "synthetic layer-level encoded-integer evidence only at registration",
            "HLS, RTL, routed, board-energy, and closed-loop model evidence remain NOT_RUN",
            "the encoded payload is smaller than BF16 but 6.70 percent larger than uniform MXFP8",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    payload = generate_registration()
    print(
        json.dumps(
            {
                "status": payload["registration_status"],
                "candidate": payload["candidate_name"],
                "output": _relative(OUTPUT),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Freeze the residual-stack MXFP4 candidate before test-set execution."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "mxfp4_rs2_base_capacity_sweep"
)
OUTPUT = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "mxfp4_rs2_candidate_preregistration.json"
)
CANDIDATE = "mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2"
DEVELOPMENT_FILES = {
    "random": {
        "tokens": EVIDENCE / "high_retention_random_mxfp4_log_tokens.csv",
        "checkpoints": EVIDENCE
        / "high_retention_random_mxfp4_log_checkpoints.csv",
        "manifest": EVIDENCE / "high_retention_random_mxfp4_log_manifest.json",
    },
    "zero": {
        "tokens": EVIDENCE / "high_retention_zero_mxfp4_log_tokens.csv",
        "checkpoints": EVIDENCE
        / "high_retention_zero_mxfp4_log_checkpoints.csv",
        "manifest": EVIDENCE / "high_retention_zero_mxfp4_log_manifest.json",
    },
}
SOURCE_FILES = (
    ROOT / "golden" / "gdn_write_log.py",
    ROOT / "scripts" / "write_log_stability.py",
    Path(__file__).resolve(),
)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _rows(path: Path, *, candidate_only: bool = True) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if candidate_only:
        rows = [row for row in rows if row["variant"] == CANDIDATE]
    if not rows:
        raise ValueError(f"candidate rows are absent from {_relative(path)}")
    return rows


def _development_summary() -> tuple[dict[str, object], int]:
    summaries: dict[str, object] = {}
    logical_bytes: set[int] = set()
    for initial_state, files in DEVELOPMENT_FILES.items():
        manifest = json.loads(files["manifest"].read_text(encoding="utf-8"))
        configuration = manifest["configuration"]
        if (
            configuration["tokens"] != 1024
            or configuration["trace_family"] != "high_retention"
            or configuration["seed"] != 0xFB72
            or manifest["initial_state_mode"] != initial_state
            or manifest["log_precision"] != "mxfp4_rs2"
            or manifest["activation_stack_depth"] != 2
            or manifest["base_stack_depth"] != 2
            or 2 not in manifest["capacities"]
        ):
            raise ValueError(f"unexpected development configuration for {initial_state}")

        token_rows = _rows(files["tokens"])
        checkpoint_rows = _rows(files["checkpoints"])
        final_rows = [row for row in checkpoint_rows if int(row["token_index"]) == 1024]
        if len(final_rows) != 1:
            raise ValueError(f"missing final checkpoint for {initial_state}")
        logical_bytes.update(int(row["logical_state_bytes"]) for row in token_rows)
        summary = {
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
            "dropped_entries": max(int(row["dropped_entries"]) for row in token_rows),
            "input_stream_sha256": manifest["input_stream_sha256"].upper(),
            "evidence_sha256": {
                _relative(path): _sha256(path) for path in files.values()
            },
        }
        if (
            summary["minimum_all_token_output_cosine"] < 0.99
            or summary["maximum_all_token_state_relative_l2"] > 0.10
            or summary["dropped_entries"] != 0
        ):
            raise ValueError(f"development gate failed for {initial_state}")
        summaries[initial_state] = summary
    if len(logical_bytes) != 1:
        raise ValueError("development runs disagree on logical state bytes")
    return summaries, logical_bytes.pop()


def generate_registration(output: Path = OUTPUT) -> dict[str, object]:
    summaries, diagnostic_bytes = _development_summary()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    payload: dict[str, object] = {
        "schema": 1,
        "registration_status": "PASS",
        "candidate_evidence_status": "NOT_RUN",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": revision,
        "candidate_name": CANDIDATE,
        "scope": "residual-stack native-MXFP4 layer-level synthetic recurrent stability",
        "controlled_configuration": {
            "num_value_heads": 32,
            "num_qk_heads": 16,
            "key_dim": 128,
            "value_dim": 128,
            "activation_block_size": 32,
            "state_block_size": 32,
            "activation_stack_depth": 2,
            "base_stack_depth": 2,
            "log_stack_depth": 2,
            "log_capacity": 2,
            "element_format": "E2M1",
            "shared_scale_format": "E8M0",
            "fold_policy": "fixed atomic all-head fold after two writes",
            "coefficient_format": "Q1.15",
            "accumulator_bits": 32,
            "alignment_guard_bits": 5,
            "target": "AMD Alveo U55C xcu55c-fsvh2892-2L-e",
        },
        "quality_gate": {
            "minimum_checkpoint_output_cosine": 0.99,
            "maximum_final_state_relative_l2": 0.10,
            "minimum_all_token_output_cosine": 0.99,
            "maximum_all_token_state_relative_l2": 0.10,
            "required_dropped_entries": 0,
            "encoded_element_saturations_required": 0,
            "encoded_accumulator_saturations_required": 0,
            "encoded_scale_clamps_required": 0,
        },
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
            "split": "rs2_held_out",
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
            "floating_diagnostic": diagnostic_bytes,
            "planned_q1_15_hardware": 570320,
            "uniform_bf16": 1048576,
            "uniform_mxfp8_e4m3_b32": 540672,
        },
        "frozen_source_sha256": {
            _relative(path): _sha256(path) for path in SOURCE_FILES
        },
        "stopping_rule": (
            "Do not alter the registered candidate after test-set execution. "
            "Retain every failed run and report the aggregate failure."
        ),
        "limitations": [
            "synthetic layer-level development evidence only at registration",
            "encoded-integer, HLS, RTL, routed, board-energy, and closed-loop model evidence remain NOT_RUN",
            "the registered payload is smaller than BF16 but slightly larger than uniform MXFP8",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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

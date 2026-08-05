"""Run preregistered E2M0 fold-residual development or held-out matrices."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from golden.vectors import DEFAULT_HEAD_DIM, DEFAULT_NUM_QK_HEADS, DEFAULT_NUM_VALUE_HEADS
from scripts.e2m0_residual_stability import (
    run_e2m0_trace,
    write_csv,
    write_manifest,
    write_report,
)
from scripts.long_sequence_stability import TraceConfiguration
from scripts.verify_e2m0_residual_stability import verify


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRATION = (
    ROOT / "reports" / "benchmark" / "corrected" / "e2m0_residual_preregistration.json"
)
DEFAULT_ROOT = ROOT / "reports" / "benchmark" / "corrected" / "e2m0_residual"
PREREQUISITE_MANIFESTS = (
    DEFAULT_ROOT / "development_robustness" / "matrix_manifest.json",
    DEFAULT_ROOT / "extended_development" / "matrix_manifest.json",
)
SUMMARY_FIELDS = [
    "gate",
    "split",
    "seed",
    "trace_family",
    "initial_state_mode",
    "token_index",
    "variant",
    "output_cosine_fp32",
    "output_rel_l2",
    "state_rel_l2",
    "state_max_abs",
    "folds",
    "dropped_entries",
    "logical_state_bytes",
    "run_status",
    "run_manifest",
    "run_verification",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_registration(path: Path) -> dict[str, object]:
    registration = json.loads(path.read_text(encoding="utf-8"))
    if registration.get("registration_status") != "PASS":
        raise RuntimeError("candidate registration is not PASS")
    if registration.get("candidate_evidence_status") != "NOT_RUN":
        raise RuntimeError("candidate registration was altered after freezing")
    for relative, expected in dict(registration["source_hashes"]).items():
        source = ROOT / relative
        if not source.is_file() or _sha256(source) != str(expected).upper():
            raise RuntimeError(f"frozen candidate source mismatch: {relative}")
    return registration


def build_specs(
    gate: str,
    registration: dict[str, object],
) -> tuple[str, int, tuple[int, ...], list[tuple[int, str, str]]]:
    if gate == "development_robustness":
        rule = dict(registration["development_robustness_gate"])
        seed0 = int(rule["high_retention_seeds"][0])
        states = tuple(str(value) for value in rule["initial_states"])
        specs = [
            (seed0, str(family), state)
            for family in rule["families_for_seed_0xfb72"]
            for state in states
        ]
        specs.extend(
            (int(seed), "high_retention", state)
            for seed in rule["high_retention_seeds"][1:]
            for state in states
        )
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
    if gate == "held_out":
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
    raise ValueError(f"unknown preregistered gate: {gate}")


def require_held_out_prerequisites(registration_path: Path) -> None:
    registration_hash = _sha256(registration_path)
    for path in PREREQUISITE_MANIFESTS:
        if not path.is_file():
            raise RuntimeError(f"held-out prerequisite is missing: {path}")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("status") != "PASS":
            raise RuntimeError(f"held-out prerequisite is not PASS: {path}")
        if str(manifest.get("registration_sha256", "")).upper() != registration_hash:
            raise RuntimeError(f"held-out prerequisite registration mismatch: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gate",
        required=True,
        choices=["development_robustness", "extended_development", "held_out"],
    )
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    registration_path = _resolve(args.registration)
    registration = load_registration(registration_path)
    if args.gate == "held_out":
        require_held_out_prerequisites(registration_path)
    split, tokens, checkpoints, specs = build_specs(args.gate, registration)
    output_dir = (
        _resolve(args.output_dir)
        if args.output_dir is not None
        else DEFAULT_ROOT / args.gate
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, object]] = []
    run_records: list[dict[str, object]] = []
    for seed, family, initial_state in specs:
        stem = f"{split}_seed{seed:08x}_{family}_{initial_state}"
        print(f"START {stem}", flush=True)
        config = TraceConfiguration(
            tokens=tokens,
            checkpoints=checkpoints,
            seed=seed,
            split=split,
            trace_family=family,
            num_value_heads=DEFAULT_NUM_VALUE_HEADS,
            num_qk_heads=DEFAULT_NUM_QK_HEADS,
            key_dim=DEFAULT_HEAD_DIM,
            value_dim=DEFAULT_HEAD_DIM,
            activation_block_size=32,
            state_block_size=32,
        )
        result = run_e2m0_trace(
            config,
            capacity=7,
            activation_stack_depth=2,
            base_stack_depth=2,
            log_mode="mxfp4_rs2",
            initial_state_mode=initial_state,
        )
        token_csv = output_dir / f"{stem}_tokens.csv"
        checkpoint_csv = output_dir / f"{stem}_checkpoints.csv"
        report = output_dir / f"{stem}.md"
        manifest = output_dir / f"{stem}_manifest.json"
        verification_path = output_dir / f"{stem}_verification.json"
        write_csv(token_csv, result.token_rows)
        write_csv(checkpoint_csv, result.checkpoint_rows)
        write_manifest(
            manifest,
            result=result,
            token_csv=token_csv,
            checkpoint_csv=checkpoint_csv,
        )
        write_report(
            report,
            result=result,
            token_csv=token_csv,
            checkpoint_csv=checkpoint_csv,
            manifest=manifest,
        )
        verification = verify(manifest)
        verification_path.write_text(
            json.dumps(verification, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        run_status = str(verification["status"])
        for row in result.checkpoint_rows:
            if row["variant"] == "fp32":
                continue
            summary_rows.append(
                {
                    "gate": args.gate,
                    "split": split,
                    "seed": seed,
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
                    "run_status": run_status,
                    "run_manifest": manifest.relative_to(ROOT).as_posix(),
                    "run_verification": verification_path.relative_to(ROOT).as_posix(),
                }
            )
        run_records.append(
            {
                "stem": stem,
                "status": run_status,
                "gate_pass": bool(verification["gate_pass"]),
                "input_stream_sha256": result.input_stream_sha256,
                "manifest": manifest.relative_to(ROOT).as_posix(),
                "manifest_sha256": _sha256(manifest),
                "verification": verification_path.relative_to(ROOT).as_posix(),
                "verification_sha256": _sha256(verification_path),
            }
        )
        print(
            f"DONE {stem} status={run_status} gate={verification['gate_pass']}",
            flush=True,
        )

    summary_csv = output_dir / "summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)
    status = "PASS" if all(record["status"] == "PASS" for record in run_records) else "FAIL"
    matrix_manifest = {
        "schema": 1,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gate": args.gate,
        "split": split,
        "tokens": tokens,
        "checkpoints": checkpoints,
        "registration": registration_path.relative_to(ROOT).as_posix(),
        "registration_sha256": _sha256(registration_path),
        "runs": run_records,
        "summary_csv": summary_csv.relative_to(ROOT).as_posix(),
        "summary_sha256": _sha256(summary_csv),
        "runner_sha256": _sha256(Path(__file__).resolve()),
    }
    manifest_path = output_dir / "matrix_manifest.json"
    manifest_path.write_text(
        json.dumps(matrix_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "gate": args.gate,
                "runs": len(run_records),
                "manifest": manifest_path.relative_to(ROOT).as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

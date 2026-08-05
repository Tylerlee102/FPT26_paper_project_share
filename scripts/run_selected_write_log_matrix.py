"""Run the frozen selected write-log candidate on a seed/family matrix."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from golden.vectors import DEFAULT_HEAD_DIM, DEFAULT_NUM_QK_HEADS, DEFAULT_NUM_VALUE_HEADS
from scripts.long_sequence_stability import DEFAULT_CHECKPOINTS, TraceConfiguration
from scripts.verify_write_log_stability import verify
from scripts.write_log_stability import (
    run_write_log_trace,
    write_csv,
    write_manifest,
    write_report,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION = (
    ROOT / "reports" / "benchmark" / "corrected" / "write_log_selection.json"
)
HELD_OUT_SEEDS = (0xA11CE, 0xC0FFEE, 0x5EED5)
DEVELOPMENT_SEEDS = (0xFB72, 0xFB73, 0xFB74)
SUMMARY_FIELDS = [
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _parse_checkpoints(raw: list[int] | None, tokens: int) -> tuple[int, ...]:
    values = DEFAULT_CHECKPOINTS if not raw else tuple(raw)
    return tuple(sorted({value for value in values if 1 <= value <= tokens}))


def _frozen_configuration(selection: dict[str, object]) -> dict[str, object]:
    config = dict(selection["selected_configuration"])
    expected = {
        "activation_block_size": 32,
        "activation_stack_depth": 2,
        "base_blocks_per_row": 4,
        "base_residual_block_fraction": 0.75,
        "base_residual_blocks_per_row": 3,
        "base_stack_depth": 2,
        "fold_policy": "fixed_atomic_all_head",
        "key_dim": 128,
        "log_capacity": 7,
        "log_precision": "mxfp8_e4m3",
        "num_qk_heads": 16,
        "num_value_heads": 32,
        "state_block_size": 32,
        "value_dim": 128,
    }
    if config != expected:
        raise RuntimeError("selection configuration does not match the frozen schema")
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--split", choices=["development", "held_out"], default="held_out")
    parser.add_argument("--seeds", nargs="+", type=lambda value: int(value, 0))
    parser.add_argument(
        "--families",
        nargs="+",
        choices=[
            "nominal",
            "dynamic_range",
            "cancellation",
            "high_retention",
            "decay_sweep",
            "adversarial",
        ],
        default=["nominal"],
    )
    parser.add_argument(
        "--initial-states", nargs="+", choices=["random", "zero"], default=["random"]
    )
    parser.add_argument("--tokens", type=int, default=8192)
    parser.add_argument("--checkpoints", nargs="+", type=int)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/benchmark/corrected/write_log_held_out"),
    )
    args = parser.parse_args(argv)

    selection_path = _resolve(args.selection)
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection.get("status") != "PASS":
        raise RuntimeError("selected configuration is not frozen PASS evidence")
    frozen = _frozen_configuration(selection)
    seeds = tuple(
        args.seeds
        if args.seeds
        else (HELD_OUT_SEEDS if args.split == "held_out" else DEVELOPMENT_SEEDS)
    )
    checkpoints = _parse_checkpoints(args.checkpoints, args.tokens)
    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, object]] = []
    run_records: list[dict[str, object]] = []

    for seed in seeds:
        for family in args.families:
            for initial_state in args.initial_states:
                stem = f"{args.split}_seed{seed:08x}_{family}_{initial_state}"
                print(f"START {stem}", flush=True)
                config = TraceConfiguration(
                    tokens=args.tokens,
                    checkpoints=checkpoints,
                    seed=seed,
                    split=args.split,
                    trace_family=family,
                    num_value_heads=DEFAULT_NUM_VALUE_HEADS,
                    num_qk_heads=DEFAULT_NUM_QK_HEADS,
                    key_dim=DEFAULT_HEAD_DIM,
                    value_dim=DEFAULT_HEAD_DIM,
                    activation_block_size=int(frozen["activation_block_size"]),
                    state_block_size=int(frozen["state_block_size"]),
                )
                result = run_write_log_trace(
                    config,
                    capacities=(int(frozen["log_capacity"]),),
                    log_precision=str(frozen["log_precision"]),
                    activation_stack_depth=int(frozen["activation_stack_depth"]),
                    base_stack_depth=int(frozen["base_stack_depth"]),
                    fold_policy="fixed",
                    initial_state_mode=initial_state,
                    base_residual_block_fraction=float(
                        frozen["base_residual_block_fraction"]
                    ),
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
                            "split": args.split,
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
    overall_status = "PASS" if all(record["status"] == "PASS" for record in run_records) else "FAIL"
    matrix_manifest = {
        "schema": 1,
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "selection": selection_path.relative_to(ROOT).as_posix(),
        "selection_sha256": _sha256(selection_path),
        "split": args.split,
        "seeds": seeds,
        "families": args.families,
        "initial_states": args.initial_states,
        "tokens": args.tokens,
        "checkpoints": checkpoints,
        "runs": run_records,
        "summary_csv": summary_csv.relative_to(ROOT).as_posix(),
        "summary_sha256": _sha256(summary_csv),
        "source_hashes": {
            "scripts/run_selected_write_log_matrix.py": _sha256(Path(__file__).resolve()),
            "scripts/write_log_stability.py": _sha256(
                ROOT / "scripts" / "write_log_stability.py"
            ),
            "golden/gdn_write_log.py": _sha256(ROOT / "golden" / "gdn_write_log.py"),
        },
    }
    manifest_path = output_dir / "matrix_manifest.json"
    manifest_path.write_text(
        json.dumps(matrix_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"MATRIX {overall_status} {manifest_path.relative_to(ROOT).as_posix()}")
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

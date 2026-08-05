"""Run the native encoded MXFP4 oracle over a controlled long synthetic trace."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import gdn_decode_step as fp32_decode_step, normalize_qk
from golden.gdn_mxfp4_encoded import decode_state, encode_state, encode_token
from golden.gdn_mxfp4_encoded_vectorized import (
    recurrence_core_step_encoded_vectorized,
)
from golden.vectors import (
    DEFAULT_HEAD_DIM,
    DEFAULT_NUM_QK_HEADS,
    DEFAULT_NUM_VALUE_HEADS,
    DEFAULT_SEED,
)
from scripts.evidence_source_snapshot import describe_source_files
from scripts.long_sequence_stability import (
    DEFAULT_CHECKPOINTS,
    TraceConfiguration,
    _error_metrics,
    _initial_state,
    _token_inputs,
    _update_input_hash,
)
from scripts.verify_vectorized_encoded_oracle import DEFAULT_OUTPUT as VECTOR_REPORT


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "benchmark" / "corrected"
DEFAULT_TOKEN_CSV = REPORT_DIR / "native_encoded_long_trace_tokens.csv"
DEFAULT_CHECKPOINT_CSV = REPORT_DIR / "native_encoded_long_trace_checkpoints.csv"
DEFAULT_REPORT = REPORT_DIR / "native_encoded_long_trace.md"
DEFAULT_MANIFEST = REPORT_DIR / "native_encoded_long_trace_manifest.json"
DEFAULT_SNAPSHOT_DIR = REPORT_DIR / "native_encoded_long_trace_snapshots"
FLOATING_MANIFEST = REPORT_DIR / "long_trace_manifest.json"
VARIANT = "native_mxfp4_encoded_act_b32_state_b32"
COUNTER_FIELDS = (
    "element_saturations",
    "accumulator_saturations",
    "scale_clamps",
    "alignment_underflows",
    "state_scale_changes",
)
CSV_FIELDS = (
    "run_id",
    "split",
    "seed",
    "trace_family",
    "variant",
    "layer_id",
    "token_index",
    "output_cosine_fp32",
    "output_rel_l2",
    "output_max_abs",
    "state_rel_l2",
    "state_max_abs",
    *(f"command_{field}" for field in COUNTER_FIELDS),
    *(f"cumulative_{field}" for field in COUNTER_FIELDS),
    "event_metrics_status",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        writer.writerows(rows)


def _write_snapshot(
    path: Path,
    *,
    token_index: int,
    reference_state: np.ndarray,
    encoded_state: object,
    reference_output: np.ndarray | None = None,
    encoded_output: np.ndarray | None = None,
) -> None:
    payload: dict[str, object] = {
        "token_index": np.asarray([token_index], dtype=np.int64),
        "reference_state": np.asarray(reference_state, dtype=np.float32),
        "encoded_state_elements": np.asarray(encoded_state.elements, dtype=np.uint8),
        "encoded_state_scales": np.asarray(encoded_state.scales, dtype=np.uint8),
        "block_size": np.asarray([encoded_state.block_size], dtype=np.int64),
    }
    if reference_output is not None and encoded_output is not None:
        payload["reference_output"] = np.asarray(reference_output, dtype=np.float32)
        payload["encoded_output"] = np.asarray(encoded_output, dtype=np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **payload)


def run_native_encoded_trace(
    config: TraceConfiguration,
    *,
    snapshot_dir: Path,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, dict[str, object]],
    str,
    str,
    float,
]:
    if config.tokens <= 0:
        raise ValueError("tokens must be positive")
    if config.activation_block_size != 32 or config.state_block_size != 32:
        raise ValueError("native encoded long trace is frozen to OCP MXFP4-B32")
    if config.num_value_heads % config.num_qk_heads != 0:
        raise ValueError("num_value_heads must be divisible by num_qk_heads")
    snapshot_dir = _resolve(snapshot_dir)

    reference_state = _initial_state(config)
    encoded_state = encode_state(reference_state, block_size=config.state_block_size)
    initial_state_sha256 = hashlib.sha256(
        np.ascontiguousarray(reference_state).tobytes()
    ).hexdigest()
    input_hasher = hashlib.sha256()
    _update_input_hash(input_hasher, "initial_state", reference_state)
    cumulative = {field: 0 for field in COUNTER_FIELDS}
    rows: list[dict[str, object]] = []
    checkpoints: list[dict[str, object]] = []
    snapshot_records: dict[str, dict[str, object]] = {}
    checkpoint_set = set(config.checkpoints)

    initial_snapshot = snapshot_dir / "token_00000.npz"
    _write_snapshot(
        initial_snapshot,
        token_index=0,
        reference_state=reference_state,
        encoded_state=encoded_state,
    )
    snapshot_records[initial_snapshot.relative_to(ROOT).as_posix()] = {
        "token_index": 0,
        "sha256": _sha256(initial_snapshot),
        "bytes": initial_snapshot.stat().st_size,
    }

    started = time.perf_counter()
    for token_zero_based in range(config.tokens):
        token_index = token_zero_based + 1
        q, k, v, alpha, beta = _token_inputs(config, token_zero_based)
        for name, array in (
            ("q", q),
            ("k", k),
            ("v", v),
            ("alpha", alpha),
            ("beta", beta),
        ):
            _update_input_hash(input_hasher, name, array)
        reference_output, reference_state = fp32_decode_step(
            q, k, v, alpha, beta, reference_state
        )
        q_scaled, k_normalized = normalize_qk(q, k)
        token = encode_token(
            q_scaled,
            k_normalized,
            v,
            alpha,
            beta,
            block_size=config.activation_block_size,
        )
        result = recurrence_core_step_encoded_vectorized(token, encoded_state)
        encoded_state = result.state
        decoded_state = decode_state(encoded_state)
        output_metrics = _error_metrics(reference_output, result.output_fp32)
        state_metrics = _error_metrics(reference_state, decoded_state)
        command = result.counters.as_dict()
        for field in COUNTER_FIELDS:
            cumulative[field] += int(command[field])
        row: dict[str, object] = {
            "run_id": f"native_encoded_{config.seed:08x}_{config.trace_family}",
            "split": config.split,
            "seed": config.seed,
            "trace_family": config.trace_family,
            "variant": VARIANT,
            "layer_id": 0,
            "token_index": token_index,
            "output_cosine_fp32": output_metrics["cosine"],
            "output_rel_l2": output_metrics["rel_l2"],
            "output_max_abs": output_metrics["max_abs"],
            "state_rel_l2": state_metrics["rel_l2"],
            "state_max_abs": state_metrics["max_abs"],
            "event_metrics_status": "PASS",
        }
        row.update({f"command_{field}": int(command[field]) for field in COUNTER_FIELDS})
        row.update(
            {f"cumulative_{field}": cumulative[field] for field in COUNTER_FIELDS}
        )
        rows.append(row)

        if token_index in checkpoint_set:
            checkpoints.append(dict(row))
            snapshot = snapshot_dir / f"token_{token_index:05d}.npz"
            _write_snapshot(
                snapshot,
                token_index=token_index,
                reference_state=reference_state,
                encoded_state=encoded_state,
                reference_output=reference_output,
                encoded_output=result.output_fp32,
            )
            snapshot_records[snapshot.relative_to(ROOT).as_posix()] = {
                "token_index": token_index,
                "sha256": _sha256(snapshot),
                "bytes": snapshot.stat().st_size,
            }
    elapsed = time.perf_counter() - started
    return (
        rows,
        checkpoints,
        snapshot_records,
        input_hasher.hexdigest(),
        initial_state_sha256,
        elapsed,
    )


def _engineering_gate(checkpoints: list[dict[str, object]]) -> dict[str, object]:
    final = checkpoints[-1]
    cosine_pass = all(
        float(row["output_cosine_fp32"]) >= 0.99 for row in checkpoints
    )
    state_pass = float(final["state_rel_l2"]) <= 0.10
    no_saturation = all(
        int(final[f"cumulative_{field}"]) == 0
        for field in (
            "element_saturations",
            "accumulator_saturations",
            "scale_clamps",
        )
    )
    return {
        "status": "PASS" if cosine_pass and state_pass and no_saturation else "FAIL",
        "output_cosine_at_least_0p99_all_checkpoints": "PASS" if cosine_pass else "FAIL",
        "state_relative_l2_at_most_0p10_at_final": "PASS" if state_pass else "FAIL",
        "zero_element_accumulator_or_scale_saturation": "PASS" if no_saturation else "FAIL",
    }


def generate(
    config: TraceConfiguration,
    *,
    token_csv: Path,
    checkpoint_csv: Path,
    report_path: Path,
    manifest_path: Path,
    snapshot_dir: Path,
) -> dict[str, object]:
    vector_report = json.loads(VECTOR_REPORT.read_text(encoding="utf-8"))
    if vector_report.get("status") != "PASS":
        raise ValueError("vectorized encoded oracle cross-check is not PASS")
    floating_manifest = json.loads(FLOATING_MANIFEST.read_text(encoding="utf-8"))
    started_at = datetime.now(timezone.utc)
    (
        rows,
        checkpoints,
        snapshots,
        input_sha256,
        initial_state_sha256,
        elapsed,
    ) = run_native_encoded_trace(config, snapshot_dir=snapshot_dir)
    if input_sha256 != floating_manifest["input_sha256"]:
        raise ValueError("native and floating long traces do not share an input stream")
    if initial_state_sha256 != floating_manifest["initial_state_sha256"]:
        raise ValueError("native and floating long traces do not share initial state")

    _write_csv(token_csv, rows)
    _write_csv(checkpoint_csv, checkpoints)
    gate = _engineering_gate(checkpoints)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Native Encoded MXFP4 Long-Sequence Diagnostic",
        "",
        "- Evidence generation: `PASS`",
        f"- Frozen synthetic engineering gate: `{gate['status']}`",
        f"- Tokens: `{config.tokens}`",
        f"- Checkpoints: `{', '.join(str(value) for value in config.checkpoints)}`",
        f"- Seed/split/family: `{hex(config.seed)}` / `{config.split}` / `{config.trace_family}`",
        "- Boundary: corrected K-by-V GDN recurrence core",
        "- Arithmetic: encoded E2M1 elements, E8M0 B32 scales, Q1.15 alpha/beta, ordered INT32 accumulation, RNE state write",
        "",
        "| Token | Output cosine | Output rel L2 | State rel L2 | State max abs | Cum. element sat. | Cum. accum. sat. | Cum. scale clamps | Cum. align underflows |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in checkpoints:
        lines.append(
            f"| {row['token_index']} | {float(row['output_cosine_fp32']):.6f} | "
            f"{float(row['output_rel_l2']):.6f} | {float(row['state_rel_l2']):.6f} | "
            f"{float(row['state_max_abs']):.6f} | {row['cumulative_element_saturations']} | "
            f"{row['cumulative_accumulator_saturations']} | {row['cumulative_scale_clamps']} | "
            f"{row['cumulative_alignment_underflows']} |"
        )
    lines.extend(
        [
            "",
            "This is a deterministic layer-boundary synthetic trace. It is not closed-loop model, routed FPGA, or board evidence.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")

    source_paths = [
        ROOT / "golden" / "gdn_fp32.py",
        ROOT / "golden" / "gdn_mxfp4_encoded.py",
        ROOT / "golden" / "gdn_mxfp4_encoded_vectorized.py",
        ROOT / "golden" / "mx_format.py",
        ROOT / "scripts" / "long_sequence_stability.py",
        ROOT / "scripts" / "native_encoded_long_trace.py",
        ROOT / "scripts" / "verify_vectorized_encoded_oracle.py",
    ]
    manifest: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "engineering_gate": gate,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "scope": "native encoded MXFP4 long-horizon synthetic recurrence diagnostic",
        "variant": VARIANT,
        "configuration": {
            **config.__dict__,
            "checkpoints": list(config.checkpoints),
            "orientation": "KxV",
        },
        "controlled_hardware_context": {
            "target": "xcu55c-fsvh2892-2L-e",
            "clock_ns": 4.0,
            "p_k": 16,
            "p_v": 8,
            "block_size": 32,
            "state_layout": "36 layer slots x 32 heads x 128 K x 128 V",
            "note": "This software run changes arithmetic only; HLS cost is extracted separately at this fixed design point.",
        },
        "input_stream_sha256": input_sha256.upper(),
        "initial_state_sha256": initial_state_sha256.upper(),
        "shared_floating_trace": {
            "path": FLOATING_MANIFEST.relative_to(ROOT).as_posix(),
            "sha256": _sha256(FLOATING_MANIFEST),
            "input_match": "PASS",
            "initial_state_match": "PASS",
        },
        "vectorized_oracle_crosscheck": {
            "path": VECTOR_REPORT.relative_to(ROOT).as_posix(),
            "sha256": _sha256(VECTOR_REPORT),
            "status": vector_report["status"],
            "tokens": vector_report["configuration"]["tokens"],
        },
        "outputs": {
            token_csv.relative_to(ROOT).as_posix(): {
                "sha256": _sha256(token_csv),
                "bytes": token_csv.stat().st_size,
                "rows": len(rows),
            },
            checkpoint_csv.relative_to(ROOT).as_posix(): {
                "sha256": _sha256(checkpoint_csv),
                "bytes": checkpoint_csv.stat().st_size,
                "rows": len(checkpoints),
            },
            report_path.relative_to(ROOT).as_posix(): {
                "sha256": _sha256(report_path),
                "bytes": report_path.stat().st_size,
            },
        },
        "snapshots": snapshots,
        "source_identity": describe_source_files(source_paths),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "command": "python -m scripts.native_encoded_long_trace",
        "exit_code": 0,
        "independent_verification": (
            "python -m scripts.verify_native_encoded_long_trace rehashes every "
            "artifact, checks row/counter invariants and shared inputs, and "
            "recomputes all checkpoint metrics from saved full-state snapshots"
        ),
        "limitations": [
            "one deterministic development seed and nominal synthetic trace",
            "layer-boundary recurrence only; not closed-loop Qwen quality",
            "software encoded oracle; HLS/RTL parity is separately bounded to 64 tokens",
            "no post-route timing, physical fit, or board energy",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=int, default=8192)
    parser.add_argument("--checkpoints", nargs="*")
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--split", choices=("development", "held_out"), default="development")
    parser.add_argument("--trace-family", default="nominal")
    parser.add_argument("--token-csv", type=Path, default=DEFAULT_TOKEN_CSV)
    parser.add_argument("--checkpoint-csv", type=Path, default=DEFAULT_CHECKPOINT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--snapshot-dir", type=Path, default=DEFAULT_SNAPSHOT_DIR)
    args = parser.parse_args(argv)
    raw_checkpoints = DEFAULT_CHECKPOINTS if not args.checkpoints else tuple(
        int(value, 0) for value in args.checkpoints
    )
    checkpoints = tuple(
        sorted({value for value in raw_checkpoints if 1 <= value <= args.tokens})
    )
    config = TraceConfiguration(
        tokens=args.tokens,
        checkpoints=checkpoints,
        seed=args.seed,
        split=args.split,
        trace_family=args.trace_family,
        num_value_heads=DEFAULT_NUM_VALUE_HEADS,
        num_qk_heads=DEFAULT_NUM_QK_HEADS,
        key_dim=DEFAULT_HEAD_DIM,
        value_dim=DEFAULT_HEAD_DIM,
        activation_block_size=32,
        state_block_size=32,
    )
    result = generate(
        config,
        token_csv=_resolve(args.token_csv),
        checkpoint_csv=_resolve(args.checkpoint_csv),
        report_path=_resolve(args.report),
        manifest_path=_resolve(args.manifest),
        snapshot_dir=_resolve(args.snapshot_dir),
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "engineering_gate": result["engineering_gate"]["status"],
                "tokens": result["configuration"]["tokens"],
                "elapsed_seconds": result["elapsed_seconds"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

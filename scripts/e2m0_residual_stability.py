"""Evaluate the dense E2M0 fold-residual mitigation on corrected GDN traces."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_e2m0_residual import (
    E2M0_RESIDUAL_BITS,
    E2M0_RESIDUAL_VALUES,
    E2M0_SCALE_POLICY,
    E2M0ResidualWriteLogGDN,
)
from golden.gdn_fp32 import gdn_recurrence_core_step, normalize_qk
from golden.gdn_mxfp4_encoded import decode_q1_15, encode_q1_15
from golden.gdn_write_log import WriteLogConfiguration, quantize_mxfp4_stack
from golden.vectors import (
    DEFAULT_HEAD_DIM,
    DEFAULT_NUM_QK_HEADS,
    DEFAULT_NUM_VALUE_HEADS,
    DEFAULT_SEED,
)
from scripts.long_sequence_stability import DEFAULT_CHECKPOINTS, TraceConfiguration
from scripts.write_log_stability import (
    FIELDS,
    _passes_gate,
    _row,
    _trace_initial_state,
    _trace_inputs,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "reports" / "benchmark" / "corrected" / "e2m0_residual"


@dataclass(frozen=True)
class E2M0RunResult:
    token_rows: list[dict[str, object]]
    checkpoint_rows: list[dict[str, object]]
    config: TraceConfiguration
    capacity: int
    activation_stack_depth: int
    base_stack_depth: int
    log_mode: str
    initial_state_mode: str
    input_stream_sha256: str
    logical_state_bytes: int
    variant: str


def _blocked_bytes(length: int, block_size: int, bytes_per_block: int) -> int:
    return ((length + block_size - 1) // block_size) * bytes_per_block


def logical_e2m0_state_bytes(
    config: TraceConfiguration,
    *,
    capacity: int,
    base_stack_depth: int,
    log_mode: str = "mxfp4_rs2",
) -> int:
    """Logical bytes for the corrected base and selected write-log format."""

    rows = config.num_value_heads * config.key_dim
    mxfp4_block_bytes = config.state_block_size // 2 + 1
    base_row_bytes = _blocked_bytes(
        config.value_dim, config.state_block_size, mxfp4_block_bytes
    )
    e2m0_block_bytes = (
        config.state_block_size * E2M0_RESIDUAL_BITS + 7
    ) // 8 + 1
    residual_row_bytes = _blocked_bytes(
        config.value_dim, config.state_block_size, e2m0_block_bytes
    )
    base_bytes = rows * (
        base_row_bytes + max(0, base_stack_depth - 1) * residual_row_bytes
    )

    if log_mode == "mxfp4_rs2":
        log_block_bytes = 2 * (config.state_block_size // 2 + 1)
    elif log_mode == "mxfp8_e4m3":
        log_block_bytes = config.state_block_size + 1
    else:
        raise ValueError(f"unknown log mode: {log_mode}")
    key_row_bytes = _blocked_bytes(
        config.key_dim, config.state_block_size, log_block_bytes
    )
    update_row_bytes = _blocked_bytes(
        config.value_dim, config.state_block_size, log_block_bytes
    )
    log_bytes = capacity * (
        config.num_qk_heads * key_row_bytes
        + config.num_value_heads * update_row_bytes
    )
    coefficient_bytes = 4 * (
        config.num_value_heads + capacity * config.num_value_heads
    )
    return base_bytes + log_bytes + coefficient_bytes + 16


def _variant_name(
    config: TraceConfiguration,
    *,
    capacity: int,
    activation_stack_depth: int,
    base_stack_depth: int,
    log_mode: str,
) -> str:
    log_label = "mxfp4rs2" if log_mode == "mxfp4_rs2" else "mxfp8"
    return (
        f"mxfp4_rs{activation_stack_depth}_act_"
        f"mxfp4_e2m0rs{base_stack_depth}_base_b{config.state_block_size}_"
        f"{log_label}_log_fixed_b{config.state_block_size}_r{capacity}"
    )


def run_e2m0_trace(
    config: TraceConfiguration,
    *,
    capacity: int = 7,
    activation_stack_depth: int = 2,
    base_stack_depth: int = 2,
    log_mode: str = "mxfp4_rs2",
    initial_state_mode: str = "random",
) -> E2M0RunResult:
    if config.tokens <= 0:
        raise ValueError("tokens must be positive")
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    if config.num_value_heads % config.num_qk_heads != 0:
        raise ValueError("num_value_heads must be divisible by num_qk_heads")

    initial_state = _trace_initial_state(config, initial_state_mode)
    reference_state = initial_state.copy()
    engine = E2M0ResidualWriteLogGDN(
        initial_state,
        num_qk_heads=config.num_qk_heads,
        config=WriteLogConfiguration(
            capacity=capacity,
            mode="mxfp4",
            activation_block_size=config.activation_block_size,
            base_block_size=config.state_block_size,
            log_block_size=config.state_block_size,
            log_precision="mxfp8_e4m3",
            activation_stack_depth=activation_stack_depth,
            base_stack_depth=base_stack_depth,
            fold_policy="fixed",
        ),
        log_mode=log_mode,
    )
    state_bytes = logical_e2m0_state_bytes(
        config,
        capacity=capacity,
        base_stack_depth=base_stack_depth,
        log_mode=log_mode,
    )
    variant = _variant_name(
        config,
        capacity=capacity,
        activation_stack_depth=activation_stack_depth,
        base_stack_depth=base_stack_depth,
        log_mode=log_mode,
    )
    fp32_state_bytes = (
        config.num_value_heads * config.key_dim * config.value_dim * 4
    )
    checkpoint_set = set(config.checkpoints)
    token_rows: list[dict[str, object]] = []
    checkpoint_rows: list[dict[str, object]] = []
    input_digest = hashlib.sha256()
    input_digest.update(np.ascontiguousarray(initial_state).tobytes())

    for token_zero_based in range(config.tokens):
        token_index = token_zero_based + 1
        q, k, v, alpha, beta = _trace_inputs(config, token_zero_based)
        for array in (q, k, v, alpha, beta):
            input_digest.update(np.ascontiguousarray(array).tobytes())

        q_scaled, k_normalized = normalize_qk(q, k)
        reference_output, reference_state = gdn_recurrence_core_step(
            q_scaled, k_normalized, v, alpha, beta, reference_state
        )
        fp32_row = _row(
            config,
            token_index=token_index,
            variant="fp32",
            reference_output=reference_output,
            reference_state=reference_state,
            output=reference_output,
            state=reference_state,
            engine=None,
            state_bytes=fp32_state_bytes,
            initial_state_mode=initial_state_mode,
        )
        token_rows.append(fp32_row)
        if token_index in checkpoint_set:
            checkpoint_rows.append(dict(fp32_row))

        q_quantized = quantize_mxfp4_stack(
            q_scaled,
            block_size=config.activation_block_size,
            depth=activation_stack_depth,
        )
        k_quantized = quantize_mxfp4_stack(
            k_normalized,
            block_size=config.activation_block_size,
            depth=activation_stack_depth,
        )
        v_quantized = quantize_mxfp4_stack(
            v,
            block_size=config.activation_block_size,
            depth=activation_stack_depth,
        )
        output, state = engine.step_core(
            q_quantized,
            k_quantized,
            v_quantized,
            decode_q1_15(encode_q1_15(alpha)),
            decode_q1_15(encode_q1_15(beta)),
        )
        candidate_row = _row(
            config,
            token_index=token_index,
            variant=variant,
            reference_output=reference_output,
            reference_state=reference_state,
            output=output,
            state=state,
            engine=engine,
            state_bytes=state_bytes,
            initial_state_mode=initial_state_mode,
        )
        token_rows.append(candidate_row)
        if token_index in checkpoint_set:
            checkpoint_rows.append(dict(candidate_row))

    checkpoint_rows.sort(key=lambda row: (int(row["token_index"]), str(row["variant"])))
    return E2M0RunResult(
        token_rows=token_rows,
        checkpoint_rows=checkpoint_rows,
        config=config,
        capacity=capacity,
        activation_stack_depth=activation_stack_depth,
        base_stack_depth=base_stack_depth,
        log_mode=log_mode,
        initial_state_mode=initial_state_mode,
        input_stream_sha256=input_digest.hexdigest(),
        logical_state_bytes=state_bytes,
        variant=variant,
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(
    path: Path,
    *,
    result: E2M0RunResult,
    token_csv: Path,
    checkpoint_csv: Path,
) -> None:
    sources = [
        ROOT / "golden" / "gdn_e2m0_residual.py",
        ROOT / "golden" / "gdn_fp32.py",
        ROOT / "golden" / "gdn_mxfp4.py",
        ROOT / "golden" / "gdn_write_log.py",
        ROOT / "golden" / "mx_format.py",
        ROOT / "scripts" / "long_sequence_stability.py",
        ROOT / "scripts" / "write_log_stability.py",
        Path(__file__).resolve(),
    ]
    payload = {
        "schema": 1,
        "status": "diagnostic_only",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": result.config.__dict__,
        "variant": result.variant,
        "capacity": result.capacity,
        "activation_stack_depth": result.activation_stack_depth,
        "base_stack_depth": result.base_stack_depth,
        "base_primary_format": "E2M1/E8M0 MXFP4",
        "base_residual_format": "signed 3-bit [0,0.5,1,2] magnitudes with E8M0",
        "base_residual_element_bits": E2M0_RESIDUAL_BITS,
        "base_residual_values": E2M0_RESIDUAL_VALUES.tolist(),
        "base_residual_scale_policy": E2M0_SCALE_POLICY,
        "log_mode": result.log_mode,
        "log_stack_depth": 2 if result.log_mode == "mxfp4_rs2" else 1,
        "fold_policy": "fixed_atomic_all_head",
        "initial_state_mode": result.initial_state_mode,
        "logical_state_bytes": result.logical_state_bytes,
        "input_stream_sha256": result.input_stream_sha256,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "source_hashes": {
            source.relative_to(ROOT).as_posix(): _sha256(source) for source in sources
        },
        "outputs": {
            token_csv.relative_to(ROOT).as_posix(): _sha256(token_csv),
            checkpoint_csv.relative_to(ROOT).as_posix(): _sha256(checkpoint_csv),
        },
        "limitations": [
            "synthetic inputs",
            "floating quantize/dequantize mitigation, not encoded-integer or RTL",
            "logical storage bytes, not placed BRAM/URAM allocation",
            "E2M0-style residual is a custom correction, not an OCP MXFP4 element",
            "not closed-loop Qwen quality evidence",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_report(
    path: Path,
    *,
    result: E2M0RunResult,
    token_csv: Path,
    checkpoint_csv: Path,
    manifest: Path,
) -> None:
    status = "PASS" if _passes_gate(result.checkpoint_rows, result.config.tokens) else "FAIL"
    lines = [
        "# Dense E2M0 Fold-Residual Development Diagnostic",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Engineering gate at executed length: `{status}`",
        f"Variant: `{result.variant}`",
        (
            f"Split/seed/family: `{result.config.split}` / "
            f"`{hex(result.config.seed)}` / `{result.config.trace_family}`"
        ),
        f"Initial state: `{result.initial_state_mode}`",
        f"Tokens/checkpoints: {result.config.tokens} / {', '.join(map(str, result.config.checkpoints))}",
        f"Logical recurrent-state bytes: {result.logical_state_bytes}",
        f"Input-stream SHA256: `{result.input_stream_sha256}`",
        f"Token CSV: `{token_csv.relative_to(ROOT).as_posix()}`",
        f"Checkpoint CSV: `{checkpoint_csv.relative_to(ROOT).as_posix()}`",
        f"Manifest: `{manifest.relative_to(ROOT).as_posix()}`",
        "",
        "The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The write log uses two residual-stacked MXFP4 terms; fold schedule, recurrence boundary, and activation stack are unchanged.",
        "",
        "| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result.checkpoint_rows:
        lines.append(
            f"| {row['token_index']} | {row['variant']} | "
            f"{float(row['output_cosine_fp32']):.6f} | "
            f"{float(row['output_rel_l2']):.6f} | "
            f"{float(row['state_rel_l2']):.6f} | "
            f"{float(row['state_max_abs']):.6f} | "
            f"{row['folds']} | {row['dropped_entries']} | {row['logical_state_bytes']} |"
        )
    lines.extend(
        [
            "",
            "This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _parse_checkpoints(raw: list[str] | None, tokens: int) -> tuple[int, ...]:
    values = DEFAULT_CHECKPOINTS if not raw else tuple(int(value, 0) for value in raw)
    return tuple(sorted({value for value in values if 1 <= value <= tokens}))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=int, default=1024)
    parser.add_argument("--checkpoints", nargs="*")
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--split", choices=["development", "held_out"], default="development")
    parser.add_argument(
        "--trace-family",
        choices=[
            "nominal",
            "dynamic_range",
            "cancellation",
            "high_retention",
            "decay_sweep",
            "adversarial",
        ],
        default="high_retention",
    )
    parser.add_argument("--capacity", type=int, default=7)
    parser.add_argument("--activation-stack-depth", type=int, default=2)
    parser.add_argument("--base-stack-depth", type=int, default=2)
    parser.add_argument(
        "--log-mode",
        choices=["mxfp4_rs2", "mxfp8_e4m3"],
        default="mxfp4_rs2",
    )
    parser.add_argument("--initial-state", choices=["random", "zero"], default="random")
    parser.add_argument("--num-value-heads", type=int, default=DEFAULT_NUM_VALUE_HEADS)
    parser.add_argument("--num-qk-heads", type=int, default=DEFAULT_NUM_QK_HEADS)
    parser.add_argument("--key-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--value-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--activation-block-size", type=int, choices=[16, 32], default=32)
    parser.add_argument("--state-block-size", type=int, choices=[16, 32], default=32)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--stem", default="development_e2m0_residual")
    args = parser.parse_args(argv)

    config = TraceConfiguration(
        tokens=args.tokens,
        checkpoints=_parse_checkpoints(args.checkpoints, args.tokens),
        seed=args.seed,
        split=args.split,
        trace_family=args.trace_family,
        num_value_heads=args.num_value_heads,
        num_qk_heads=args.num_qk_heads,
        key_dim=args.key_dim,
        value_dim=args.value_dim,
        activation_block_size=args.activation_block_size,
        state_block_size=args.state_block_size,
    )
    result = run_e2m0_trace(
        config,
        capacity=args.capacity,
        activation_stack_depth=args.activation_stack_depth,
        base_stack_depth=args.base_stack_depth,
        log_mode=args.log_mode,
        initial_state_mode=args.initial_state,
    )
    output_dir = _resolve(args.output_dir)
    token_csv = output_dir / f"{args.stem}_tokens.csv"
    checkpoint_csv = output_dir / f"{args.stem}_checkpoints.csv"
    manifest = output_dir / f"{args.stem}_manifest.json"
    report = output_dir / f"{args.stem}.md"
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
    print(
        json.dumps(
            {
                "status": "PASS" if _passes_gate(result.checkpoint_rows, config.tokens) else "FAIL",
                "report": report.relative_to(ROOT).as_posix(),
                "manifest": manifest.relative_to(ROOT).as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Evaluate bounded lazy-base/write-log candidates on corrected GDN traces."""

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

from golden.gdn_fp32 import gdn_recurrence_core_step, normalize_qk
from golden.gdn_mxfp4_encoded import decode_q1_15, encode_q1_15
from golden.gdn_write_log import (
    LazyWriteLogGDN,
    WriteLogConfiguration,
    quantize_mxfp4_stack,
)
from golden.vectors import (
    DEFAULT_HEAD_DIM,
    DEFAULT_NUM_QK_HEADS,
    DEFAULT_NUM_VALUE_HEADS,
    DEFAULT_SEED,
)
from scripts.long_sequence_stability import (
    DEFAULT_CHECKPOINTS,
    TraceConfiguration,
    _error_metrics,
    _initial_state,
    _token_inputs,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKEN_CSV = (
    ROOT / "reports" / "benchmark" / "corrected" / "write_log_development_tokens.csv"
)
DEFAULT_CHECKPOINT_CSV = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "write_log_development_checkpoints.csv"
)
DEFAULT_REPORT = (
    ROOT / "reports" / "benchmark" / "corrected" / "write_log_development.md"
)
DEFAULT_MANIFEST = (
    ROOT / "reports" / "benchmark" / "corrected" / "write_log_development_manifest.json"
)


@dataclass(frozen=True)
class WriteLogRunResult:
    token_rows: list[dict[str, object]]
    checkpoint_rows: list[dict[str, object]]
    config: TraceConfiguration
    capacities: tuple[int, ...]
    log_precision: str
    activation_stack_depth: int
    base_stack_depth: int
    fold_policy: str
    adaptive_min_entries: int
    fold_decay_threshold: float
    initial_state_mode: str
    base_residual_block_fraction: float
    input_stream_sha256: str


FIELDS = [
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
    "folds",
    "coefficient_rebases",
    "dropped_entries",
    "live_entries",
    "max_live_entries",
    "logical_state_bytes",
    "event_metrics_status",
]


def _variant_name(
    config: TraceConfiguration,
    capacity: int,
    log_precision: str,
    activation_stack_depth: int,
    base_stack_depth: int,
    fold_policy: str,
    fold_decay_threshold: float,
    base_residual_block_fraction: float,
) -> str:
    precision = log_precision.replace("_e4m3", "")
    policy = (
        "fixed"
        if fold_policy == "fixed"
        else f"adaptive_decay{int(round(fold_decay_threshold * 1000)):03d}"
    )
    sparse = (
        "dense"
        if base_residual_block_fraction >= 1.0
        else f"sparse{int(round(base_residual_block_fraction * 100)):02d}"
    )
    return (
        f"mxfp4_rs{activation_stack_depth}_act_rs{base_stack_depth}_{sparse}_base_"
        f"b{config.state_block_size}_{precision}_log_{policy}_"
        f"b{config.state_block_size}_r{capacity}"
    )


def _blocked_bytes(length: int, block_size: int, bytes_per_block: int) -> int:
    return ((length + block_size - 1) // block_size) * bytes_per_block


def logical_state_bytes(
    config: TraceConfiguration,
    *,
    capacity: int,
    log_precision: str,
    base_stack_depth: int = 1,
    base_residual_block_fraction: float = 1.0,
) -> int:
    base_row_bytes = _blocked_bytes(
        config.value_dim,
        config.state_block_size,
        config.state_block_size // 2 + 1,
    )
    rows = config.num_value_heads * config.key_dim
    base_bytes = rows * base_row_bytes
    if base_stack_depth > 1:
        blocks_per_row = (config.value_dim + config.state_block_size - 1) // config.state_block_size
        selected_blocks = min(
            blocks_per_row,
            int(np.ceil(blocks_per_row * base_residual_block_fraction)),
        )
        block_bytes = config.state_block_size // 2 + 1
        bitmap_bytes = (
            0
            if base_residual_block_fraction >= 1.0
            else (blocks_per_row + 7) // 8
        )
        residual_layer_bytes = rows * (
            selected_blocks * block_bytes + bitmap_bytes
        )
        base_bytes += (base_stack_depth - 1) * residual_layer_bytes
    if log_precision == "mxfp8_e4m3":
        bytes_per_block = config.state_block_size + 1
        key_row_bytes = _blocked_bytes(
            config.key_dim, config.state_block_size, bytes_per_block
        )
        update_row_bytes = _blocked_bytes(
            config.value_dim, config.state_block_size, bytes_per_block
        )
        log_vectors = capacity * (
            config.num_qk_heads * key_row_bytes
            + config.num_value_heads * update_row_bytes
        )
    elif log_precision == "mxfp4_rs2":
        bytes_per_block = config.state_block_size // 2 + 1
        key_row_bytes = 2 * _blocked_bytes(
            config.key_dim, config.state_block_size, bytes_per_block
        )
        update_row_bytes = 2 * _blocked_bytes(
            config.value_dim, config.state_block_size, bytes_per_block
        )
        log_vectors = capacity * (
            config.num_qk_heads * key_row_bytes
            + config.num_value_heads * update_row_bytes
        )
    elif log_precision in {"bf16", "fp16"}:
        log_vectors = capacity * 2 * (
            config.num_qk_heads * config.key_dim
            + config.num_value_heads * config.value_dim
        )
    elif log_precision == "fp32":
        log_vectors = capacity * 4 * (
            config.num_qk_heads * config.key_dim
            + config.num_value_heads * config.value_dim
        )
    else:
        raise ValueError(f"unknown log precision: {log_precision}")
    coefficient_bytes = 4 * (
        config.num_value_heads + capacity * config.num_value_heads
    )
    metadata_bytes = 16
    return base_bytes + log_vectors + coefficient_bytes + metadata_bytes


def _row(
    config: TraceConfiguration,
    *,
    token_index: int,
    variant: str,
    reference_output: np.ndarray,
    reference_state: np.ndarray,
    output: np.ndarray,
    state: np.ndarray,
    engine: LazyWriteLogGDN | None,
    state_bytes: int,
    initial_state_mode: str,
) -> dict[str, object]:
    output_metrics = _error_metrics(reference_output, output)
    state_metrics = _error_metrics(reference_state, state)
    counters = engine.counters if engine is not None else None
    return {
        "run_id": (
            f"synthetic_{config.seed:08x}_{config.trace_family}_{initial_state_mode}"
        ),
        "split": config.split,
        "seed": config.seed,
        "trace_family": config.trace_family,
        "variant": variant,
        "layer_id": 0,
        "token_index": token_index,
        "output_cosine_fp32": output_metrics["cosine"],
        "output_rel_l2": output_metrics["rel_l2"],
        "output_max_abs": output_metrics["max_abs"],
        "state_rel_l2": state_metrics["rel_l2"],
        "state_max_abs": state_metrics["max_abs"],
        "folds": 0 if counters is None else counters.folds,
        "coefficient_rebases": 0 if counters is None else counters.coefficient_rebases,
        "dropped_entries": 0 if counters is None else counters.dropped_entries,
        "live_entries": 0 if engine is None else engine.live_entries,
        "max_live_entries": 0 if counters is None else counters.max_live_entries,
        "logical_state_bytes": state_bytes,
        "event_metrics_status": "PASS",
    }


def _trace_initial_state(config: TraceConfiguration, mode: str) -> np.ndarray:
    if mode == "random":
        return _initial_state(config)
    if mode == "zero":
        return np.zeros(
            (config.num_value_heads, config.key_dim, config.value_dim),
            dtype=np.float32,
        )
    raise ValueError(f"unknown initial-state mode: {mode}")


def _trace_inputs(
    config: TraceConfiguration,
    token_index: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if config.trace_family not in {"decay_sweep", "adversarial"}:
        return _token_inputs(config, token_index)

    nominal = TraceConfiguration(
        **{**config.__dict__, "trace_family": "nominal"}
    )
    q, k, v, alpha, beta = _token_inputs(nominal, token_index)
    if config.trace_family == "decay_sweep":
        alpha_levels = np.array([0.0, 0.5, 0.9, 0.99, 0.999, 1.0], dtype=np.float32)
        beta_levels = np.array([0.0, 0.25, 0.5, 0.75, 1.0], dtype=np.float32)
        heads = np.arange(config.num_value_heads)
        alpha = alpha_levels[(heads + token_index) % alpha_levels.size]
        beta = beta_levels[(2 * heads + token_index) % beta_levels.size]
        return q, k, v, alpha, beta

    q.fill(0)
    k.fill(0)
    key_index = token_index % config.key_dim
    sign = np.float32(-1.0 if token_index & 1 else 1.0)
    q[:, key_index] = sign
    k[:, key_index] = sign
    exponent = (token_index // 16) % 9 - 4
    v = np.ldexp(np.sign(v) * np.float32(0.75), exponent).astype(np.float32)
    alpha.fill(np.float32(0.999))
    beta.fill(np.float32(1.0))
    return q, k, v, alpha, beta


def run_write_log_trace(
    config: TraceConfiguration,
    *,
    capacities: tuple[int, ...] = (4, 8, 16),
    log_precision: str = "mxfp8_e4m3",
    activation_stack_depth: int = 1,
    base_stack_depth: int = 1,
    fold_policy: str = "fixed",
    adaptive_min_entries: int = 1,
    fold_decay_threshold: float = 0.85,
    initial_state_mode: str = "random",
    base_residual_block_fraction: float = 1.0,
) -> WriteLogRunResult:
    if config.tokens <= 0:
        raise ValueError("tokens must be positive")
    if not capacities or any(capacity <= 0 for capacity in capacities):
        raise ValueError("capacities must be positive")
    if config.num_value_heads % config.num_qk_heads != 0:
        raise ValueError("num_value_heads must be divisible by num_qk_heads")

    initial_state = _trace_initial_state(config, initial_state_mode)
    reference_state = initial_state.copy()
    engines = {
        capacity: LazyWriteLogGDN(
            initial_state,
            num_qk_heads=config.num_qk_heads,
            config=WriteLogConfiguration(
                capacity=capacity,
                mode="mxfp4",
                activation_block_size=config.activation_block_size,
                base_block_size=config.state_block_size,
                log_block_size=config.state_block_size,
                log_precision=log_precision,
                activation_stack_depth=activation_stack_depth,
                base_stack_depth=base_stack_depth,
                fold_policy=fold_policy,
                adaptive_min_entries=adaptive_min_entries,
                fold_decay_threshold=fold_decay_threshold,
                base_residual_block_fraction=base_residual_block_fraction,
            ),
        )
        for capacity in capacities
    }
    state_bytes = {
        capacity: logical_state_bytes(
            config,
            capacity=capacity,
            log_precision=log_precision,
            base_stack_depth=base_stack_depth,
            base_residual_block_fraction=base_residual_block_fraction,
        )
        for capacity in capacities
    }
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
        alpha_quantized = decode_q1_15(encode_q1_15(alpha))
        beta_quantized = decode_q1_15(encode_q1_15(beta))
        for capacity, engine in engines.items():
            output, state = engine.step_core(
                q_quantized,
                k_quantized,
                v_quantized,
                alpha_quantized,
                beta_quantized,
            )
            row = _row(
                config,
                token_index=token_index,
                variant=_variant_name(
                    config,
                    capacity,
                    log_precision,
                    activation_stack_depth,
                    base_stack_depth,
                    fold_policy,
                    fold_decay_threshold,
                    base_residual_block_fraction,
                ),
                reference_output=reference_output,
                reference_state=reference_state,
                output=output,
                state=state,
                engine=engine,
                state_bytes=state_bytes[capacity],
                initial_state_mode=initial_state_mode,
            )
            token_rows.append(row)
            if token_index in checkpoint_set:
                checkpoint_rows.append(dict(row))

    checkpoint_rows.sort(key=lambda row: (int(row["token_index"]), str(row["variant"])))
    return WriteLogRunResult(
        token_rows=token_rows,
        checkpoint_rows=checkpoint_rows,
        config=config,
        capacities=capacities,
        log_precision=log_precision,
        activation_stack_depth=activation_stack_depth,
        base_stack_depth=base_stack_depth,
        fold_policy=fold_policy,
        adaptive_min_entries=adaptive_min_entries,
        fold_decay_threshold=fold_decay_threshold,
        initial_state_mode=initial_state_mode,
        base_residual_block_fraction=base_residual_block_fraction,
        input_stream_sha256=input_digest.hexdigest(),
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
    result: WriteLogRunResult,
    token_csv: Path,
    checkpoint_csv: Path,
) -> None:
    sources = [
        ROOT / "golden" / "gdn_fp32.py",
        ROOT / "golden" / "gdn_mxfp4.py",
        ROOT / "golden" / "gdn_write_log.py",
        ROOT / "golden" / "mx_format.py",
        ROOT / "scripts" / "long_sequence_stability.py",
        Path(__file__).resolve(),
    ]
    payload = {
        "schema": 1,
        "status": "diagnostic_only",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": result.config.__dict__,
        "capacities": result.capacities,
        "log_precision": result.log_precision,
        "activation_stack_depth": result.activation_stack_depth,
        "base_stack_depth": result.base_stack_depth,
        "fold_policy": result.fold_policy,
        "adaptive_min_entries": result.adaptive_min_entries,
        "fold_decay_threshold": result.fold_decay_threshold,
        "initial_state_mode": result.initial_state_mode,
        "base_residual_block_fraction": result.base_residual_block_fraction,
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
            "floating Q/DQ candidate, not the encoded-integer oracle",
            "logical storage bytes, not placed BRAM/URAM allocation",
            "not closed-loop Qwen quality evidence",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _passes_gate(rows: list[dict[str, object]], final_token: int) -> bool:
    candidate_rows = [row for row in rows if row["variant"] != "fp32"]
    final_rows = [row for row in candidate_rows if int(row["token_index"]) == final_token]
    return bool(final_rows) and all(
        float(row["output_cosine_fp32"]) >= 0.99 for row in candidate_rows
    ) and all(float(row["state_rel_l2"]) <= 0.10 for row in final_rows) and all(
        int(row["dropped_entries"]) == 0 for row in candidate_rows
    )


def write_report(
    path: Path,
    *,
    result: WriteLogRunResult,
    token_csv: Path,
    checkpoint_csv: Path,
    manifest: Path,
) -> None:
    config = result.config
    status = "PASS" if _passes_gate(result.checkpoint_rows, config.tokens) else "FAIL"
    lines = [
        "# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Engineering gate at executed length: `{status}`",
        f"Split/seed/family: `{config.split}` / `{hex(config.seed)}` / `{config.trace_family}`",
        f"Initial state: `{result.initial_state_mode}`",
        f"Base residual-block fraction: {result.base_residual_block_fraction}",
        f"Tokens/checkpoints: {config.tokens} / {', '.join(map(str, config.checkpoints))}",
        (
            "Residual-stack depths (activation/base): "
            f"{result.activation_stack_depth}/{result.base_stack_depth}"
        ),
        (
            "Fold policy: "
            f"{result.fold_policy}, minimum entries={result.adaptive_min_entries}, "
            f"decay threshold={result.fold_decay_threshold}"
        ),
        f"Input-stream SHA256: `{result.input_stream_sha256}`",
        f"Token CSV: `{token_csv.relative_to(ROOT).as_posix()}`",
        f"Checkpoint CSV: `{checkpoint_csv.relative_to(ROOT).as_posix()}`",
        f"Manifest: `{manifest.relative_to(ROOT).as_posix()}`",
        "",
        "The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.",
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
            "This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.",
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
    parser.add_argument("--tokens", type=int, default=8192)
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
        default="nominal",
    )
    parser.add_argument("--capacities", nargs="+", type=int, default=[4, 8, 16])
    parser.add_argument(
        "--log-precision",
        choices=["mxfp8_e4m3", "mxfp4_rs2", "bf16", "fp16", "fp32"],
        default="mxfp8_e4m3",
    )
    parser.add_argument("--activation-stack-depth", type=int, default=1)
    parser.add_argument("--base-stack-depth", type=int, default=1)
    parser.add_argument(
        "--fold-policy", choices=["fixed", "decay_threshold"], default="fixed"
    )
    parser.add_argument("--adaptive-min-entries", type=int, default=1)
    parser.add_argument("--fold-decay-threshold", type=float, default=0.85)
    parser.add_argument(
        "--initial-state", choices=["random", "zero"], default="random"
    )
    parser.add_argument("--base-residual-block-fraction", type=float, default=1.0)
    parser.add_argument("--num-value-heads", type=int, default=DEFAULT_NUM_VALUE_HEADS)
    parser.add_argument("--num-qk-heads", type=int, default=DEFAULT_NUM_QK_HEADS)
    parser.add_argument("--key-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--value-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--activation-block-size", type=int, choices=[16, 32], default=32)
    parser.add_argument("--state-block-size", type=int, choices=[16, 32], default=32)
    parser.add_argument("--token-csv", type=Path, default=DEFAULT_TOKEN_CSV)
    parser.add_argument("--checkpoint-csv", type=Path, default=DEFAULT_CHECKPOINT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
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
    result = run_write_log_trace(
        config,
        capacities=tuple(sorted(set(args.capacities))),
        log_precision=args.log_precision,
        activation_stack_depth=args.activation_stack_depth,
        base_stack_depth=args.base_stack_depth,
        fold_policy=args.fold_policy,
        adaptive_min_entries=args.adaptive_min_entries,
        fold_decay_threshold=args.fold_decay_threshold,
        initial_state_mode=args.initial_state,
        base_residual_block_fraction=args.base_residual_block_fraction,
    )
    token_csv = _resolve(args.token_csv)
    checkpoint_csv = _resolve(args.checkpoint_csv)
    report = _resolve(args.report)
    manifest = _resolve(args.manifest)
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
    print(report.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

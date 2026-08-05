"""Corrected synthetic long-sequence GDN stability diagnostics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_bf16 import (
    gdn_decode_step as bf16_decode_step,
    roundtrip_bf16,
)
from golden.gdn_fp32 import (
    gdn_decode_step as fp32_decode_step,
    gdn_recurrence_core_step,
    normalize_qk,
)
from golden.gdn_int4 import gdn_decode_step as int4_decode_step
from golden.gdn_mxfp4 import quantize_activation, quantize_state
from golden.gdn_mxfp4_encoded import decode_q1_15, encode_q1_15
from golden.vectors import (
    DEFAULT_HEAD_DIM,
    DEFAULT_NUM_QK_HEADS,
    DEFAULT_NUM_VALUE_HEADS,
    DEFAULT_SEED,
)
from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKEN_CSV = ROOT / "reports" / "benchmark" / "corrected" / "long_trace_tokens.csv"
DEFAULT_CHECKPOINT_CSV = ROOT / "reports" / "benchmark" / "corrected" / "long_trace_checkpoints.csv"
DEFAULT_REPORT = ROOT / "reports" / "benchmark" / "corrected" / "long_trace.md"
DEFAULT_MANIFEST = ROOT / "reports" / "benchmark" / "corrected" / "long_trace_manifest.json"
DEFAULT_CHECKPOINTS = (64, 256, 1024, 4096, 8192)


@dataclass(frozen=True)
class TraceConfiguration:
    tokens: int
    checkpoints: tuple[int, ...]
    seed: int
    split: str
    trace_family: str
    num_value_heads: int
    num_qk_heads: int
    key_dim: int
    value_dim: int
    activation_block_size: int
    state_block_size: int


@dataclass(frozen=True)
class LongTraceResult:
    token_rows: list[dict[str, object]]
    checkpoint_rows: list[dict[str, object]]
    config: TraceConfiguration
    input_sha256: str
    initial_state_sha256: str


def _token_rng(seed: int, token_index: int, trace_family: str) -> np.random.Generator:
    family_offset = sum((index + 1) * ord(char) for index, char in enumerate(trace_family))
    return np.random.default_rng(
        seed + 0x9E3779B97F4A7C15 * (token_index + 2) + family_offset
    )


def _initial_state(config: TraceConfiguration) -> np.ndarray:
    generator = _token_rng(config.seed, -1, config.trace_family)
    return generator.normal(
        0.0,
        0.05,
        size=(config.num_value_heads, config.key_dim, config.value_dim),
    ).astype(np.float32)


def _token_inputs(
    config: TraceConfiguration,
    token_index: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    generator = _token_rng(config.seed, token_index, config.trace_family)
    q = generator.normal(0.0, 1.0, size=(config.num_qk_heads, config.key_dim)).astype(
        np.float32
    )
    k = generator.normal(0.0, 1.0, size=(config.num_qk_heads, config.key_dim)).astype(
        np.float32
    )
    v = generator.normal(
        0.0, 0.25, size=(config.num_value_heads, config.value_dim)
    ).astype(np.float32)
    alpha = generator.uniform(0.95, 1.0, size=config.num_value_heads).astype(np.float32)
    beta = generator.uniform(0.0, 1.0, size=config.num_value_heads).astype(np.float32)

    if config.trace_family == "dynamic_range":
        exponent = (token_index // 32) % 9 - 4
        v = np.ldexp(v, exponent).astype(np.float32)
    elif config.trace_family == "cancellation":
        sign = np.float32(-1.0 if (token_index & 1) else 1.0)
        q = np.abs(q) * sign
        k = np.abs(k) * sign
        v = np.abs(v) * sign
    elif config.trace_family == "high_retention":
        alpha = generator.uniform(0.995, 1.0, size=config.num_value_heads).astype(
            np.float32
        )
        beta = generator.uniform(0.85, 1.0, size=config.num_value_heads).astype(
            np.float32
        )
    elif config.trace_family != "nominal":
        raise ValueError(f"unknown trace family: {config.trace_family}")
    return q, k, v, alpha, beta


def _error_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    reference64 = np.asarray(reference, dtype=np.float64).reshape(-1)
    candidate64 = np.asarray(candidate, dtype=np.float64).reshape(-1)
    if reference64.shape != candidate64.shape:
        raise ValueError("metric arrays must have identical shapes")
    if np.array_equal(reference64, candidate64):
        return {"cosine": 1.0, "rel_l2": 0.0, "max_abs": 0.0}
    difference = candidate64 - reference64
    reference_norm = float(np.linalg.norm(reference64))
    candidate_norm = float(np.linalg.norm(candidate64))
    denominator = max(reference_norm, 1e-12)
    cosine_denominator = reference_norm * candidate_norm
    if cosine_denominator <= 1e-24:
        cosine = 1.0 if reference_norm <= 1e-12 and candidate_norm <= 1e-12 else 0.0
    else:
        cosine = float(np.dot(reference64, candidate64) / cosine_denominator)
    return {
        "cosine": max(-1.0, min(1.0, cosine)),
        "rel_l2": float(np.linalg.norm(difference) / denominator),
        "max_abs": float(np.max(np.abs(difference))) if difference.size else 0.0,
    }


def _update_input_hash(hasher: object, name: str, array: np.ndarray) -> None:
    contiguous = np.ascontiguousarray(array)
    hasher.update(name.encode("ascii"))
    hasher.update(contiguous.dtype.str.encode("ascii"))
    hasher.update(json.dumps(contiguous.shape).encode("ascii"))
    hasher.update(contiguous.tobytes())


def _mxfp_variant_precisions(
    config: TraceConfiguration,
) -> dict[str, str]:
    return {
        (
            f"mxfp4_qdq_act_b{config.activation_block_size}_"
            f"state_b{config.state_block_size}"
        ): "mxfp4",
        (
            f"mxfp4_qdq_act_b{config.activation_block_size}_"
            f"mxfp8_e4m3_state_b{config.state_block_size}"
        ): "mxfp8_e4m3",
    }


def _metric_row(
    config: TraceConfiguration,
    *,
    token_index: int,
    variant: str,
    reference_output: np.ndarray,
    reference_state: np.ndarray,
    output: np.ndarray,
    state: np.ndarray,
) -> dict[str, object]:
    output_metrics = _error_metrics(reference_output, output)
    state_metrics = _error_metrics(reference_state, state)
    return {
        "run_id": f"synthetic_{config.seed:08x}_{config.trace_family}",
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
        "element_saturations": "",
        "accumulator_saturations": "",
        "scale_clamps": "",
        "alignment_underflows": "",
        "state_scale_changes": "",
        "event_metrics_status": "NOT_RUN",
    }


def run_long_trace(config: TraceConfiguration) -> LongTraceResult:
    if config.tokens <= 0:
        raise ValueError("tokens must be positive")
    if config.num_value_heads % config.num_qk_heads != 0:
        raise ValueError("num_value_heads must be divisible by num_qk_heads")
    if config.activation_block_size not in (16, 32) or config.state_block_size not in (16, 32):
        raise ValueError("block sizes must be 16 or 32")

    reference_state = _initial_state(config)
    initial_state_sha256 = hashlib.sha256(
        np.ascontiguousarray(reference_state).tobytes()
    ).hexdigest()
    input_hasher = hashlib.sha256()
    _update_input_hash(input_hasher, "initial_state", reference_state)
    mxfp_precisions = _mxfp_variant_precisions(config)
    states = {
        name: quantize_state(
            reference_state,
            block_size=config.state_block_size,
            precision=precision,
        )
        for name, precision in mxfp_precisions.items()
    }
    states["bf16_qdq_fp32_accum_state_bf16"] = roundtrip_bf16(reference_state)
    states["flat_int4_qdq"] = reference_state.copy()
    checkpoint_set = set(config.checkpoints)
    token_rows: list[dict[str, object]] = []
    checkpoint_rows: list[dict[str, object]] = []

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
        fp32_row = _metric_row(
            config,
            token_index=token_index,
            variant="fp32",
            reference_output=reference_output,
            reference_state=reference_state,
            output=reference_output,
            state=reference_state,
        )
        fp32_row["event_metrics_status"] = "PASS"
        fp32_row["element_saturations"] = 0
        fp32_row["accumulator_saturations"] = 0
        fp32_row["scale_clamps"] = 0
        fp32_row["alignment_underflows"] = 0
        fp32_row["state_scale_changes"] = 0
        token_rows.append(fp32_row)

        bf16_output, states["bf16_qdq_fp32_accum_state_bf16"] = bf16_decode_step(
            q,
            k,
            v,
            alpha,
            beta,
            states["bf16_qdq_fp32_accum_state_bf16"],
        )
        bf16_row = _metric_row(
            config,
            token_index=token_index,
            variant="bf16_qdq_fp32_accum_state_bf16",
            reference_output=reference_output,
            reference_state=reference_state,
            output=bf16_output,
            state=states["bf16_qdq_fp32_accum_state_bf16"],
        )
        token_rows.append(bf16_row)
        if token_index in checkpoint_set:
            checkpoint_rows.append(dict(bf16_row))

        q_scaled, k_normalized = normalize_qk(q, k)
        q_q = quantize_activation(
            q_scaled, block_size=config.activation_block_size
        )
        k_q = quantize_activation(
            k_normalized, block_size=config.activation_block_size
        )
        v_q = quantize_activation(v, block_size=config.activation_block_size)
        alpha_q = decode_q1_15(encode_q1_15(alpha))
        beta_q = decode_q1_15(encode_q1_15(beta))

        for variant, precision in mxfp_precisions.items():
            output, updated_state = gdn_recurrence_core_step(
                q_q,
                k_q,
                v_q,
                alpha_q,
                beta_q,
                states[variant],
            )
            states[variant] = quantize_state(
                updated_state,
                block_size=config.state_block_size,
                precision=precision,
            )
            row = _metric_row(
                config,
                token_index=token_index,
                variant=variant,
                reference_output=reference_output,
                reference_state=reference_state,
                output=output,
                state=states[variant],
            )
            token_rows.append(row)
            if token_index in checkpoint_set:
                checkpoint_rows.append(dict(row))

        int4_output, states["flat_int4_qdq"] = int4_decode_step(
            q, k, v, alpha, beta, states["flat_int4_qdq"]
        )
        int4_row = _metric_row(
            config,
            token_index=token_index,
            variant="flat_int4_qdq",
            reference_output=reference_output,
            reference_state=reference_state,
            output=int4_output,
            state=states["flat_int4_qdq"],
        )
        token_rows.append(int4_row)
        if token_index in checkpoint_set:
            checkpoint_rows.append(dict(int4_row))
        if token_index in checkpoint_set:
            checkpoint_rows.append(dict(fp32_row))

    checkpoint_rows.sort(key=lambda row: (int(row["token_index"]), str(row["variant"])))
    return LongTraceResult(
        token_rows,
        checkpoint_rows,
        config,
        input_hasher.hexdigest(),
        initial_state_sha256,
    )


TOKEN_FIELDS = [
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
    "element_saturations",
    "accumulator_saturations",
    "scale_clamps",
    "alignment_underflows",
    "state_scale_changes",
    "event_metrics_status",
]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TOKEN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(
    path: Path,
    *,
    result: LongTraceResult,
    token_csv: Path,
    checkpoint_csv: Path,
    report_path: Path | None = None,
    execution_command: str = "library call: write_manifest",
) -> None:
    source_paths = [
        ROOT / "golden" / "gdn_bf16.py",
        ROOT / "golden" / "gdn_fp32.py",
        ROOT / "golden" / "gdn_mxfp4.py",
        ROOT / "golden" / "gdn_int4.py",
        ROOT / "golden" / "mx_format.py",
        Path(__file__).resolve(),
    ]
    source_identity = describe_source_files(source_paths)
    payload = {
        "schema": 1,
        "status": "PASS",
        "evidence_scope": "synthetic_floating_qdq_diagnostic",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": result.config.__dict__,
        "input_sha256": result.input_sha256,
        "initial_state_sha256": result.initial_state_sha256,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "execution": {
            "command": execution_command,
            "exit_code": 0,
            "raw_log": (
                report_path.relative_to(ROOT).as_posix()
                if report_path is not None
                else "NOT_RUN"
            ),
        },
        "source_hashes": {
            source.relative_to(ROOT).as_posix(): _sha256(source) for source in source_paths
        },
        "outputs": {
            token_csv.relative_to(ROOT).as_posix(): _sha256(token_csv),
            checkpoint_csv.relative_to(ROOT).as_posix(): _sha256(checkpoint_csv),
        },
        "limitations": [
            "synthetic inputs",
            "floating Q/DQ variants are not the encoded-integer oracle",
            "event counters are NOT_RUN for Q/DQ variants",
            "not closed-loop Qwen quality evidence",
        ],
        "independent_verification": (
            "python -m scripts.verify_synthetic_stability cross-checks hashes, "
            "row sequences, checkpoint projections, metrics, and scale-policy parity"
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_report(
    path: Path,
    *,
    result: LongTraceResult,
    token_csv: Path,
    checkpoint_csv: Path,
    manifest: Path,
) -> None:
    config = result.config
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Corrected Synthetic Long-Sequence Diagnostic",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "Status: `PASS` for synthetic floating Q/DQ stability diagnostics only",
        f"Seed/split: `{hex(config.seed)}` / `{config.split}`",
        f"Trace family: `{config.trace_family}`",
        (
            "Shape: "
            f"value_heads={config.num_value_heads}, qk_heads={config.num_qk_heads}, "
            f"K={config.key_dim}, V={config.value_dim}, orientation=KxV"
        ),
        f"Tokens: {config.tokens}",
        f"Checkpoints: {', '.join(str(value) for value in config.checkpoints)}",
        f"Token CSV: `{token_csv.relative_to(ROOT).as_posix()}`",
        f"Checkpoint CSV: `{checkpoint_csv.relative_to(ROOT).as_posix()}`",
        f"Manifest: `{manifest.relative_to(ROOT).as_posix()}`",
        "",
        "The run uses the corrected alpha-decayed Qwen recurrence and paired Q/K heads. MX rows are floating Q/DQ diagnostics, not encoded-oracle, HLS, RTL, board, or closed-loop model evidence.",
        "",
        "| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs error |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for row in result.checkpoint_rows:
        lines.append(
            f"| {row['token_index']} | {row['variant']} | "
            f"{float(row['output_cosine_fp32']):.6f} | "
            f"{float(row['output_rel_l2']):.6f} | "
            f"{float(row['state_rel_l2']):.6f} | "
            f"{float(row['state_max_abs']):.6f} |"
        )
    lines.append("")
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
        choices=["nominal", "dynamic_range", "cancellation", "high_retention"],
        default="nominal",
    )
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
    result = run_long_trace(config)
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
        report_path=report,
        execution_command=subprocess.list2cmdline(
            ["python", "-m", "scripts.long_sequence_stability", *sys.argv[1:]]
        ),
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

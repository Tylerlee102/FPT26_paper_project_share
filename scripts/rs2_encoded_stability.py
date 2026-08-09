"""Run the frozen-width encoded two-term MXFP4 stability experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_e2m0_encoded import ACCUMULATOR_BITS, ACCUMULATOR_GUARD_BITS
from golden.gdn_fp32 import gdn_recurrence_core_step, normalize_qk
from golden.gdn_mxfp4_encoded import ArithmeticCounters
from golden.gdn_rs2_encoded import encode_rs2_state, encode_rs2_token
from golden.gdn_rs2_encoded_vectorized import EncodedRS2WriteLogGDNVectorized
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
)
from scripts.write_log_stability import _trace_initial_state, _trace_inputs


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "reports" / "benchmark" / "corrected" / "rs2_encoded"
CAPACITY = 3
VARIANT = "mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5"
OUTPUT_COSINE_MINIMUM = 0.99
STATE_RELATIVE_L2_MAXIMUM = 0.10

COUNTER_FIELDS = (
    "element_saturations",
    "accumulator_saturations",
    "scale_clamps",
    "alignment_underflows",
    "state_scale_changes",
)
FIELDS = [
    "run_id",
    "split",
    "seed",
    "trace_family",
    "initial_state_mode",
    "variant",
    "token_index",
    "output_cosine_fp32",
    "output_rel_l2",
    "output_max_abs",
    "state_rel_l2",
    "state_max_abs",
    *COUNTER_FIELDS,
    *(f"cumulative_{name}" for name in COUNTER_FIELDS),
    "folded",
    "folds",
    "live_entries",
    "logical_state_bytes",
    "event_metrics_status",
]


@dataclass(frozen=True)
class EncodedRS2RunResult:
    token_rows: list[dict[str, object]]
    checkpoint_rows: list[dict[str, object]]
    config: TraceConfiguration
    initial_state_mode: str
    input_stream_sha256: str
    logical_state_bytes: int
    gate_pass: bool
    gate_metrics: dict[str, float | int]


def logical_encoded_state_bytes(config: TraceConfiguration) -> int:
    """Return fixed-layout bytes for two E2M1 terms and a two-entry log."""

    if config.activation_block_size != 32 or config.state_block_size != 32:
        raise ValueError("the encoded candidate is fixed to OCP B32")
    rows = config.num_value_heads * config.key_dim
    blocks_per_state_row = (config.value_dim + 31) // 32
    # Each E2M1 B32 term uses 16 packed element bytes plus one E8M0 byte.
    base_bytes = rows * blocks_per_state_row * (17 * 2)
    qk_blocks = (config.key_dim + 31) // 32
    value_blocks = (config.value_dim + 31) // 32
    log_bytes = CAPACITY * (
        config.num_qk_heads * qk_blocks * (17 * 2)
        + config.num_value_heads * value_blocks * (17 * 2)
    )
    coefficient_bytes = 2 * (
        config.num_value_heads + CAPACITY * config.num_value_heads
    )
    return base_bytes + log_bytes + coefficient_bytes + 16


def _row(
    config: TraceConfiguration,
    *,
    initial_state_mode: str,
    token_index: int,
    variant: str,
    reference_output: np.ndarray,
    reference_state: np.ndarray,
    output: np.ndarray,
    state: np.ndarray,
    counters: dict[str, int],
    cumulative: dict[str, int],
    folded: bool,
    folds: int,
    live_entries: int,
    logical_state_bytes: int,
) -> dict[str, object]:
    output_metrics = _error_metrics(reference_output, output)
    state_metrics = _error_metrics(reference_state, state)
    row: dict[str, object] = {
        "run_id": (
            f"synthetic_{config.seed:08x}_{config.trace_family}_{initial_state_mode}"
        ),
        "split": config.split,
        "seed": config.seed,
        "trace_family": config.trace_family,
        "initial_state_mode": initial_state_mode,
        "variant": variant,
        "token_index": token_index,
        "output_cosine_fp32": output_metrics["cosine"],
        "output_rel_l2": output_metrics["rel_l2"],
        "output_max_abs": output_metrics["max_abs"],
        "state_rel_l2": state_metrics["rel_l2"],
        "state_max_abs": state_metrics["max_abs"],
        "folded": int(folded),
        "folds": folds,
        "live_entries": live_entries,
        "logical_state_bytes": logical_state_bytes,
        "event_metrics_status": "PASS",
    }
    for name in COUNTER_FIELDS:
        row[name] = counters[name]
        row[f"cumulative_{name}"] = cumulative[name]
    return row


def _derive_gate(
    candidate_rows: list[dict[str, object]], cumulative: dict[str, int]
) -> tuple[bool, dict[str, float | int]]:
    if not candidate_rows:
        return False, {
            "all_token_output_cosine_min": float("nan"),
            "all_token_state_relative_l2_max": float("nan"),
        }
    minimum_cosine = min(float(row["output_cosine_fp32"]) for row in candidate_rows)
    maximum_state_error = max(float(row["state_rel_l2"]) for row in candidate_rows)
    metrics: dict[str, float | int] = {
        "all_token_output_cosine_min": minimum_cosine,
        "all_token_state_relative_l2_max": maximum_state_error,
        "final_output_cosine": float(candidate_rows[-1]["output_cosine_fp32"]),
        "final_state_relative_l2": float(candidate_rows[-1]["state_rel_l2"]),
        **{f"cumulative_{name}": int(cumulative[name]) for name in COUNTER_FIELDS},
    }
    gate_pass = (
        minimum_cosine >= OUTPUT_COSINE_MINIMUM
        and maximum_state_error <= STATE_RELATIVE_L2_MAXIMUM
        and cumulative["element_saturations"] == 0
        and cumulative["accumulator_saturations"] == 0
        and cumulative["scale_clamps"] == 0
    )
    return gate_pass, metrics


def run_encoded_trace(
    config: TraceConfiguration,
    *,
    initial_state_mode: str,
) -> EncodedRS2RunResult:
    if config.tokens <= 0:
        raise ValueError("tokens must be positive")
    if config.activation_block_size != 32 or config.state_block_size != 32:
        raise ValueError("the encoded candidate requires B32 tokens and state")
    if config.num_value_heads % config.num_qk_heads:
        raise ValueError("value heads must be divisible by q/k heads")

    initial = _trace_initial_state(config, initial_state_mode)
    reference_state = initial.copy()
    engine = EncodedRS2WriteLogGDNVectorized(
        encode_rs2_state(initial, block_size=32),
        num_qk_heads=config.num_qk_heads,
        capacity=CAPACITY,
    )
    logical_bytes = logical_encoded_state_bytes(config)
    fp32_bytes = config.num_value_heads * config.key_dim * config.value_dim * 4
    checkpoint_set = set(config.checkpoints)
    token_rows: list[dict[str, object]] = []
    checkpoint_rows: list[dict[str, object]] = []
    cumulative = ArithmeticCounters().as_dict()
    folds = 0
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(initial).tobytes())

    for token_zero_based in range(config.tokens):
        token_index = token_zero_based + 1
        q, k, v, alpha, beta = _trace_inputs(config, token_zero_based)
        for array in (q, k, v, alpha, beta):
            digest.update(np.ascontiguousarray(array).tobytes())
        q_scaled, k_normalized = normalize_qk(q, k)
        reference_output, reference_state = gdn_recurrence_core_step(
            q_scaled, k_normalized, v, alpha, beta, reference_state
        )
        zero_counters = ArithmeticCounters().as_dict()
        fp32_row = _row(
            config,
            initial_state_mode=initial_state_mode,
            token_index=token_index,
            variant="fp32",
            reference_output=reference_output,
            reference_state=reference_state,
            output=reference_output,
            state=reference_state,
            counters=zero_counters,
            cumulative=zero_counters,
            folded=False,
            folds=0,
            live_entries=0,
            logical_state_bytes=fp32_bytes,
        )
        token_rows.append(fp32_row)

        encoded = encode_rs2_token(
            q_scaled,
            k_normalized,
            v,
            alpha,
            beta,
            block_size=32,
        )
        result = engine.step(encoded)
        command_counters = result.counters.as_dict()
        for name, value in command_counters.items():
            cumulative[name] += int(value)
        folds += int(result.folded)
        candidate_row = _row(
            config,
            initial_state_mode=initial_state_mode,
            token_index=token_index,
            variant=VARIANT,
            reference_output=reference_output,
            reference_state=reference_state,
            output=result.output_fp32,
            state=result.materialized_state_fp32,
            counters=command_counters,
            cumulative=cumulative,
            folded=result.folded,
            folds=folds,
            live_entries=result.live_entries,
            logical_state_bytes=logical_bytes,
        )
        token_rows.append(candidate_row)
        if token_index in checkpoint_set:
            checkpoint_rows.extend((dict(fp32_row), dict(candidate_row)))

    candidate_rows = [row for row in token_rows if row["variant"] == VARIANT]
    gate_pass, gate_metrics = _derive_gate(candidate_rows, cumulative)
    return EncodedRS2RunResult(
        token_rows,
        checkpoint_rows,
        config,
        initial_state_mode,
        digest.hexdigest(),
        logical_bytes,
        gate_pass,
        gate_metrics,
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_manifest(
    path: Path,
    *,
    result: EncodedRS2RunResult,
    token_csv: Path,
    checkpoint_csv: Path,
    raw_log: Path,
    command: str,
) -> None:
    sources = [
        ROOT / "golden" / "gdn_rs2_encoded.py",
        ROOT / "golden" / "gdn_rs2_encoded_vectorized.py",
        ROOT / "golden" / "gdn_e2m0_encoded.py",
        ROOT / "golden" / "gdn_e2m0_encoded_vectorized.py",
        ROOT / "golden" / "gdn_mxfp4_encoded.py",
        ROOT / "golden" / "gdn_mxfp4_encoded_vectorized.py",
        ROOT / "golden" / "gdn_fp32.py",
        Path(__file__).resolve(),
    ]
    source_identity = describe_source_files(sources)
    payload = {
        "schema": 1,
        "status": "PASS" if result.gate_pass else "FAIL",
        "evidence_scope": "encoded_integer_synthetic_stability",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "variant": VARIANT,
        "configuration": result.config.__dict__,
        "initial_state_mode": result.initial_state_mode,
        "input_stream_sha256": result.input_stream_sha256.upper(),
        "logical_state_bytes": result.logical_state_bytes,
        "arithmetic_contract": {
            "accumulator_bits": ACCUMULATOR_BITS,
            "alignment_guard_bits": ACCUMULATOR_GUARD_BITS,
            "coefficient_format": "Q1.15",
            "state": "two E2M1/E8M0 B32 terms",
            "token_and_log": "two E2M1/E8M0 B32 terms",
            "capacity": CAPACITY,
            "fold_policy": "fixed all-head atomic at capacity",
        },
        "gate": {
            "scope": "every token in the trace",
            "output_cosine_minimum": OUTPUT_COSINE_MINIMUM,
            "state_relative_l2_maximum": STATE_RELATIVE_L2_MAXIMUM,
            "element_saturations_required": 0,
            "accumulator_saturations_required": 0,
            "scale_clamps_required": 0,
            "metrics": result.gate_metrics,
            "gate_pass": result.gate_pass,
        },
        "python": platform.python_version(),
        "numpy": np.__version__,
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "source_sha256": {
            source.relative_to(ROOT).as_posix(): _sha256(source) for source in sources
        },
        "outputs": {
            token_csv.relative_to(ROOT).as_posix(): _sha256(token_csv),
            checkpoint_csv.relative_to(ROOT).as_posix(): _sha256(checkpoint_csv),
            raw_log.relative_to(ROOT).as_posix(): _sha256(raw_log),
        },
        "execution": {"command": command, "exit_code": 0},
        "limitations": [
            "layer-level deterministic synthetic traces only",
            "vectorized executor is software, not HLS C simulation or RTL",
            "closed-loop Qwen quality, placement, routing, board parity, and energy are NOT_RUN",
        ],
        "independent_verification": "python -m scripts.verify_rs2_encoded_stability",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=int, default=1024)
    parser.add_argument("--checkpoint", action="append")
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--split", default="development")
    parser.add_argument("--trace-family", default="high_retention")
    parser.add_argument("--initial-state", choices=("random", "zero"), default="random")
    parser.add_argument("--num-value-heads", type=int, default=DEFAULT_NUM_VALUE_HEADS)
    parser.add_argument("--num-qk-heads", type=int, default=DEFAULT_NUM_QK_HEADS)
    parser.add_argument("--key-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--value-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR / "development")
    args = parser.parse_args(argv)
    checkpoints = tuple(
        sorted(
            {
                int(value, 0)
                for value in (args.checkpoint or [str(v) for v in DEFAULT_CHECKPOINTS])
                if 1 <= int(value, 0) <= args.tokens
            }
            | {args.tokens}
        )
    )
    config = TraceConfiguration(
        tokens=args.tokens,
        checkpoints=checkpoints,
        seed=args.seed,
        split=args.split,
        trace_family=args.trace_family,
        num_value_heads=args.num_value_heads,
        num_qk_heads=args.num_qk_heads,
        key_dim=args.key_dim,
        value_dim=args.value_dim,
        activation_block_size=32,
        state_block_size=32,
    )
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    stem = f"{args.trace_family}_{args.seed:08x}_{args.initial_state}_{args.tokens}"
    token_csv = output_dir / f"{stem}_tokens.csv"
    checkpoint_csv = output_dir / f"{stem}_checkpoints.csv"
    manifest = output_dir / f"{stem}_manifest.json"
    raw_log = output_dir / f"{stem}.log"
    command = " ".join(
        [sys.executable, "-m", "scripts.rs2_encoded_stability", *(argv or sys.argv[1:])]
    )
    result = run_encoded_trace(config, initial_state_mode=args.initial_state)
    write_csv(token_csv, result.token_rows)
    write_csv(checkpoint_csv, result.checkpoint_rows)
    raw_log.parent.mkdir(parents=True, exist_ok=True)
    raw_log.write_text(
        json.dumps(
            {
                "status": "PASS" if result.gate_pass else "FAIL",
                "tokens": config.tokens,
                "rows": len(result.token_rows),
                "gate_pass": result.gate_pass,
                "gate_metrics": result.gate_metrics,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_manifest(
        manifest,
        result=result,
        token_csv=token_csv,
        checkpoint_csv=checkpoint_csv,
        raw_log=raw_log,
        command=command,
    )
    print(
        json.dumps(
            {
                "status": "PASS" if result.gate_pass else "FAIL",
                "manifest": manifest.relative_to(ROOT).as_posix(),
                "logical_state_bytes": result.logical_state_bytes,
                "gate_metrics": result.gate_metrics,
            },
            sort_keys=True,
        )
    )
    return 0 if result.gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

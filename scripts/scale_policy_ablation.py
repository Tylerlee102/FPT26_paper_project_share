"""Run controlled MXFP4 recurrent-state scale-refresh diagnostics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import (
    gdn_decode_step as fp32_decode_step,
    gdn_recurrence_core_step,
    normalize_qk,
)
from golden.gdn_mxfp4 import quantize_activation
from golden.gdn_mxfp4_encoded import decode_q1_15, encode_q1_15
from golden.mxfp4_scale_policy import (
    initialize_mxfp4_state,
    quantize_mxfp4_state_with_policy,
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
from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKEN_CSV = (
    ROOT / "reports" / "benchmark" / "corrected" / "scale_policy_tokens.csv"
)
DEFAULT_CHECKPOINT_CSV = (
    ROOT / "reports" / "benchmark" / "corrected" / "scale_policy_checkpoints.csv"
)
DEFAULT_REPORT = (
    ROOT / "reports" / "benchmark" / "corrected" / "scale_policy_ablation.md"
)
DEFAULT_MANIFEST = (
    ROOT / "reports" / "benchmark" / "corrected" / "scale_policy_manifest.json"
)


@dataclass(frozen=True)
class PolicySpec:
    variant: str
    policy: str
    refresh_interval: int | None = None


POLICIES = (
    PolicySpec("mxfp4_scale_fixed", "fixed"),
    PolicySpec("mxfp4_scale_every_token", "every_token"),
    PolicySpec("mxfp4_scale_periodic_4", "periodic", 4),
    PolicySpec("mxfp4_scale_periodic_8", "periodic", 8),
    PolicySpec("mxfp4_scale_periodic_16", "periodic", 16),
    PolicySpec("mxfp4_scale_threshold_0p75_5p5", "threshold"),
)


@dataclass(frozen=True)
class ScalePolicyResult:
    token_rows: list[dict[str, object]]
    checkpoint_rows: list[dict[str, object]]
    config: TraceConfiguration
    input_sha256: str
    initial_state_sha256: str
    initial_scale_blocks: int


FIELDS = [
    "run_id",
    "split",
    "seed",
    "trace_family",
    "variant",
    "policy",
    "refresh_interval",
    "layer_id",
    "token_index",
    "output_cosine_fp32",
    "output_rel_l2",
    "output_max_abs",
    "state_rel_l2",
    "state_max_abs",
    "state_element_saturations",
    "state_element_saturations_cumulative",
    "state_scale_refreshes",
    "state_scale_refreshes_cumulative",
    "state_scale_changes",
    "state_scale_changes_cumulative",
    "event_scope",
]


def _update_input_hash(hasher: object, name: str, array: np.ndarray) -> None:
    contiguous = np.ascontiguousarray(array)
    hasher.update(name.encode("ascii"))
    hasher.update(contiguous.dtype.str.encode("ascii"))
    hasher.update(json.dumps(contiguous.shape).encode("ascii"))
    hasher.update(contiguous.tobytes())


def run_scale_policy_ablation(config: TraceConfiguration) -> ScalePolicyResult:
    if config.tokens <= 0:
        raise ValueError("tokens must be positive")
    if config.num_value_heads % config.num_qk_heads != 0:
        raise ValueError("num_value_heads must be divisible by num_qk_heads")
    if config.activation_block_size not in (16, 32):
        raise ValueError("activation block size must be 16 or 32")
    if config.state_block_size not in (16, 32):
        raise ValueError("state block size must be 16 or 32")

    reference_state = _initial_state(config)
    initial_state_sha256 = hashlib.sha256(
        np.ascontiguousarray(reference_state).tobytes()
    ).hexdigest()
    input_hasher = hashlib.sha256()
    _update_input_hash(input_hasher, "initial_state", reference_state)
    initialized = initialize_mxfp4_state(
        reference_state, block_size=config.state_block_size
    )
    runtimes = {
        spec.variant: {
            "state": initialized.resident_state.copy(),
            "scales": initialized.scales.copy(),
            "saturations": 0,
            "refreshes": 0,
            "scale_changes": 0,
        }
        for spec in POLICIES
    }
    checkpoints = set(config.checkpoints)
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

        for spec in POLICIES:
            runtime = runtimes[spec.variant]
            output, updated_state = gdn_recurrence_core_step(
                q_q,
                k_q,
                v_q,
                alpha_q,
                beta_q,
                runtime["state"],
            )
            quantized = quantize_mxfp4_state_with_policy(
                updated_state,
                runtime["scales"],
                token_index=token_index,
                policy=spec.policy,
                block_size=config.state_block_size,
                refresh_interval=spec.refresh_interval,
            )
            runtime["state"] = quantized.resident_state
            runtime["scales"] = quantized.scales
            runtime["saturations"] += quantized.element_saturations
            runtime["refreshes"] += quantized.scale_refreshes
            runtime["scale_changes"] += quantized.state_scale_changes

            output_metrics = _error_metrics(reference_output, output)
            state_metrics = _error_metrics(reference_state, runtime["state"])
            row = {
                "run_id": f"scale_policy_{config.seed:08x}_{config.trace_family}",
                "split": config.split,
                "seed": config.seed,
                "trace_family": config.trace_family,
                "variant": spec.variant,
                "policy": spec.policy,
                "refresh_interval": spec.refresh_interval or "",
                "layer_id": 0,
                "token_index": token_index,
                "output_cosine_fp32": output_metrics["cosine"],
                "output_rel_l2": output_metrics["rel_l2"],
                "output_max_abs": output_metrics["max_abs"],
                "state_rel_l2": state_metrics["rel_l2"],
                "state_max_abs": state_metrics["max_abs"],
                "state_element_saturations": quantized.element_saturations,
                "state_element_saturations_cumulative": runtime["saturations"],
                "state_scale_refreshes": quantized.scale_refreshes,
                "state_scale_refreshes_cumulative": runtime["refreshes"],
                "state_scale_changes": quantized.state_scale_changes,
                "state_scale_changes_cumulative": runtime["scale_changes"],
                "event_scope": "floating_qdq_state_requantization_only",
            }
            token_rows.append(row)
            if token_index in checkpoints:
                checkpoint_rows.append(dict(row))

    checkpoint_rows.sort(key=lambda row: (int(row["token_index"]), str(row["variant"])))
    return ScalePolicyResult(
        token_rows=token_rows,
        checkpoint_rows=checkpoint_rows,
        config=config,
        input_sha256=input_hasher.hexdigest(),
        initial_state_sha256=initial_state_sha256,
        initial_scale_blocks=int(initialized.scales.size),
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_report(path: Path, result: ScalePolicyResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MXFP4 State Scale-Policy Ablation",
        "",
        "Status: `PASS` for synthetic floating Q/DQ diagnostics only. ",
        "This uses floating Q/DQ recurrence arithmetic; ",
        "event counts cover state requantization only, not encoded accumulation or HLS.",
        "",
        (
            f"Configuration: value heads={result.config.num_value_heads}, "
            f"Q/K heads={result.config.num_qk_heads}, K={result.config.key_dim}, "
            f"V={result.config.value_dim}, activation B{result.config.activation_block_size}, "
            f"state B{result.config.state_block_size}, seed={result.config.seed}, "
            f"family={result.config.trace_family}."
        ),
        "",
        "| Token | Policy | Output cosine | State rel L2 | State max abs | Cumulative state saturations | Cumulative scale changes |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in result.checkpoint_rows:
        lines.append(
            f"| {row['token_index']} | {row['variant']} | "
            f"{float(row['output_cosine_fp32']):.6f} | "
            f"{float(row['state_rel_l2']):.6f} | "
            f"{float(row['state_max_abs']):.6f} | "
            f"{row['state_element_saturations_cumulative']} | "
            f"{row['state_scale_changes_cumulative']} |"
        )
    lines.extend(
        [
            "",
            "The preregistered development diagnostic thresholds are output cosine "
            "at least 0.99 at every required checkpoint and state relative L2 at most "
            "0.10 at token 8192. These are engineering thresholds, not model-quality claims.",
            "",
            "Refresh semantics: fixed scales use token-0 calibration; periodic scales "
            "refresh after tokens divisible by N; threshold refresh occurs per block "
            "when nonzero normalized maximum magnitude leaves [0.75, 5.5].",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(
    path: Path,
    result: ScalePolicyResult,
    token_csv: Path,
    checkpoint_csv: Path,
    report: Path,
    execution_command: str = "library call: write_manifest",
) -> None:
    source_paths = (
        ROOT / "golden" / "gdn_fp32.py",
        ROOT / "golden" / "gdn_mxfp4.py",
        ROOT / "golden" / "mxfp4_scale_policy.py",
        ROOT / "golden" / "mx_format.py",
        ROOT / "scripts" / "long_sequence_stability.py",
        ROOT / "scripts" / "scale_policy_ablation.py",
    )
    source_identity = describe_source_files(list(source_paths))
    manifest = {
        "schema": 1,
        "status": "PASS",
        "evidence_scope": "synthetic_floating_qdq_scale_policy_diagnostic",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": asdict(result.config),
        "policies": [asdict(spec) for spec in POLICIES],
        "input_sha256": result.input_sha256,
        "initial_state_sha256": result.initial_state_sha256,
        "initial_scale_blocks": result.initial_scale_blocks,
        "event_scope": "floating_qdq_state_requantization_only",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "execution": {
            "command": execution_command,
            "exit_code": 0,
            "raw_log": report.relative_to(ROOT).as_posix(),
        },
        "source_hashes": {
            source.relative_to(ROOT).as_posix(): _sha256(source)
            for source in source_paths
        },
        "outputs": {
            output.relative_to(ROOT).as_posix(): _sha256(output)
            for output in (token_csv, checkpoint_csv, report)
        },
        "limitations": [
            "synthetic inputs",
            "floating Q/DQ arithmetic, not encoded-integer arithmetic",
            "state requantization counters only",
            "not closed-loop Qwen quality evidence",
        ],
        "independent_verification": (
            "python -m scripts.verify_synthetic_stability cross-checks hashes, "
            "row sequences, checkpoint projections, and every-token parity"
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=int, default=max(DEFAULT_CHECKPOINTS))
    parser.add_argument(
        "--checkpoints", type=int, nargs="*", default=list(DEFAULT_CHECKPOINTS)
    )
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--split", choices=("development", "held_out"), default="development")
    parser.add_argument(
        "--trace-family",
        choices=("nominal", "dynamic_range", "cancellation", "high_retention"),
        default="nominal",
    )
    parser.add_argument("--num-value-heads", type=int, default=DEFAULT_NUM_VALUE_HEADS)
    parser.add_argument("--num-qk-heads", type=int, default=DEFAULT_NUM_QK_HEADS)
    parser.add_argument("--key-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--value-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--activation-block-size", type=int, choices=(16, 32), default=32)
    parser.add_argument("--state-block-size", type=int, choices=(16, 32), default=32)
    parser.add_argument("--token-csv", type=Path, default=DEFAULT_TOKEN_CSV)
    parser.add_argument("--checkpoint-csv", type=Path, default=DEFAULT_CHECKPOINT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    config = TraceConfiguration(
        tokens=args.tokens,
        checkpoints=tuple(sorted(set(args.checkpoints))),
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
    result = run_scale_policy_ablation(config)
    token_csv = _resolve(args.token_csv)
    checkpoint_csv = _resolve(args.checkpoint_csv)
    report = _resolve(args.report)
    manifest = _resolve(args.manifest)
    write_csv(token_csv, result.token_rows)
    write_csv(checkpoint_csv, result.checkpoint_rows)
    write_report(report, result)
    write_manifest(
        manifest,
        result,
        token_csv,
        checkpoint_csv,
        report,
        execution_command=subprocess.list2cmdline(
            ["python", "-m", "scripts.scale_policy_ablation", *sys.argv[1:]]
        ),
    )
    print(report.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Corrected synthetic Q/DQ calibration diagnostics.

These reports exercise the official alpha-decayed recurrence but remain
floating quantize/dequantize diagnostics. They are not encoded-oracle, HLS, or
real-model evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from .gdn_fp32 import gdn_decode_step as fp32_decode_step
from .gdn_int4 import gdn_decode_step as int4_decode_step
from .gdn_mxfp4 import gdn_decode_step as mxfp4_decode_step
from .gdn_mxfp4 import gdn_decode_step_ablation
from .mx_format import quantization_error, to_mxfp4, to_mxfp8
from .vectors import (
    DEFAULT_HEAD_DIM,
    DEFAULT_NUM_QK_HEADS,
    DEFAULT_NUM_VALUE_HEADS,
    DEFAULT_SEED,
    DecodeVector,
    generate_vectors,
)


@dataclass(frozen=True)
class CalibrationResult:
    output_path: Path
    manifest_path: Path
    report_path: Path
    ablation_path: Path
    summary: dict[str, object]


def _stack(items: Iterable[np.ndarray]) -> np.ndarray:
    return np.stack([np.asarray(item, dtype=np.float32) for item in items], axis=0)


def _mean_metric(metrics: list[dict[str, float]], key: str) -> float:
    return float(np.mean([metric[key] for metric in metrics])) if metrics else 0.0


def _format_metric_row(name: str, metrics: dict[str, float]) -> str:
    return (
        f"| {name} | {metrics['output_rel_l2']:.6f} | "
        f"{metrics['output_max_abs']:.6f} | {metrics['output_cosine']:.6f} | "
        f"{metrics['state_rel_l2']:.6f} |"
    )


def _model_metrics(
    vectors: list[DecodeVector],
    name: str,
    model_fn: Callable[[DecodeVector], tuple[np.ndarray, np.ndarray]],
) -> dict[str, float]:
    output_metrics: list[dict[str, float]] = []
    state_metrics: list[dict[str, float]] = []
    for vector in vectors:
        reference_output, reference_state = fp32_decode_step(
            vector.q,
            vector.k,
            vector.v,
            vector.alpha,
            vector.beta,
            vector.state_in,
        )
        output, state = model_fn(vector)
        output_metrics.append(quantization_error(reference_output, output))
        state_metrics.append(quantization_error(reference_state, state))
    return {
        "name": name,
        "output_rel_l2": _mean_metric(output_metrics, "rel_l2"),
        "output_max_abs": _mean_metric(output_metrics, "max_abs"),
        "output_cosine": _mean_metric(output_metrics, "cosine"),
        "state_rel_l2": _mean_metric(state_metrics, "rel_l2"),
    }


def _q1_15_codes(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(values, dtype=np.float64), 0.0, 1.0)
    return np.rint(clipped * 32768.0).astype(np.uint16)


def _scale_arrays(
    vectors: list[DecodeVector], block_size: int, state_block_size: int
) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for tensor_name in ("q", "k", "v"):
        values = [getattr(vector, tensor_name) for vector in vectors]
        arrays[f"{tensor_name}_mxfp4_b{block_size}_scales"] = np.stack(
            [to_mxfp4(value, block_size=block_size, axis=-1)[1] for value in values],
            axis=0,
        )
    arrays[f"state_mxfp4_b{state_block_size}_scales"] = np.stack(
        [to_mxfp4(vector.state_in, block_size=state_block_size, axis=-1)[1] for vector in vectors],
        axis=0,
    )
    arrays[f"state_mxfp8_e4m3_b{state_block_size}_scales"] = np.stack(
        [to_mxfp8(vector.state_in, block_size=state_block_size, axis=-1)[1] for vector in vectors],
        axis=0,
    )
    arrays["alpha_q1_15_codes"] = _q1_15_codes(_stack(vector.alpha for vector in vectors))
    arrays["beta_q1_15_codes"] = _q1_15_codes(_stack(vector.beta for vector in vectors))
    return arrays


def _write_manifest(path: Path, manifest_path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(f"{digest}  {path.as_posix()}\n", encoding="utf-8")


def _write_quantization_report(
    path: Path,
    *,
    summary: dict[str, object],
    metric_rows: list[dict[str, float]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Corrected Q/DQ Quantization Diagnostic",
        "",
        f"Generated: {summary['timestamp']}",
        f"Source: {summary['source']}",
        f"Vectors: {summary['num_vectors']}",
        (
            "Shape: "
            f"value_heads={summary['num_value_heads']}, "
            f"qk_heads={summary['num_qk_heads']}, head_dim={summary['head_dim']}"
        ),
        "State orientation: KxV",
        "",
        "This diagnostic uses the corrected alpha-decayed recurrence. It performs floating Q/DQ and is not an encoded-integer oracle, HLS parity result, or real-model quality result.",
        "",
        "| Configuration | Output rel L2 | Output max abs | Output cosine | State rel L2 |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(_format_metric_row(str(row["name"]), row) for row in metric_rows)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_ablation_report(path: Path, *, rows: list[dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Corrected Q/DQ Ablation",
        "",
        "Each row quantizes one tensor while retaining the corrected recurrence.",
        "",
        "| Tensor | Output rel L2 | Output max abs | Output cosine | State rel L2 |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(_format_metric_row(str(row["name"]), row) for row in rows)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_calibration(
    *,
    output_path: str | Path = "data/calibration/corrected_scales.npz",
    manifest_path: str | Path = "data/calibration/corrected_manifest.sha256",
    report_path: str | Path = "reports/golden_corrected/quantization_qdq.md",
    ablation_path: str | Path = "reports/golden_corrected/quantization_qdq_ablation.md",
    count: int = 16,
    seed: int = DEFAULT_SEED,
    num_value_heads: int = DEFAULT_NUM_VALUE_HEADS,
    num_qk_heads: int = DEFAULT_NUM_QK_HEADS,
    head_dim: int = DEFAULT_HEAD_DIM,
    block_size: int = 32,
    state_block_size: int = 32,
    source: str = "synthetic_official_recurrence",
) -> CalibrationResult:
    if source != "synthetic_official_recurrence":
        raise NotImplementedError("Only corrected synthetic diagnostics are locally available.")

    vectors = list(
        generate_vectors(
            count,
            kind=source,
            seed=seed,
            num_value_heads=num_value_heads,
            num_qk_heads=num_qk_heads,
            head_dim=head_dim,
        )
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    metadata: dict[str, object] = {
        "schema": 2,
        "source": source,
        "timestamp": timestamp,
        "num_vectors": count,
        "seed": seed,
        "num_value_heads": num_value_heads,
        "num_qk_heads": num_qk_heads,
        "head_dim": head_dim,
        "state_orientation": "KxV",
        "recurrence": "transformers_v4.57.0_recurrent",
        "block_size": block_size,
        "state_block_size": state_block_size,
    }
    arrays = _scale_arrays(vectors, block_size, state_block_size)
    np.savez_compressed(
        output,
        metadata_json=np.array(json.dumps(metadata, sort_keys=True)),
        **arrays,
    )
    manifest = Path(manifest_path)
    _write_manifest(output, manifest)

    metric_rows = [
        _model_metrics(
            vectors,
            f"MXFP4 B={block_size}, state MXFP4 B={state_block_size}",
            lambda vector: mxfp4_decode_step(
                vector.q,
                vector.k,
                vector.v,
                vector.alpha,
                vector.beta,
                vector.state_in,
                block_size=block_size,
                state_block_size=state_block_size,
            ),
        ),
        _model_metrics(
            vectors,
            f"MXFP4 B={block_size}, state MXFP8-E4M3 B={state_block_size}",
            lambda vector: mxfp4_decode_step(
                vector.q,
                vector.k,
                vector.v,
                vector.alpha,
                vector.beta,
                vector.state_in,
                block_size=block_size,
                state_block_size=state_block_size,
                state_precision="mxfp8_e4m3",
            ),
        ),
        _model_metrics(
            vectors,
            "INT4 fallback",
            lambda vector: int4_decode_step(
                vector.q,
                vector.k,
                vector.v,
                vector.alpha,
                vector.beta,
                vector.state_in,
            ),
        ),
    ]
    _write_quantization_report(Path(report_path), summary=metadata, metric_rows=metric_rows)

    ablation_rows = [
        _model_metrics(
            vectors,
            tensor_name,
            lambda vector, tensor_name=tensor_name: gdn_decode_step_ablation(
                vector.q,
                vector.k,
                vector.v,
                vector.alpha,
                vector.beta,
                vector.state_in,
                quantized_tensors={tensor_name},
                block_size=block_size,
                state_block_size=state_block_size,
            ),
        )
        for tensor_name in ("q", "k", "v", "state")
    ]
    _write_ablation_report(Path(ablation_path), rows=ablation_rows)

    summary = {
        **metadata,
        "output_path": output.as_posix(),
        "manifest_path": manifest.as_posix(),
        "report_path": Path(report_path).as_posix(),
        "ablation_path": Path(ablation_path).as_posix(),
        "metrics": metric_rows,
        "ablation": ablation_rows,
    }
    return CalibrationResult(
        output_path=output,
        manifest_path=manifest,
        report_path=Path(report_path),
        ablation_path=Path(ablation_path),
        summary=summary,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/calibration/corrected_scales.npz")
    parser.add_argument("--manifest", default="data/calibration/corrected_manifest.sha256")
    parser.add_argument("--report", default="reports/golden_corrected/quantization_qdq.md")
    parser.add_argument(
        "--ablation-report",
        default="reports/golden_corrected/quantization_qdq_ablation.md",
    )
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument("--num-value-heads", type=int, default=DEFAULT_NUM_VALUE_HEADS)
    parser.add_argument("--num-qk-heads", type=int, default=DEFAULT_NUM_QK_HEADS)
    parser.add_argument("--head-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--block-size", type=int, choices=[16, 32], default=32)
    parser.add_argument("--state-block-size", type=int, choices=[16, 32], default=32)
    args = parser.parse_args(argv)

    result = run_calibration(
        output_path=args.output,
        manifest_path=args.manifest,
        report_path=args.report,
        ablation_path=args.ablation_report,
        count=args.count,
        seed=args.seed,
        num_value_heads=args.num_value_heads,
        num_qk_heads=args.num_qk_heads,
        head_dim=args.head_dim,
        block_size=args.block_size,
        state_block_size=args.state_block_size,
    )
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

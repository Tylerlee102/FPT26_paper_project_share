"""PTQ calibration and Phase 2 quantization report generation."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

import numpy as np

from .gdn_fp32 import gdn_decode_step as fp32_decode_step
from .gdn_int4 import gdn_decode_step as int4_decode_step
from .gdn_mxfp4 import gdn_decode_step as mxfp4_decode_step
from .gdn_mxfp4 import gdn_decode_step_ablation
from .mx_format import quantization_error, to_mxfp4, to_mxfp8
from .vectors import DEFAULT_HEAD_DIM, DEFAULT_NUM_HEADS, DEFAULT_SEED, DecodeVector, generate_vectors


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
    return float(np.mean([m[key] for m in metrics])) if metrics else 0.0


def _format_metric_row(name: str, metrics: dict[str, float]) -> str:
    return (
        f"| {name} | {metrics['output_rel_l2']:.6f} | {metrics['output_max_abs']:.6f} | "
        f"{metrics['output_cosine']:.6f} | {metrics['state_rel_l2']:.6f} |"
    )


def _model_metrics(vectors: list[DecodeVector], name: str, model_fn) -> dict[str, float]:
    output_metrics: list[dict[str, float]] = []
    state_metrics: list[dict[str, float]] = []
    for vector in vectors:
        ref_output, ref_state = fp32_decode_step(
            vector.q, vector.k, vector.v, vector.beta, vector.gate, vector.state_in
        )
        out, state = model_fn(vector)
        output_metrics.append(quantization_error(ref_output, out))
        state_metrics.append(quantization_error(ref_state, state))
    return {
        "name": name,
        "output_rel_l2": _mean_metric(output_metrics, "rel_l2"),
        "output_max_abs": _mean_metric(output_metrics, "max_abs"),
        "output_cosine": _mean_metric(output_metrics, "cosine"),
        "state_rel_l2": _mean_metric(state_metrics, "rel_l2"),
    }


def _scale_arrays(vectors: list[DecodeVector], block_size: int, state_block_size: int) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for tensor_name in ("q", "k", "v", "gate"):
        values = [getattr(vector, tensor_name) for vector in vectors]
        arrays[f"{tensor_name}_mxfp4_b{block_size}_scales"] = np.stack(
            [to_mxfp4(value, block_size=block_size, axis=-1)[1] for value in values],
            axis=0,
        )
    arrays[f"state_mxfp4_b{state_block_size}_scales"] = np.stack(
        [to_mxfp4(vector.state_in, block_size=state_block_size, axis=-1)[1] for vector in vectors],
        axis=0,
    )
    arrays[f"state_mxfp8_b{state_block_size}_scales"] = np.stack(
        [to_mxfp8(vector.state_in, block_size=state_block_size, axis=-1)[1] for vector in vectors],
        axis=0,
    )
    beta = _stack(vector.beta for vector in vectors)
    max_abs_beta = float(np.max(np.abs(beta))) if beta.size else 0.0
    arrays["beta_int8_scale"] = np.array(1.0 if max_abs_beta == 0.0 else max_abs_beta / 127.0, dtype=np.float32)
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
        "# Quantization Report",
        "",
        f"Generated: {summary['timestamp']}",
        f"Source: {summary['source']}",
        f"Vectors: {summary['num_vectors']}",
        f"Shape: num_heads={summary['num_heads']}, head_dim={summary['head_dim']}",
        "",
        "This offline Phase 2 run uses deterministic synthetic vectors. Qwen3-Next activation capture and "
        "Microsoft microxcaling parity remain external-dependency checks for the full acceptance run.",
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
        "# Quantization Ablation",
        "",
        "Each row quantizes one tensor to MXFP4 while keeping the rest in FP32.",
        "",
        "| Tensor | Output rel L2 | Output max abs | Output cosine | State rel L2 |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(_format_metric_row(str(row["name"]), row) for row in rows)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_calibration(
    *,
    output_path: str | Path = "data/calibration/scales.npz",
    manifest_path: str | Path = "data/calibration/manifest.sha256",
    report_path: str | Path = "reports/golden/quantization.md",
    ablation_path: str | Path = "reports/golden/quantization_ablation.md",
    count: int = 16,
    seed: int = DEFAULT_SEED,
    num_heads: int = DEFAULT_NUM_HEADS,
    head_dim: int = DEFAULT_HEAD_DIM,
    block_size: int = 32,
    state_block_size: int = 16,
    source: str = "synthetic",
) -> CalibrationResult:
    if source != "synthetic":
        raise NotImplementedError("Only synthetic offline calibration is available without Qwen capture data.")

    vectors = list(
        generate_vectors(
            count,
            kind="synthetic",
            seed=seed,
            num_heads=num_heads,
            head_dim=head_dim,
        )
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    metadata = {
        "schema": 1,
        "source": "synthetic",
        "timestamp": timestamp,
        "num_vectors": count,
        "seed": seed,
        "num_heads": num_heads,
        "head_dim": head_dim,
        "block_size": block_size,
        "state_block_size": state_block_size,
    }
    arrays = _scale_arrays(vectors, block_size, state_block_size)
    np.savez_compressed(output, metadata_json=np.array(json.dumps(metadata, sort_keys=True)), **arrays)
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
                vector.beta,
                vector.gate,
                vector.state_in,
                block_size=block_size,
                state_block_size=state_block_size,
            ),
        ),
        _model_metrics(
            vectors,
            f"MXFP4 B={block_size}, state MXFP8 B={state_block_size}",
            lambda vector: mxfp4_decode_step(
                vector.q,
                vector.k,
                vector.v,
                vector.beta,
                vector.gate,
                vector.state_in,
                block_size=block_size,
                state_block_size=state_block_size,
                state_precision="mxfp8",
            ),
        ),
        _model_metrics(
            vectors,
            "INT4 fallback",
            lambda vector: int4_decode_step(vector.q, vector.k, vector.v, vector.beta, vector.gate, vector.state_in),
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
                vector.beta,
                vector.gate,
                vector.state_in,
                quantized_tensors={tensor_name},
                block_size=block_size,
                state_block_size=state_block_size,
            ),
        )
        for tensor_name in ("q", "k", "v", "gate", "state")
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
    parser.add_argument("--output", default="data/calibration/scales.npz")
    parser.add_argument("--manifest", default="data/calibration/manifest.sha256")
    parser.add_argument("--report", default="reports/golden/quantization.md")
    parser.add_argument("--ablation-report", default="reports/golden/quantization_ablation.md")
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--seed", type=lambda s: int(s, 0), default=DEFAULT_SEED)
    parser.add_argument("--num-heads", type=int, default=DEFAULT_NUM_HEADS)
    parser.add_argument("--head-dim", type=int, default=DEFAULT_HEAD_DIM)
    parser.add_argument("--block-size", type=int, choices=[16, 32], default=32)
    parser.add_argument("--state-block-size", type=int, choices=[16, 32], default=16)
    args = parser.parse_args(argv)

    result = run_calibration(
        output_path=args.output,
        manifest_path=args.manifest,
        report_path=args.report,
        ablation_path=args.ablation_report,
        count=args.count,
        seed=args.seed,
        num_heads=args.num_heads,
        head_dim=args.head_dim,
        block_size=args.block_size,
        state_block_size=args.state_block_size,
    )
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

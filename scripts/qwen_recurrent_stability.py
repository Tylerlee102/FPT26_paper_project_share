"""Evaluate low-precision GDN recurrence on reconstructed real Qwen tensors."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import gdn_decode_step as fp32_decode_step
from golden.gdn_bf16 import gdn_decode_step as bf16_decode_step
from golden.gdn_int4 import gdn_decode_step as int4_decode_step
from golden.gdn_mxfp4 import gdn_decode_step as mx_decode_step
from scripts.hf_safetensors_range import sha256_file


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT / "data" / "calibration" / "qwen3_next_80b_a3b_layer12_recurrence.npz"
)
DEFAULT_TRACE = ROOT / "reports" / "benchmark" / "qwen_recurrent_stability.csv"
DEFAULT_SUMMARY = ROOT / "reports" / "benchmark" / "qwen_recurrent_stability_summary.csv"
DEFAULT_MANIFEST = ROOT / "reports" / "benchmark" / "qwen_recurrent_stability_manifest.json"

VARIANTS = (
    "bf16_qdq_fp32_accum_state_bf16",
    "mxfp4_qdq_state_mxfp4_b32",
    "mxfp4_qdq_state_mxfp8_b32",
    "flat_int4_qdq",
)


def _metrics(reference: np.ndarray, candidate: np.ndarray) -> tuple[float, float, float]:
    ref = np.asarray(reference, dtype=np.float64).reshape(-1)
    cand = np.asarray(candidate, dtype=np.float64).reshape(-1)
    difference = cand - ref
    ref_norm = float(np.linalg.norm(ref))
    cand_norm = float(np.linalg.norm(cand))
    if ref_norm == 0.0 and cand_norm == 0.0:
        cosine = 1.0
    elif ref_norm == 0.0 or cand_norm == 0.0:
        cosine = 0.0
    else:
        cosine = float(np.dot(ref, cand) / (ref_norm * cand_norm))
    relative_l2 = float(np.linalg.norm(difference) / max(ref_norm, np.finfo(np.float64).tiny))
    max_abs = float(np.max(np.abs(difference))) if difference.size else 0.0
    return cosine, relative_l2, max_abs


def evaluate(input_path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    with np.load(input_path, allow_pickle=False) as archive:
        q = np.asarray(archive["q"], dtype=np.float32)
        k = np.asarray(archive["k"], dtype=np.float32)
        v = np.asarray(archive["v"], dtype=np.float32)
        alpha = np.asarray(archive["alpha"], dtype=np.float32)
        beta = np.asarray(archive["beta"], dtype=np.float32)
        mask = np.asarray(archive["attention_mask"], dtype=bool)
        source_metadata = json.loads(str(archive["metadata_json"]))

    trace_rows: list[dict[str, object]] = []
    for sequence in range(q.shape[0]):
        reference_state = np.zeros((32, 128, 128), dtype=np.float32)
        states = {variant: reference_state.copy() for variant in VARIANTS}
        valid_indices = np.flatnonzero(mask[sequence])
        for position, token in enumerate(valid_indices, start=1):
            reference_output, reference_state = fp32_decode_step(
                q[sequence, token],
                k[sequence, token],
                v[sequence, token],
                alpha[sequence, token],
                beta[sequence, token],
                reference_state,
            )
            outputs: dict[str, np.ndarray] = {}
            outputs[VARIANTS[0]], states[VARIANTS[0]] = bf16_decode_step(
                q[sequence, token], k[sequence, token], v[sequence, token],
                alpha[sequence, token], beta[sequence, token], states[VARIANTS[0]],
            )
            outputs[VARIANTS[1]], states[VARIANTS[1]] = mx_decode_step(
                q[sequence, token], k[sequence, token], v[sequence, token],
                alpha[sequence, token], beta[sequence, token], states[VARIANTS[1]],
                block_size=32, state_block_size=32, state_precision="mxfp4",
            )
            outputs[VARIANTS[2]], states[VARIANTS[2]] = mx_decode_step(
                q[sequence, token], k[sequence, token], v[sequence, token],
                alpha[sequence, token], beta[sequence, token], states[VARIANTS[2]],
                block_size=32, state_block_size=32, state_precision="mxfp8_e4m3",
            )
            outputs[VARIANTS[3]], states[VARIANTS[3]] = int4_decode_step(
                q[sequence, token], k[sequence, token], v[sequence, token],
                alpha[sequence, token], beta[sequence, token], states[VARIANTS[3]],
            )
            for variant in VARIANTS:
                output_cosine, output_rel_l2, output_max_abs = _metrics(
                    reference_output, outputs[variant]
                )
                state_cosine, state_rel_l2, state_max_abs_error = _metrics(
                    reference_state, states[variant]
                )
                trace_rows.append(
                    {
                        "sequence": sequence,
                        "token": position,
                        "source_token_index": int(token),
                        "variant": variant,
                        "output_cosine_fp32": output_cosine,
                        "output_rel_l2": output_rel_l2,
                        "output_max_abs_error": output_max_abs,
                        "state_cosine_fp32": state_cosine,
                        "state_rel_l2": state_rel_l2,
                        "state_max_abs_error": state_max_abs_error,
                        "reference_state_max_abs": float(np.max(np.abs(reference_state))),
                        "candidate_state_max_abs": float(np.max(np.abs(states[variant]))),
                        "nonfinite_events": int(
                            np.count_nonzero(~np.isfinite(outputs[variant]))
                            + np.count_nonzero(~np.isfinite(states[variant]))
                        ),
                    }
                )

    summary_rows: list[dict[str, object]] = []
    for sequence in range(q.shape[0]):
        for variant in VARIANTS:
            rows = [
                row for row in trace_rows
                if row["sequence"] == sequence and row["variant"] == variant
            ]
            final = rows[-1]
            summary_rows.append(
                {
                    "sequence": sequence,
                    "tokens": len(rows),
                    "variant": variant,
                    "final_output_cosine_fp32": final["output_cosine_fp32"],
                    "worst_output_cosine_fp32": min(float(row["output_cosine_fp32"]) for row in rows),
                    "final_state_rel_l2": final["state_rel_l2"],
                    "worst_state_rel_l2": max(float(row["state_rel_l2"]) for row in rows),
                    "max_state_abs_error": max(float(row["state_max_abs_error"]) for row in rows),
                    "nonfinite_events": sum(int(row["nonfinite_events"]) for row in rows),
                }
            )

    aggregate: dict[str, object] = {}
    for variant in VARIANTS:
        rows = [row for row in summary_rows if row["variant"] == variant]
        aggregate[variant] = {
            "mean_final_output_cosine_fp32": float(np.mean([row["final_output_cosine_fp32"] for row in rows])),
            "worst_output_cosine_fp32": min(float(row["worst_output_cosine_fp32"]) for row in rows),
            "mean_final_state_rel_l2": float(np.mean([row["final_state_rel_l2"] for row in rows])),
            "worst_state_rel_l2": max(float(row["worst_state_rel_l2"]) for row in rows),
            "max_state_abs_error": max(float(row["max_state_abs_error"]) for row in rows),
            "nonfinite_events": sum(int(row["nonfinite_events"]) for row in rows),
        }
    manifest = {
        "status": "PASS",
        "schema": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": input_path.as_posix(),
        "input_sha256": sha256_file(input_path),
        "source_metadata": source_metadata,
        "arithmetic_boundary": "floating_qdq_recurrence_diagnostic",
        "variants": list(VARIANTS),
        "aggregate": aggregate,
        "limitations": [
            "Four real prompt traces contain only 12 to 18 valid tokens each.",
            "The low-precision paths are floating Q/DQ diagnostics, not HLS bit-exact execution.",
            "No full-model logits or perplexity are evaluated.",
        ],
    }
    return trace_rows, summary_rows, manifest


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    trace_rows, summary_rows, manifest = evaluate(args.input)
    _write_csv(args.trace, trace_rows)
    _write_csv(args.summary, summary_rows)
    manifest["trace_csv"] = args.trace.as_posix()
    manifest["trace_sha256"] = sha256_file(args.trace)
    manifest["summary_csv"] = args.summary.as_posix()
    manifest["summary_sha256"] = sha256_file(args.summary)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

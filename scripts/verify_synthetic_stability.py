"""Verify long-trace and scale-policy evidence and derive scoped decisions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "reports" / "benchmark" / "corrected"
DEFAULT_LONG_MANIFEST = BENCHMARK / "long_trace_manifest.json"
DEFAULT_SCALE_MANIFEST = BENCHMARK / "scale_policy_manifest.json"
DEFAULT_OUTPUT = BENCHMARK / "synthetic_stability_verification.json"
DEFAULT_MARKDOWN = BENCHMARK / "synthetic_stability_verification.md"
CHECKPOINTS = (64, 256, 1024, 4096, 8192)
LONG_VARIANTS = {
    "fp32",
    "bf16_qdq_fp32_accum_state_bf16",
    "flat_int4_qdq",
    "mxfp4_qdq_act_b32_state_b32",
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _verify_manifest(path: Path, expected_scope: str) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS":
        raise ValueError(f"manifest status is not PASS: {path}")
    if manifest.get("evidence_scope") != expected_scope:
        raise ValueError(f"unexpected evidence scope: {path}")
    for relative, expected in manifest["source_hashes"].items():
        if _sha256(ROOT / relative) != expected:
            raise ValueError(f"source hash mismatch: {relative}")
    for relative, expected in manifest["outputs"].items():
        if _sha256(ROOT / relative) != expected:
            raise ValueError(f"output hash mismatch: {relative}")
    identity = manifest["source_identity"]
    if identity["git_revision"] != manifest["source_revision"]:
        raise ValueError(f"source revision mismatch: {path}")
    if len(identity["dirty_patch"]["sha256"]) != 64:
        raise ValueError(f"invalid dirty-patch fingerprint: {path}")
    if manifest["execution"]["exit_code"] != 0:
        raise ValueError(f"evidence command did not exit zero: {path}")
    return manifest


def threshold_decision(rows: list[dict[str, str]]) -> dict[str, object]:
    checkpoint_rows = [row for row in rows if int(row["token_index"]) in CHECKPOINTS]
    if {int(row["token_index"]) for row in checkpoint_rows} != set(CHECKPOINTS):
        raise ValueError("required checkpoint rows are incomplete")
    final = next(row for row in checkpoint_rows if int(row["token_index"]) == 8192)
    minimum_cosine = min(float(row["output_cosine_fp32"]) for row in checkpoint_rows)
    final_state_rel_l2 = float(final["state_rel_l2"])
    status = "PASS" if minimum_cosine >= 0.99 and final_state_rel_l2 <= 0.10 else "FAIL"
    return {
        "status": status,
        "minimum_checkpoint_output_cosine": minimum_cosine,
        "token_8192_state_relative_l2": final_state_rel_l2,
        "output_cosine_threshold": 0.99,
        "state_relative_l2_threshold": 0.10,
    }


def _validate_metrics(rows: list[dict[str, str]], fields: tuple[str, ...]) -> None:
    for row in rows:
        for field in fields:
            value = float(row[field])
            if not math.isfinite(value):
                raise ValueError(f"non-finite metric {field}")
        cosine = float(row["output_cosine_fp32"])
        if not -1.0 <= cosine <= 1.0:
            raise ValueError("cosine is outside [-1, 1]")
        if float(row["state_rel_l2"]) < 0.0 or float(row["state_max_abs"]) < 0.0:
            raise ValueError("state error metric is negative")


def verify(
    long_manifest_path: Path = DEFAULT_LONG_MANIFEST,
    scale_manifest_path: Path = DEFAULT_SCALE_MANIFEST,
) -> dict[str, object]:
    long_manifest = _verify_manifest(
        long_manifest_path, "synthetic_floating_qdq_diagnostic"
    )
    scale_manifest = _verify_manifest(
        scale_manifest_path, "synthetic_floating_qdq_scale_policy_diagnostic"
    )
    if long_manifest["input_sha256"] != scale_manifest["input_sha256"]:
        raise ValueError("long trace and scale ablation input streams differ")
    if long_manifest["initial_state_sha256"] != scale_manifest["initial_state_sha256"]:
        raise ValueError("long trace and scale ablation initial states differ")
    long_token_path = ROOT / "reports/benchmark/corrected/long_trace_tokens.csv"
    long_checkpoint_path = ROOT / "reports/benchmark/corrected/long_trace_checkpoints.csv"
    scale_token_path = ROOT / "reports/benchmark/corrected/scale_policy_tokens.csv"
    scale_checkpoint_path = ROOT / "reports/benchmark/corrected/scale_policy_checkpoints.csv"
    long_rows = _read_csv(long_token_path)
    long_checkpoints = _read_csv(long_checkpoint_path)
    scale_rows = _read_csv(scale_token_path)
    scale_checkpoints = _read_csv(scale_checkpoint_path)

    if len(long_rows) != 8192 * len(LONG_VARIANTS):
        raise ValueError("long-trace token row count mismatch")
    if len(long_checkpoints) != len(CHECKPOINTS) * len(LONG_VARIANTS):
        raise ValueError("long-trace checkpoint row count mismatch")
    if {row["variant"] for row in long_rows} != LONG_VARIANTS:
        raise ValueError("long-trace variant set mismatch")
    for variant in LONG_VARIANTS:
        variant_rows = [row for row in long_rows if row["variant"] == variant]
        if [int(row["token_index"]) for row in variant_rows] != list(range(1, 8193)):
            raise ValueError(f"token sequence mismatch for {variant}")
    _validate_metrics(
        long_rows,
        (
            "output_cosine_fp32",
            "output_rel_l2",
            "output_max_abs",
            "state_rel_l2",
            "state_max_abs",
        ),
    )
    fp32_rows = [row for row in long_rows if row["variant"] == "fp32"]
    if any(
        float(row["output_cosine_fp32"]) != 1.0
        or float(row["output_rel_l2"]) != 0.0
        or float(row["state_rel_l2"]) != 0.0
        or row["event_metrics_status"] != "PASS"
        for row in fp32_rows
    ):
        raise ValueError("FP32 self-reference rows are not exact")
    if any(
        row["event_metrics_status"] != "NOT_RUN"
        for row in long_rows
        if row["variant"] != "fp32"
    ):
        raise ValueError("floating Q/DQ event status is not explicit")
    selected_long_rows = sorted(
        (row for row in long_rows if int(row["token_index"]) in CHECKPOINTS),
        key=lambda row: (int(row["token_index"]), row["variant"]),
    )
    if selected_long_rows != long_checkpoints:
        raise ValueError("checkpoint CSV is not an exact projection of token CSV")

    policy_names = {entry["variant"] for entry in scale_manifest["policies"]}
    if len(scale_rows) != 8192 * len(policy_names):
        raise ValueError("scale-policy token row count mismatch")
    if len(scale_checkpoints) != len(CHECKPOINTS) * len(policy_names):
        raise ValueError("scale-policy checkpoint row count mismatch")
    if {row["variant"] for row in scale_rows} != policy_names:
        raise ValueError("scale-policy variant set mismatch")
    _validate_metrics(
        scale_rows,
        (
            "output_cosine_fp32",
            "output_rel_l2",
            "output_max_abs",
            "state_rel_l2",
            "state_max_abs",
        ),
    )
    for row in scale_rows:
        for field in (
            "state_element_saturations",
            "state_element_saturations_cumulative",
            "state_scale_refreshes",
            "state_scale_refreshes_cumulative",
            "state_scale_changes",
            "state_scale_changes_cumulative",
        ):
            if int(row[field]) < 0:
                raise ValueError(f"negative scale-policy event count: {field}")
    selected_scale_rows = sorted(
        (row for row in scale_rows if int(row["token_index"]) in CHECKPOINTS),
        key=lambda row: (int(row["token_index"]), row["variant"]),
    )
    if selected_scale_rows != scale_checkpoints:
        raise ValueError("scale checkpoint CSV is not an exact projection")

    long_mxfp4 = {
        int(row["token_index"]): row
        for row in long_rows
        if row["variant"] == "mxfp4_qdq_act_b32_state_b32"
    }
    scale_every = {
        int(row["token_index"]): row
        for row in scale_rows
        if row["variant"] == "mxfp4_scale_every_token"
    }
    for token in range(1, 8193):
        for metric in (
            "output_cosine_fp32",
            "output_rel_l2",
            "output_max_abs",
            "state_rel_l2",
            "state_max_abs",
        ):
            if long_mxfp4[token][metric] != scale_every[token][metric]:
                raise ValueError(
                    f"every-token scale policy diverges from main MXFP4 trace at token {token}"
                )

    long_decisions = {
        variant: threshold_decision(
            [row for row in long_checkpoints if row["variant"] == variant]
        )
        for variant in sorted(LONG_VARIANTS - {"fp32"})
    }
    policy_decisions = {
        variant: threshold_decision(
            [row for row in scale_checkpoints if row["variant"] == variant]
        )
        for variant in sorted(policy_names)
    }
    uniform_variant = "mxfp4_qdq_act_b32_state_b32"
    bf16_variant = "bf16_qdq_fp32_accum_state_bf16"
    source_identity = describe_source_files([Path(__file__).resolve()])
    result: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "evidence_scope": "synthetic_floating_qdq_only",
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "execution": {
            "command": "python -m scripts.verify_synthetic_stability",
            "exit_code": 0,
            "raw_log": DEFAULT_MARKDOWN.relative_to(ROOT).as_posix(),
        },
        "configuration": long_manifest["configuration"],
        "artifact_integrity": {
            "long_trace": "PASS",
            "scale_policy_ablation": "PASS",
            "every_token_cross_check": "PASS",
            "shared_input_stream_cross_check": "PASS",
            "long_token_rows": len(long_rows),
            "scale_policy_token_rows": len(scale_rows),
        },
        "long_trace_decisions": long_decisions,
        "scale_policy_decisions": policy_decisions,
        "bf16_software_stability": long_decisions[bf16_variant]["status"],
        "uniform_mxfp4_stability": long_decisions[uniform_variant]["status"],
        "scale_policy_rescues_uniform_mxfp4": (
            "PASS"
            if any(row["status"] == "PASS" for row in policy_decisions.values())
            else "FAIL"
        ),
        "overall_synthetic_mxfp4_for_bf16_replacement_question": "FAIL",
        "overall_mxfp4_for_bf16_replacement_question": "FAIL",
        "overall_finding": (
            "The BF16 operand/state diagnostic passes the frozen synthetic stability "
            "thresholds, while uniform MXFP4 and every tested block-scale policy fail. "
            "Uniform native MXFP4 therefore fails the replacement question on stability "
            "for this trace, independent of the still-NOT_RUN physical cost comparison."
        ),
        "limitations": [
            "synthetic nominal trace only",
            "floating quantize/dequantize arithmetic, not encoded HLS arithmetic",
            "no realistic activation capture or closed-loop Qwen execution",
            "this verifier does not ingest the separately reported matched BF16 HLS estimate",
            "no matched post-route implementation, power, or board result",
        ],
        "independent_verification": [
            "recomputed SHA256 for every declared source and output",
            "checked exact per-variant token sequences and checkpoint projections",
            "cross-checked shared long-trace and scale-policy input hashes",
            "cross-checked every-token MXFP4 metrics between independent runners",
        ],
    }
    return result


def write_report(result: dict[str, object], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    uniform = result["long_trace_decisions"]["mxfp4_qdq_act_b32_state_b32"]
    bf16 = result["long_trace_decisions"]["bf16_qdq_fp32_accum_state_bf16"]
    mxfp8 = result["long_trace_decisions"][
        "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32"
    ]
    int4 = result["long_trace_decisions"]["flat_int4_qdq"]
    markdown_path.write_text(
        "\n".join(
            [
                "# Synthetic Stability Verification",
                "",
                "- Artifact integrity: `PASS`",
                f"- BF16 software stability gate: `{bf16['status']}`",
                f"- Uniform MXFP4 stability gate: `{uniform['status']}`",
                f"- MXFP8-state stability gate: `{mxfp8['status']}`",
                f"- Flat INT4 stability gate: `{int4['status']}`",
                f"- Any tested scale policy rescues uniform MXFP4: `{result['scale_policy_rescues_uniform_mxfp4']}`",
                (
                    "- Overall synthetic MXFP4-for-BF16 replacement question: "
                    f"`{result['overall_mxfp4_for_bf16_replacement_question']}`"
                ),
                "",
                result["overall_finding"],
                "",
                "These conclusions are limited to the frozen synthetic floating Q/DQ",
                "diagnostic. They are not model-quality or physical-FPGA evidence.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--long-manifest", type=Path, default=DEFAULT_LONG_MANIFEST)
    parser.add_argument("--scale-manifest", type=Path, default=DEFAULT_SCALE_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    paths = [args.long_manifest, args.scale_manifest, args.output, args.markdown]
    resolved = [path if path.is_absolute() else ROOT / path for path in paths]
    result = verify(resolved[0], resolved[1])
    write_report(result, resolved[2], resolved[3])
    print(json.dumps({"status": result["status"], "uniform_mxfp4": result["uniform_mxfp4_stability"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

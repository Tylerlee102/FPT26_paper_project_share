"""Build a controlled BF16, native-MXFP4, and native-MXFP8 HLS comparison."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MX = ROOT / "reports" / "csynth" / "corrected" / "baseline_csynth_summary.json"
DEFAULT_BF16 = ROOT / "reports" / "csynth" / "corrected" / "bf16_hls_summary.json"
DEFAULT_MXFP8 = ROOT / "reports" / "csynth" / "corrected" / "mxfp8_hls_summary.json"
DEFAULT_MX_IMPL = (
    ROOT
    / "reports"
    / "csynth"
    / "corrected_attempt9_transport_pipeline_cleanup"
    / "report"
    / "gdn_top_impl_csynth.rpt"
)
DEFAULT_OUTPUT = ROOT / "reports" / "benchmark" / "corrected"
PARAMS = ROOT / "hls" / "include" / "gdn_params.hpp"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_step_cycles(report: str, loop_name: str = "step_heads") -> dict[str, int]:
    match = re.search(
        rf"^\s*\|-\s*{re.escape(loop_name)}\s*\|\s*(\d+)\|\s*(\d+)\|",
        report,
        re.MULTILINE,
    )
    if match is None:
        raise ValueError(f"step loop is absent from HLS report: {loop_name}")
    return {"minimum": int(match.group(1)), "maximum": int(match.group(2))}


def _controlled_configuration() -> dict[str, object]:
    text = PARAMS.read_text(encoding="utf-8")

    def literal(name: str) -> int:
        match = re.search(rf"constexpr int {name}\s*=\s*(\d+)\s*;", text)
        if match is None:
            raise ValueError(f"missing literal parameter: {name}")
        return int(match.group(1))

    def define(name: str) -> int:
        match = re.search(rf"#define {name}\s+(\d+)", text)
        if match is None:
            raise ValueError(f"missing default define: {name}")
        return int(match.group(1))

    return {
        "num_qk_heads": literal("NUM_QK_HEADS"),
        "num_value_heads": literal("NUM_VALUE_HEADS"),
        "key_dim": literal("KEY_DIM"),
        "value_dim": literal("VALUE_DIM"),
        "num_layers": literal("NUM_LAYERS"),
        "num_sequences": define("GDN_NUM_SEQUENCES"),
        "p_k": define("GDN_P_K"),
        "p_v": define("GDN_P_V"),
        "block_size": define("GDN_BLOCK_SIZE"),
        "state_orientation": "KxV",
        "pipeline": "same persistent-state five-phase GDN command kernel",
    }


def generate_comparison(
    mx_path: Path,
    bf16_path: Path,
    mx_impl_path: Path,
    output: Path,
    mxfp8_path: Path = DEFAULT_MXFP8,
) -> dict[str, object]:
    for path in (mx_path, bf16_path, mxfp8_path, mx_impl_path, PARAMS):
        if not path.exists():
            raise FileNotFoundError(path)
    mx = json.loads(mx_path.read_text(encoding="utf-8"))
    bf16 = json.loads(bf16_path.read_text(encoding="utf-8"))
    mxfp8 = json.loads(mxfp8_path.read_text(encoding="utf-8"))
    if any(payload.get("status") != "PASS" for payload in (mx, bf16, mxfp8)):
        raise ValueError("all HLS extraction manifests must be PASS")
    mx_metrics = mx["metrics"]
    bf16_metrics = bf16["csynth"]["metrics"]
    mxfp8_metrics = mxfp8["csynth"]["metrics"]
    for key in ("target_device", "target_clock_ns", "estimated_clock_ns"):
        if not (mx_metrics[key] == bf16_metrics[key] == mxfp8_metrics[key]):
            raise ValueError(f"uncontrolled HLS comparison field: {key}")

    mx_step = parse_step_cycles(mx_impl_path.read_text(encoding="utf-8"))
    bf16_step = bf16["csynth"]["step_loop_latency_cycles"]
    mxfp8_step = mxfp8["csynth"]["step_loop_latency_cycles"]
    configuration = _controlled_configuration()
    rows = []
    variants = (
        ("BF16", bf16_metrics, bf16_step, "BF16 state; BF16 operands; FP32 accumulation"),
        (
            "uniform_mxfp4",
            mx_metrics,
            mx_step,
            "E2M1 state/operands with E8M0 block scales and integer accumulation",
        ),
        (
            "native_mxfp8",
            mxfp8_metrics,
            mxfp8_step,
            "E4M3 state/operands with E8M0 block scales and integer accumulation",
        ),
    )
    for variant, metrics, step, arithmetic in variants:
        resources = metrics["resources"]
        rows.append(
            {
                "variant": variant,
                "arithmetic": arithmetic,
                "target_device": metrics["target_device"],
                "target_clock_ns": metrics["target_clock_ns"],
                "estimated_clock_ns": metrics["estimated_clock_ns"],
                "estimated_fmax_mhz": metrics["estimated_fmax_mhz"],
                "step_cycles_min": step["minimum"],
                "step_cycles_max": step["maximum"],
                "lut": resources["LUT"],
                "ff": resources["FF"],
                "bram_18k": resources["BRAM_18K"],
                "uram": resources["URAM"],
                "dsp": resources["DSP"],
                "evidence_stage": "Vitis HLS C-synthesis estimate",
                "post_route_status": "NOT_RUN",
                "energy_status": "BLOCKED_EXTERNAL_NO_U55C_DEVICE_OR_XRT",
            }
        )

    bf = rows[0]
    mxr = rows[1]
    mx8 = rows[2]

    def ratio(row: dict[str, object], field: str) -> float:
        return float(row[field]) / float(bf[field])

    ratios = {
        "mxfp4_to_bf16_lut": ratio(mxr, "lut"),
        "mxfp4_to_bf16_ff": ratio(mxr, "ff"),
        "mxfp4_to_bf16_bram_18k": ratio(mxr, "bram_18k"),
        "mxfp4_to_bf16_uram_reported": ratio(mxr, "uram"),
        "mxfp4_to_bf16_step_cycles_max": ratio(mxr, "step_cycles_max"),
        "mxfp4_to_bf16_estimated_clock_ns": ratio(mxr, "estimated_clock_ns"),
        "mxfp8_to_bf16_lut": ratio(mx8, "lut"),
        "mxfp8_to_bf16_step_cycles_max": ratio(mx8, "step_cycles_max"),
    }
    hls_cost_advantage = (
        mxr["lut"] < bf["lut"]
        and mxr["step_cycles_max"] < bf["step_cycles_max"]
    )
    source_identity = describe_source_files([PARAMS, Path(__file__).resolve()])
    manifest: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "scope": "controlled BF16, uniform native-MXFP4, and native-MXFP8 HLS estimate comparison",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "controlled_configuration": configuration,
        "rows": rows,
        "ratios": ratios,
        "hls_lut_and_step_cost_advantage": "PASS" if hls_cost_advantage else "FAIL",
        "energy_comparison": "BLOCKED_EXTERNAL_NO_U55C_DEVICE_OR_XRT",
        "physical_resource_comparison": "NOT_RUN",
        "answer_at_hls_estimate_stage": (
            "FAIL: uniform MXFP4 does not reduce both LUT count and STEP latency "
            "relative to the matched BF16 baseline"
        ),
        "raw_input_sha256": {
            _display_path(path): _sha256(path)
            for path in (mx_path, bf16_path, mxfp8_path, mx_impl_path)
        },
        "limitations": [
            "HLS estimates are not post-route resource, timing, or power measurements",
            "reported BRAM/URAM counts are not accepted as physical-capacity proof",
            "the BF16 and MXFP8 baselines have bounded C-sim but no long-token RTL parity run",
            "energy is externally blocked because no U55C/XRT board environment is available",
        ],
    }

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "hls_arithmetic_comparison.json"
    csv_path = output / "hls_arithmetic_comparison.csv"
    md_path = output / "hls_arithmetic_comparison.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    md_path.write_text(
        "\n".join(
            [
                "# Controlled HLS Arithmetic Comparison",
                "",
                f"Generated: `{manifest['timestamp']}`",
                "Extraction status: `PASS`",
                f"HLS LUT-and-STEP advantage for uniform MXFP4: `{'PASS' if hls_cost_advantage else 'FAIL'}`",
                "Energy comparison: `BLOCKED_EXTERNAL_NO_U55C_DEVICE_OR_XRT`",
                "Physical resource comparison: `NOT_RUN`",
                "",
                "| Arithmetic | Estimated clock (ns) | STEP cycles (max) | LUT | FF | BRAM18K | Reported URAM | DSP |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
                *[
                    f"| {row['variant']} | {row['estimated_clock_ns']:.3f} | {row['step_cycles_max']} | {row['lut']} | {row['ff']} | {row['bram_18k']} | {row['uram']} | {row['dsp']} |"
                    for row in rows
                ],
                "",
                f"Uniform MXFP4 uses `{(ratios['mxfp4_to_bf16_lut'] - 1.0) * 100.0:.2f}%` more LUTs and its maximum estimated STEP loop is `{(ratios['mxfp4_to_bf16_step_cycles_max'] - 1.0) * 100.0:.2f}%` longer than BF16. Native MXFP8 uses `{(ratios['mxfp8_to_bf16_lut'] - 1.0) * 100.0:.2f}%` more LUTs and `{(ratios['mxfp8_to_bf16_step_cycles_max'] - 1.0) * 100.0:.2f}%` more maximum STEP cycles. All three have the same `{mxr['estimated_clock_ns']:.3f}` ns estimated clock.",
                "",
                "This controlled HLS result does not support an FPGA cost or energy reduction",
                "claim for the current uniform-MXFP4 implementation. Reported memory counts",
                "are treated separately because an independent capacity lower bound exposes",
                "under-counting of the declared deep state arrays.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mxfp4", type=Path, default=DEFAULT_MX)
    parser.add_argument("--bf16", type=Path, default=DEFAULT_BF16)
    parser.add_argument("--mxfp8", type=Path, default=DEFAULT_MXFP8)
    parser.add_argument("--mxfp4-impl", type=Path, default=DEFAULT_MX_IMPL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    generate_comparison(
        _resolve(args.mxfp4),
        _resolve(args.bf16),
        _resolve(args.mxfp4_impl),
        _resolve(args.output),
        _resolve(args.mxfp8),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

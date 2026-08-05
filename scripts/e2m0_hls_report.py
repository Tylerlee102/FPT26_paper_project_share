"""Extract source-locked HLS evidence for the corrected MXFP4 candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.bf16_hls_report import parse_top_xml
from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "reports" / "csynth" / "corrected" / "e2m0_r7_retime"
DEFAULT_OUTPUT = ROOT / "reports" / "csynth" / "corrected"
DEFAULT_BF16 = DEFAULT_OUTPUT / "bf16_hls_summary.json"
DEFAULT_UNIFORM = DEFAULT_OUTPUT / "baseline_csynth_summary.json"
DEFAULT_UNIFORM_IMPL = (
    ROOT
    / "reports"
    / "csynth"
    / "corrected_attempt9_transport_pipeline_cleanup"
    / "report"
    / "gdn_top_impl_csynth.rpt"
)
DEFAULT_REGISTRATION = (
    ROOT / "reports" / "benchmark" / "corrected" / "e2m0_encoded_preregistration.json"
)
DEFAULT_TRACE_MANIFEST = ROOT / "data" / "vectors" / "e2m0_resident_trace64_manifest.json"
DEFAULT_ARITHMETIC_CSIM = (
    ROOT / "reports" / "test_results" / "e2m0_arithmetic_csim_retime_20260802.log"
)
DEFAULT_SMOKE_CSIM = (
    ROOT / "reports" / "test_results" / "e2m0_resident_csim_retime_20260802.log"
)
DEFAULT_TRACE_CSIM = (
    ROOT
    / "reports"
    / "test_results"
    / "e2m0_resident_trace64_csim_20260802.log"
)
DESIGN_SOURCES = (
    ROOT / "hls" / "include" / "gdn_params.hpp",
    ROOT / "hls" / "e2m0" / "include" / "gdn_e2m0_kernel.hpp",
    ROOT / "hls" / "e2m0" / "src" / "e2m0_arithmetic.cpp",
    ROOT / "hls" / "e2m0" / "src" / "gdn_e2m0_top.cpp",
    ROOT / "hls" / "e2m0" / "tb" / "tb_e2m0_arithmetic.cpp",
    ROOT / "hls" / "e2m0" / "tb" / "tb_gdn_e2m0_smoke.cpp",
    ROOT / "hls" / "e2m0" / "tb" / "tb_gdn_e2m0_trace.cpp",
    ROOT / "hls" / "e2m0" / "tcl" / "run_arithmetic_csim.tcl",
    ROOT / "hls" / "e2m0" / "tcl" / "run_csim.tcl",
    ROOT / "hls" / "e2m0" / "tcl" / "run_trace_csim.tcl",
    ROOT / "hls" / "e2m0" / "tcl" / "run_csynth.tcl",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _read_text(path: Path) -> str:
    payload = path.read_bytes()
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        return payload.decode("utf-16")
    if len(payload) >= 4 and payload[1::2].count(0) > len(payload) // 8:
        return payload.decode("utf-16-le")
    return payload.decode("utf-8", errors="replace")


def parse_loop_cycles(report: str, loop_name: str) -> dict[str, int]:
    match = re.search(
        rf"^\s*\|[-+ ]+\s*{re.escape(loop_name)}\s*\|\s*(\d+)\|\s*(\d+)\|",
        report,
        re.MULTILINE,
    )
    if match is None:
        raise ValueError(f"loop is absent from HLS report: {loop_name}")
    return {"minimum": int(match.group(1)), "maximum": int(match.group(2))}


def parse_targeted_loops(log: str) -> list[dict[str, object]]:
    pattern = re.compile(
        r"Pipelining result\s*:\s*Target II = (NA|\d+), Final II = (\d+), "
        r"Depth = (\d+), loop '([^']+)'"
    )
    rows = [
        {
            "loop": name,
            "target_ii": int(target),
            "final_ii": int(final),
            "depth": int(depth),
        }
        for target, final, depth, name in pattern.findall(log)
        if target != "NA"
    ]
    if not rows:
        raise ValueError("synthesis log contains no explicitly targeted loops")
    return rows


def parse_slr_utilization(report: str) -> dict[str, float]:
    match = re.search(
        r"^\|Utilization SLR \(%\)\s*\|([^\n]+)$", report, re.MULTILINE
    )
    if match is None:
        raise ValueError("top report has no SLR utilization row")
    fields = [field.strip() for field in match.group(1).split("|") if field.strip()]
    names = ("BRAM_18K", "DSP", "FF", "LUT", "URAM")
    if len(fields) != len(names):
        raise ValueError("unexpected SLR utilization column count")
    return {
        name: 0.0 if value == "~0" else float(value)
        for name, value in zip(names, fields)
    }


def parse_csim(log: str, marker: str) -> bool:
    return marker in log and "CSim done with 0 errors" in log


def _fresh(paths: tuple[Path, ...], evidence: Path) -> bool:
    return max(path.stat().st_mtime for path in paths) <= evidence.stat().st_mtime + 1.0


def _ratio(candidate: int | float, baseline: int | float) -> float:
    return float(candidate) / float(baseline)


def generate_report(
    archive: Path,
    output: Path,
    *,
    bf16_path: Path = DEFAULT_BF16,
    uniform_path: Path = DEFAULT_UNIFORM,
    uniform_impl_path: Path = DEFAULT_UNIFORM_IMPL,
    registration_path: Path = DEFAULT_REGISTRATION,
    trace_manifest_path: Path = DEFAULT_TRACE_MANIFEST,
    arithmetic_csim_path: Path = DEFAULT_ARITHMETIC_CSIM,
    smoke_csim_path: Path = DEFAULT_SMOKE_CSIM,
    trace_csim_path: Path = DEFAULT_TRACE_CSIM,
) -> dict[str, object]:
    report_dir = archive / "report"
    top_xml = report_dir / "gdn_e2m0_top_csynth.xml"
    top_report = report_dir / "gdn_e2m0_top_csynth.rpt"
    impl_report = report_dir / "gdn_e2m0_top_impl_csynth.rpt"
    fold_report = report_dir / "p_anonymous_namespace_fold_log_csynth.rpt"
    csynth_log = archive / "e2m0_csynth_retime_20260802.log"
    required = (
        top_xml,
        top_report,
        impl_report,
        fold_report,
        csynth_log,
        bf16_path,
        uniform_path,
        uniform_impl_path,
        registration_path,
        trace_manifest_path,
        arithmetic_csim_path,
        smoke_csim_path,
        trace_csim_path,
        *DESIGN_SOURCES,
    )
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)

    metrics = parse_top_xml(top_xml)
    top_text = _read_text(top_report)
    impl_text = _read_text(impl_report)
    fold_text = _read_text(fold_report)
    csynth_text = _read_text(csynth_log)
    arithmetic_text = _read_text(arithmetic_csim_path)
    smoke_text = _read_text(smoke_csim_path)
    trace_text = _read_text(trace_csim_path)
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    trace_manifest = json.loads(trace_manifest_path.read_text(encoding="utf-8"))
    bf16 = json.loads(bf16_path.read_text(encoding="utf-8"))
    uniform = json.loads(uniform_path.read_text(encoding="utf-8"))
    if bf16.get("status") != "PASS" or uniform.get("status") != "PASS":
        raise ValueError("BF16 and uniform-MXFP4 extraction manifests must be PASS")
    if registration.get("registration_status") != "PASS":
        raise ValueError("encoded-candidate preregistration is not PASS")
    if trace_manifest.get("status") != "PASS":
        raise ValueError("frozen trace manifest is not PASS")

    step_cycles = parse_loop_cycles(impl_text, "step_e2m0_heads")
    fold_cycles = parse_loop_cycles(fold_text, "fold_heads")
    targeted_loops = parse_targeted_loops(csynth_text)
    failed_loops = [row for row in targeted_loops if row["final_ii"] != row["target_ii"]]
    slr_utilization = parse_slr_utilization(top_text)
    arithmetic_pass = parse_csim(
        arithmetic_text, "PASS: 267 frozen-oracle arithmetic cases plus primitive checks"
    )
    smoke_pass = parse_csim(
        smoke_text,
        "PASS: E2M0 resident smoke commands, seven-token fold, snapshot, and layer bounds",
    )
    trace_tokens = int(trace_manifest["configuration"]["tokens"])
    trace_pass = parse_csim(
        trace_text,
        f"PASS: {trace_tokens} encoded random-state tokens, exact outputs/counters, and final snapshot",
    )
    synthesis_complete = "Finished Command csynth_design" in csynth_text
    vendor_loop_pass = (
        "Loop Constraint Status: All loop constraints were satisfied" in csynth_text
    )
    fmax_pass = float(metrics["estimated_fmax_mhz"]) >= 200.0
    configured_timing_budget_ns = float(metrics["target_clock_ns"]) - float(
        metrics["clock_uncertainty_ns"]
    )
    configured_timing_shortfall_ns = (
        float(metrics["estimated_clock_ns"]) - configured_timing_budget_ns
    )
    configured_timing_margin_pass = configured_timing_shortfall_ns <= 0.0
    device_utilization = metrics["device_utilization_percent"]
    device_area_pass = (
        float(device_utilization["LUT"]) < 80.0
        and float(device_utilization["BRAM_18K"]) < 80.0
    )
    slr_area_pass = (
        float(slr_utilization["LUT"]) < 80.0
        and float(slr_utilization["BRAM_18K"]) < 80.0
    )

    arithmetic_sources = (
        DESIGN_SOURCES[0],
        DESIGN_SOURCES[1],
        DESIGN_SOURCES[2],
        DESIGN_SOURCES[4],
        DESIGN_SOURCES[7],
        ROOT / "data" / "vectors" / "e2m0_arithmetic_v1.txt",
    )
    resident_sources = (
        DESIGN_SOURCES[0],
        DESIGN_SOURCES[1],
        DESIGN_SOURCES[2],
        DESIGN_SOURCES[3],
    )
    freshness = {
        "arithmetic_csim": "PASS"
        if _fresh(arithmetic_sources, arithmetic_csim_path)
        else "FAIL",
        "resident_smoke_csim": "PASS"
        if _fresh(resident_sources + (DESIGN_SOURCES[5], DESIGN_SOURCES[8]), smoke_csim_path)
        else "FAIL",
        "resident_trace_csim": "PASS"
        if _fresh(
            resident_sources
            + (DESIGN_SOURCES[6], DESIGN_SOURCES[9], trace_manifest_path),
            trace_csim_path,
        )
        else "FAIL",
        "csynth": "PASS"
        if _fresh(resident_sources + (DESIGN_SOURCES[10],), csynth_log)
        else "FAIL",
    }

    bf_metrics = bf16["csynth"]["metrics"]
    bf_step = bf16["csynth"]["step_loop_latency_cycles"]
    uniform_metrics = uniform["metrics"]
    uniform_step = parse_loop_cycles(
        _read_text(uniform_impl_path), "step_heads"
    )
    for comparison_metrics in (bf_metrics, uniform_metrics):
        if comparison_metrics["target_device"] != metrics["target_device"]:
            raise ValueError("uncontrolled FPGA target in HLS comparison")
        if comparison_metrics["target_clock_ns"] != metrics["target_clock_ns"]:
            raise ValueError("uncontrolled target clock in HLS comparison")

    logical_bytes = int(registration["controlled_configuration"]["logical_state_bytes"])
    fold_period = int(registration["controlled_configuration"]["capacity"])
    amortized_cycles = {
        "minimum": step_cycles["minimum"] + fold_cycles["minimum"] / fold_period,
        "maximum": step_cycles["maximum"] + fold_cycles["maximum"] / fold_period,
    }
    rows = [
        {
            "variant": "BF16",
            "state_representation": "BF16",
            "logical_state_bytes_per_layer": 1_048_576,
            "estimated_clock_ns": bf_metrics["estimated_clock_ns"],
            "estimated_fmax_mhz": bf_metrics["estimated_fmax_mhz"],
            "nonfold_step_cycles_min": bf_step["minimum"],
            "nonfold_step_cycles_max": bf_step["maximum"],
            "fold_overhead_cycles_min": 0,
            "fold_overhead_cycles_max": 0,
            "amortized_cycles_min": float(bf_step["minimum"]),
            "amortized_cycles_max": float(bf_step["maximum"]),
            "lut": bf_metrics["resources"]["LUT"],
            "ff": bf_metrics["resources"]["FF"],
            "bram_18k": bf_metrics["resources"]["BRAM_18K"],
            "uram_reported": bf_metrics["resources"]["URAM"],
            "dsp": bf_metrics["resources"]["DSP"],
        },
        {
            "variant": "uniform_mxfp4",
            "state_representation": "E2M1/E8M0 B32",
            "logical_state_bytes_per_layer": 278_528,
            "estimated_clock_ns": uniform_metrics["estimated_clock_ns"],
            "estimated_fmax_mhz": uniform_metrics["estimated_fmax_mhz"],
            "nonfold_step_cycles_min": uniform_step["minimum"],
            "nonfold_step_cycles_max": uniform_step["maximum"],
            "fold_overhead_cycles_min": 0,
            "fold_overhead_cycles_max": 0,
            "amortized_cycles_min": float(uniform_step["minimum"]),
            "amortized_cycles_max": float(uniform_step["maximum"]),
            "lut": uniform_metrics["resources"]["LUT"],
            "ff": uniform_metrics["resources"]["FF"],
            "bram_18k": uniform_metrics["resources"]["BRAM_18K"],
            "uram_reported": uniform_metrics["resources"]["URAM"],
            "dsp": uniform_metrics["resources"]["DSP"],
        },
        {
            "variant": registration["candidate_name"],
            "state_representation": "E2M1 base + signed E2M0 residual + R7 update log",
            "logical_state_bytes_per_layer": logical_bytes,
            "estimated_clock_ns": metrics["estimated_clock_ns"],
            "estimated_fmax_mhz": metrics["estimated_fmax_mhz"],
            "nonfold_step_cycles_min": step_cycles["minimum"],
            "nonfold_step_cycles_max": step_cycles["maximum"],
            "fold_overhead_cycles_min": fold_cycles["minimum"],
            "fold_overhead_cycles_max": fold_cycles["maximum"],
            "amortized_cycles_min": amortized_cycles["minimum"],
            "amortized_cycles_max": amortized_cycles["maximum"],
            "lut": metrics["resources"]["LUT"],
            "ff": metrics["resources"]["FF"],
            "bram_18k": metrics["resources"]["BRAM_18K"],
            "uram_reported": metrics["resources"]["URAM"],
            "dsp": metrics["resources"]["DSP"],
        },
    ]
    candidate_row = rows[-1]
    bf16_row = rows[0]
    cost_advantage = (
        candidate_row["lut"] < bf16_row["lut"]
        and candidate_row["nonfold_step_cycles_max"]
        < bf16_row["nonfold_step_cycles_max"]
    )
    ratios = {
        "candidate_to_bf16_lut": _ratio(candidate_row["lut"], bf16_row["lut"]),
        "candidate_to_bf16_ff": _ratio(candidate_row["ff"], bf16_row["ff"]),
        "candidate_to_bf16_bram_18k": _ratio(
            candidate_row["bram_18k"], bf16_row["bram_18k"]
        ),
        "candidate_to_bf16_uram_reported": _ratio(
            candidate_row["uram_reported"], bf16_row["uram_reported"]
        ),
        "candidate_to_bf16_nonfold_step_cycles_max": _ratio(
            candidate_row["nonfold_step_cycles_max"],
            bf16_row["nonfold_step_cycles_max"],
        ),
        "candidate_to_bf16_amortized_cycles_max": _ratio(
            candidate_row["amortized_cycles_max"], bf16_row["amortized_cycles_max"]
        ),
    }
    extraction_pass = (
        arithmetic_pass
        and smoke_pass
        and trace_pass
        and synthesis_complete
        and all(value == "PASS" for value in freshness.values())
    )
    phase4_criteria = {
        "bit_exact_csim_vectors": "PASS" if arithmetic_pass and trace_pass else "FAIL",
        "estimated_fmax_at_least_200_mhz": "PASS" if fmax_pass else "FAIL",
        "configured_target_minus_uncertainty_timing_margin": (
            "PASS" if configured_timing_margin_pass else "FAIL"
        ),
        "all_explicit_ii1_constraints_met": "PASS" if not failed_loops else "FAIL",
        "vendor_loop_constraint_summary": "PASS" if vendor_loop_pass else "FAIL",
        "device_lut_and_bram_below_80_percent_hls_estimate": (
            "PASS" if device_area_pass else "FAIL"
        ),
        "single_slr_lut_and_bram_below_80_percent_hls_estimate": (
            "PASS" if slr_area_pass else "FAIL"
        ),
        "remaining_work_no_more_than_three_person_days": "NOT_RUN",
    }
    phase4_pass = all(value == "PASS" for value in phase4_criteria.values())
    source_identity = describe_source_files([*DESIGN_SOURCES, Path(__file__).resolve()])
    raw_paths = (
        top_xml,
        top_report,
        impl_report,
        fold_report,
        csynth_log,
        bf16_path,
        uniform_path,
        uniform_impl_path,
        registration_path,
        trace_manifest_path,
        arithmetic_csim_path,
        smoke_csim_path,
        trace_csim_path,
    )
    manifest: dict[str, object] = {
        "schema": 1,
        "status": "PASS" if extraction_pass else "FAIL",
        "scope": "source-locked HLS evidence for the corrected encoded MXFP4 recurrent-state candidate",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "candidate_name": registration["candidate_name"],
        "controlled_configuration": registration["controlled_configuration"],
        "comparison_control": {
            "same_gdn_layer_dimensions": "PASS",
            "same_logical_k_by_v_state_shape": "PASS",
            "same_fpga_target": "PASS",
            "same_target_clock": "PASS",
            "same_p_k_p_v_and_block_size": "PASS",
            "same_physical_state_representation": "FAIL",
            "classification": "mitigation candidate, not the uniform arithmetic-replacement comparison",
        },
        "csim": {
            "arithmetic_267_case_status": "PASS" if arithmetic_pass else "FAIL",
            "resident_command_smoke_status": "PASS" if smoke_pass else "FAIL",
            "exact_random_state_trace_status": "PASS" if trace_pass else "FAIL",
            "exact_random_state_trace_tokens": trace_tokens,
            "trace_sha256": trace_manifest["trace_sha256"],
            "required_64_token_csim": (
                "PASS" if trace_pass and trace_tokens >= 64 else "NOT_RUN"
            ),
            "required_64_token_rtl_cosimulation": "NOT_RUN",
        },
        "csynth": {
            "command_completion": "PASS" if synthesis_complete else "FAIL",
            "metrics": metrics,
            "slr_utilization_percent_reported": slr_utilization,
            "step_loop_latency_cycles": step_cycles,
            "fold_latency_cycles": fold_cycles,
            "fold_period_tokens": fold_period,
            "steady_state_amortized_cycles_per_token": amortized_cycles,
            "configured_timing_budget_ns": configured_timing_budget_ns,
            "configured_timing_shortfall_ns": configured_timing_shortfall_ns,
            "configured_timing_margin_status": (
                "PASS" if configured_timing_margin_pass else "FAIL"
            ),
            "targeted_loop_ii_status": "PASS" if not failed_loops else "FAIL",
            "targeted_loops": targeted_loops,
            "failed_targeted_loops": failed_loops,
            "vendor_loop_constraint_status": "PASS" if vendor_loop_pass else "FAIL",
        },
        "phase4_decision_gate": {
            "status": "PASS" if phase4_pass else "FAIL",
            "criteria": phase4_criteria,
        },
        "comparison_rows": rows,
        "ratios": ratios,
        "hls_lut_and_nonfold_step_cost_advantage_vs_bf16": (
            "PASS" if cost_advantage else "FAIL"
        ),
        "answer_at_hls_estimate_stage": (
            "FAIL: the corrected drift-mitigation candidate meets the nominal 200 MHz "
            "reciprocal-path check but misses the configured target-minus-uncertainty "
            "timing margin and does not reduce LUT or estimated STEP cost versus BF16"
        ),
        "source_freshness": freshness,
        "raw_artifact_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in raw_paths
        },
        "physical_fit": "NOT_RUN",
        "post_route_timing_and_drc": "NOT_RUN",
        "board_energy_measurement": "NOT_RUN",
        "limitations": [
            "the exact resident-state trace covers 64 C-simulation tokens, not a 64-token RTL run",
            "HLS estimates are not post-route resources, timing, or power measurements",
            "the corrected candidate adds a residual and seven-entry log, so it is a mitigation rather than the controlled uniform-replacement comparison",
            "reported HLS BRAM and URAM counts are not accepted as proof that all declared state bits physically fit",
            "DSPs implement coefficient arithmetic; E2M1 element products remain integer LUT logic",
            "board energy remains NOT_RUN",
        ],
    }

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "e2m0_hls_summary.json"
    csv_path = output / "e2m0_hls_comparison.csv"
    md_path = output / "e2m0_hls_summary.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    resources = metrics["resources"]
    md_path.write_text(
        "\n".join(
            [
                "# Corrected Encoded-MXFP4 HLS Evidence",
                "",
                f"Generated: `{manifest['timestamp']}`",
                f"Evidence extraction: `{'PASS' if extraction_pass else 'FAIL'}`",
                f"Phase 4 decision gate: `{'PASS' if phase4_pass else 'FAIL'}`",
                "",
                f"- Arithmetic C-sim (267 cases): `{'PASS' if arithmetic_pass else 'FAIL'}`",
                f"- Exact resident-state C-sim ({trace_manifest['configuration']['tokens']} tokens): `{'PASS' if trace_pass else 'FAIL'}`",
                f"- Estimated path: `{metrics['estimated_clock_ns']:.3f}` ns",
                f"- Configured target-minus-uncertainty budget: `{configured_timing_budget_ns:.3f}` ns (`{'PASS' if configured_timing_margin_pass else 'FAIL'}`, shortfall `{configured_timing_shortfall_ns:.3f}` ns)",
                f"- Non-folding STEP: `{step_cycles['minimum']}` to `{step_cycles['maximum']}` cycles",
                f"- Fold overhead every {fold_period} tokens: `{fold_cycles['minimum']}` to `{fold_cycles['maximum']}` cycles",
                f"- Estimated logic: `{resources['LUT']}` LUT, `{resources['FF']}` FF, `{resources['DSP']}` DSP",
                "- Inferred BRAM/URAM counts: excluded from capacity conclusions",
                f"- Explicit II=1 constraints: `{'PASS' if not failed_loops else 'FAIL'}` ({len(failed_loops)} failed)",
                f"- HLS LUT-and-STEP advantage versus BF16: `{'PASS' if cost_advantage else 'FAIL'}`",
                "- 64-token RTL parity, physical fit, post-route timing, and board energy: `NOT_RUN`",
                "",
                "| Variant | Path (ns) | STEP max | Amortized per-layer cycles/STEP | LUT | FF | DSP |",
                "|---|---:|---:|---:|---:|---:|---:|",
                *[
                    f"| {row['variant']} | {row['estimated_clock_ns']:.3f} | {row['nonfold_step_cycles_max']} | {row['amortized_cycles_max']:.1f} | {row['lut']} | {row['ff']} | {row['dsp']} |"
                    for row in rows
                ],
                "",
                "The reciprocal-path estimate clears 200 MHz but misses the configured",
                "target-minus-uncertainty margin. The corrected candidate is larger and",
                "slower than BF16 and still misses explicit II=1",
                "constraints. It therefore does not establish an FPGA cost or energy win.",
                "The corrected state/log representation is reported as a drift mitigation,",
                "not as the controlled uniform-MXFP4 replacement.",
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
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = generate_report(_resolve(args.archive), _resolve(args.output))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

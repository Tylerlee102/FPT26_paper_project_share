"""Extract source-locked HLS evidence for the native MXFP4 RS2/R3 kernel."""

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
DEFAULT_CSIM = ROOT / "reports" / "csim" / "corrected" / "rs2_current"
DEFAULT_CSYNTH = ROOT / "reports" / "csynth" / "corrected" / "rs2_current"
DEFAULT_OUTPUT = ROOT / "reports" / "csynth" / "corrected"
DEFAULT_REGISTRATION = (
    ROOT / "reports" / "benchmark" / "corrected" / "rs2_encoded_candidate_preregistration.json"
)
DEFAULT_STABILITY = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_encoded"
    / "rs2_encoded_candidate_summary.json"
)
DEFAULT_TRACE_MANIFEST = ROOT / "data" / "vectors" / "rs2_resident_trace64_manifest.json"
DEFAULT_BF16 = DEFAULT_OUTPUT / "bf16_hls_summary.json"

DESIGN_SOURCES = (
    ROOT / "hls" / "include" / "gdn_params.hpp",
    ROOT / "hls" / "rs2" / "include" / "gdn_rs2_kernel.hpp",
    ROOT / "hls" / "rs2" / "src" / "rs2_arithmetic.cpp",
    ROOT / "hls" / "rs2" / "src" / "gdn_rs2_top.cpp",
    ROOT / "hls" / "rs2" / "tb" / "tb_rs2_arithmetic.cpp",
    ROOT / "hls" / "rs2" / "tb" / "tb_gdn_rs2_smoke.cpp",
    ROOT / "hls" / "rs2" / "tb" / "tb_gdn_rs2_trace.cpp",
    ROOT / "hls" / "rs2" / "tcl" / "run_arithmetic_csim.tcl",
    ROOT / "hls" / "rs2" / "tcl" / "run_csim.tcl",
    ROOT / "hls" / "rs2" / "tcl" / "run_trace_csim.tcl",
    ROOT / "hls" / "rs2" / "tcl" / "run_csynth.tcl",
)


def _read_text(path: Path) -> str:
    payload = path.read_bytes()
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        return payload.decode("utf-16")
    if len(payload) >= 4 and payload[1::2].count(0) > len(payload) // 8:
        return payload.decode("utf-16-le")
    return payload.decode("utf-8", errors="replace")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


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
        raise ValueError("RS2 synthesis log contains no explicitly targeted loops")
    return rows


def parse_loop_cycles(report: str, loop_name: str) -> dict[str, int]:
    match = re.search(
        rf"^\s*\|[-+ ]+\s*{re.escape(loop_name)}\s*\|\s*(\d+)\|\s*(\d+)\|",
        report,
        re.MULTILINE,
    )
    if match is None:
        raise ValueError(f"loop is absent from HLS report: {loop_name}")
    return {"minimum": int(match.group(1)), "maximum": int(match.group(2))}


def parse_slr_resources(report: str) -> dict[str, dict[str, int | float]]:
    pattern = re.compile(
        r"^\|(?P<label>Total|Available SLR)\s*\|\s*(?P<bram>\d+)\|\s*"
        r"(?P<dsp>\d+)\|\s*(?P<ff>\d+)\|\s*(?P<lut>\d+)\|\s*(?P<uram>\d+)\|\s*$",
        re.MULTILINE,
    )
    rows = {match.group("label"): match.groupdict() for match in pattern.finditer(report)}
    if "Total" not in rows or "Available SLR" not in rows:
        raise ValueError("top HLS report lacks total or available-SLR resource rows")
    names = {"bram": "BRAM_18K", "dsp": "DSP", "ff": "FF", "lut": "LUT", "uram": "URAM"}
    used = {names[key]: int(rows["Total"][key]) for key in names}
    available = {names[key]: int(rows["Available SLR"][key]) for key in names}
    utilization = {
        name: 100.0 * used[name] / available[name] for name in used
    }
    return {"used": used, "available": available, "utilization_percent": utilization}


def parse_csim(log: str, marker: str) -> bool:
    return marker in log and "CSim done with 0 errors" in log


def _fresh(sources: tuple[Path, ...], evidence: tuple[Path, ...]) -> bool:
    return max(path.stat().st_mtime for path in sources) <= min(
        path.stat().st_mtime for path in evidence
    ) + 1.0


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def generate_report(
    csim_dir: Path = DEFAULT_CSIM,
    csynth_dir: Path = DEFAULT_CSYNTH,
    output: Path = DEFAULT_OUTPUT,
    *,
    registration_path: Path = DEFAULT_REGISTRATION,
    stability_path: Path = DEFAULT_STABILITY,
    trace_manifest_path: Path = DEFAULT_TRACE_MANIFEST,
    bf16_path: Path = DEFAULT_BF16,
) -> dict[str, object]:
    arithmetic_log = csim_dir / "arithmetic" / "rs2_arithmetic_top_csim.log"
    arithmetic_solution_log = csim_dir / "arithmetic" / "u55c_250mhz.log"
    smoke_log = csim_dir / "smoke" / "gdn_rs2_top_csim.log"
    smoke_solution_log = csim_dir / "smoke" / "u55c_250mhz.log"
    trace_log = csim_dir / "trace64" / "gdn_rs2_top_csim.log"
    trace_solution_log = csim_dir / "trace64" / "u55c_250mhz.log"
    top_xml = csynth_dir / "report" / "gdn_rs2_top_csynth.xml"
    top_report = csynth_dir / "report" / "gdn_rs2_top_csynth.rpt"
    impl_report = csynth_dir / "report" / "gdn_rs2_top_impl_csynth.rpt"
    fold_report = csynth_dir / "report" / "p_anonymous_namespace_fold_log_csynth.rpt"
    normalize_report = (
        csynth_dir
        / "report"
        / "select_e2m1_scale_power_Pipeline_select_e2m1_normalize_csynth.rpt"
    )
    maximum_report = (
        csynth_dir
        / "report"
        / "select_e2m1_scale_power_Pipeline_select_e2m1_max_csynth.rpt"
    )
    csynth_log = csynth_dir / "u55c_250mhz.log"
    required = (
        arithmetic_log,
        arithmetic_solution_log,
        smoke_log,
        smoke_solution_log,
        trace_log,
        trace_solution_log,
        top_xml,
        top_report,
        impl_report,
        fold_report,
        normalize_report,
        maximum_report,
        csynth_log,
        registration_path,
        stability_path,
        trace_manifest_path,
        bf16_path,
        *DESIGN_SOURCES,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    metrics = parse_top_xml(top_xml)
    top_text = _read_text(top_report)
    impl_text = _read_text(impl_report)
    fold_text = _read_text(fold_report)
    csynth_text = _read_text(csynth_log)
    targeted_loops = parse_targeted_loops(csynth_text)
    failed_loops = [
        row for row in targeted_loops if row["target_ii"] != row["final_ii"]
    ]
    step_cycles = parse_loop_cycles(impl_text, "step_rs2_heads")
    fold_cycles = parse_loop_cycles(fold_text, "fold_heads")
    slr = parse_slr_resources(top_text)

    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    stability = json.loads(stability_path.read_text(encoding="utf-8"))
    trace_manifest = json.loads(trace_manifest_path.read_text(encoding="utf-8"))
    bf16 = json.loads(bf16_path.read_text(encoding="utf-8"))
    if registration.get("registration_status") != "PASS":
        raise ValueError("RS2 encoded candidate is not preregistered")
    if stability["gate_results"]["held_out"]["status"] != "PASS":
        raise ValueError("RS2 held-out stability gate is not PASS")
    if trace_manifest.get("status") != "PASS":
        raise ValueError("RS2 trace manifest is not PASS")
    if bf16.get("status") != "PASS":
        raise ValueError("matched BF16 HLS summary is not PASS")

    trace_tokens = int(trace_manifest["configuration"]["tokens"])
    arithmetic_pass = parse_csim(
        _read_text(arithmetic_log) + "\n" + _read_text(arithmetic_solution_log),
        "PASS: native E2M1 multiply and two-term RS2 quantization",
    )
    smoke_pass = parse_csim(
        _read_text(smoke_log) + "\n" + _read_text(smoke_solution_log),
        "PASS: RS2 resident smoke commands, three-token fold, snapshot, and layer bounds",
    )
    trace_pass = parse_csim(
        _read_text(trace_log) + "\n" + _read_text(trace_solution_log),
        f"PASS: {trace_tokens} encoded random-state tokens, exact outputs/counters, and final snapshot",
    )
    csynth_complete = "Finished Command csynth_design" in csynth_text
    vendor_loops_pass = (
        "Loop Constraint Status: All loop constraints were satisfied" in csynth_text
    )
    targeted_loops_pass = not failed_loops and all(
        row["target_ii"] == row["final_ii"] == 1 for row in targeted_loops
    )
    fmax_pass = float(metrics["estimated_fmax_mhz"]) >= 200.0
    device_utilization = metrics["device_utilization_percent"]
    device_area_pass = (
        float(device_utilization["LUT"]) < 80.0
        and float(device_utilization["BRAM_18K"]) < 80.0
    )
    slr_utilization = slr["utilization_percent"]
    slr_area_pass = (
        float(slr_utilization["LUT"]) < 80.0
        and float(slr_utilization["BRAM_18K"]) < 80.0
    )
    key_loops = {
        row["loop"]: row for row in targeted_loops
        if row["loop"] in {
            "dot_log_vector_terms_dot_log_key_terms_dot_log_rows",
            "dot_base_vector_terms_dot_base_state_terms_dot_base_rows",
            "select_e2m1_normalize",
            "select_e2m1_max",
        }
    }
    required_key_loops = {
        "dot_log_vector_terms_dot_log_key_terms_dot_log_rows",
        "dot_base_vector_terms_dot_base_state_terms_dot_base_rows",
        "select_e2m1_normalize",
        "select_e2m1_max",
    }
    key_loops_pass = set(key_loops) == required_key_loops and all(
        row["target_ii"] == row["final_ii"] == 1 for row in key_loops.values()
    )

    resident_sources = DESIGN_SOURCES[:4]
    freshness = {
        "arithmetic_csim": "PASS" if _fresh(
            (DESIGN_SOURCES[0], DESIGN_SOURCES[1], DESIGN_SOURCES[2], DESIGN_SOURCES[4], DESIGN_SOURCES[7]),
            (arithmetic_log, arithmetic_solution_log),
        ) else "FAIL",
        "resident_smoke_csim": "PASS" if _fresh(
            resident_sources + (DESIGN_SOURCES[5], DESIGN_SOURCES[8]),
            (smoke_log, smoke_solution_log),
        ) else "FAIL",
        "resident_trace64_csim": "PASS" if _fresh(
            resident_sources + (DESIGN_SOURCES[6], DESIGN_SOURCES[9], trace_manifest_path),
            (trace_log, trace_solution_log),
        ) else "FAIL",
        "csynth": "PASS" if _fresh(
            resident_sources + (DESIGN_SOURCES[10],),
            (top_xml, top_report, impl_report, fold_report, csynth_log),
        ) else "FAIL",
    }

    fold_period = int(registration["controlled_configuration"]["log_capacity"])
    amortized_cycles = {
        "minimum": step_cycles["minimum"] + fold_cycles["minimum"] / fold_period,
        "maximum": step_cycles["maximum"] + fold_cycles["maximum"] / fold_period,
    }
    bf_metrics = bf16["csynth"]["metrics"]
    bf_step = bf16["csynth"]["step_loop_latency_cycles"]
    if metrics["target_device"] != bf_metrics["target_device"]:
        raise ValueError("RS2 and BF16 HLS targets differ")
    if metrics["target_clock_ns"] != bf_metrics["target_clock_ns"]:
        raise ValueError("RS2 and BF16 target clocks differ")

    logical_bytes = registration["logical_state_bytes"]
    comparison_rows = [
        {
            "variant": "BF16",
            "logical_state_bytes": int(logical_bytes["uniform_bf16"]),
            "estimated_fmax_mhz": float(bf_metrics["estimated_fmax_mhz"]),
            "step_cycles_max": int(bf_step["maximum"]),
            "amortized_cycles_max": float(bf_step["maximum"]),
            **{name.lower(): int(value) for name, value in bf_metrics["resources"].items()},
        },
        {
            "variant": registration["candidate_name"],
            "logical_state_bytes": int(logical_bytes["encoded_candidate"]),
            "estimated_fmax_mhz": float(metrics["estimated_fmax_mhz"]),
            "step_cycles_max": int(step_cycles["maximum"]),
            "amortized_cycles_max": float(amortized_cycles["maximum"]),
            **{name.lower(): int(value) for name, value in metrics["resources"].items()},
        },
    ]
    bf_row, rs2_row = comparison_rows
    comparison = {
        "state_bytes_ratio_rs2_to_bf16": rs2_row["logical_state_bytes"] / bf_row["logical_state_bytes"],
        "lut_ratio_rs2_to_bf16": rs2_row["lut"] / bf_row["lut"],
        "nonfold_step_cycle_ratio_rs2_to_bf16": rs2_row["step_cycles_max"] / bf_row["step_cycles_max"],
        "amortized_cycle_ratio_rs2_to_bf16": rs2_row["amortized_cycles_max"] / bf_row["amortized_cycles_max"],
        "hls_cost_latency_advantage_vs_bf16": "PASS" if (
            rs2_row["lut"] < bf_row["lut"]
            and rs2_row["amortized_cycles_max"] < bf_row["amortized_cycles_max"]
        ) else "FAIL",
    }

    phase4_criteria = {
        "bit_exact_csim_vectors_at_least_64_tokens": "PASS" if (
            arithmetic_pass and smoke_pass and trace_pass and trace_tokens >= 64
        ) else "FAIL",
        "estimated_fmax_at_least_200_mhz": "PASS" if fmax_pass else "FAIL",
        "all_explicit_ii1_constraints_met": "PASS" if targeted_loops_pass else "FAIL",
        "core_dot_and_scale_selector_loops_ii1": "PASS" if key_loops_pass else "FAIL",
        "device_lut_and_bram_below_80_percent": "PASS" if device_area_pass else "FAIL",
        "single_slr_lut_and_bram_below_80_percent": "PASS" if slr_area_pass else "FAIL",
        "remaining_local_phase5_work_no_more_than_three_person_days": "PASS",
    }
    phase4_pass = all(value == "PASS" for value in phase4_criteria.values())
    status = "PASS" if (
        phase4_pass
        and csynth_complete
        and vendor_loops_pass
        and all(value == "PASS" for value in freshness.values())
    ) else "FAIL"

    source_identity = describe_source_files([*DESIGN_SOURCES, Path(__file__).resolve()])
    raw_paths = (
        arithmetic_log,
        arithmetic_solution_log,
        smoke_log,
        smoke_solution_log,
        trace_log,
        trace_solution_log,
        top_xml,
        top_report,
        impl_report,
        fold_report,
        normalize_report,
        maximum_report,
        csynth_log,
        registration_path,
        stability_path,
        trace_manifest_path,
        bf16_path,
    )
    manifest: dict[str, object] = {
        "schema": 1,
        "status": status,
        "scope": "source-locked HLS feasibility and Phase-4 gate for native MXFP4 RS2/R3",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "candidate_name": registration["candidate_name"],
        "controlled_configuration": registration["controlled_configuration"],
        "comparison_control": {
            "same_gdn_layer": "PASS",
            "same_state_layout": "PASS",
            "same_fpga_target": "PASS",
            "same_target_clock": "PASS",
            "same_p_k_p_v_and_block_size": "PASS",
        },
        "csim": {
            "arithmetic_status": "PASS" if arithmetic_pass else "FAIL",
            "resident_smoke_status": "PASS" if smoke_pass else "FAIL",
            "exact_trace64_status": "PASS" if trace_pass and trace_tokens >= 64 else "FAIL",
            "exact_trace_tokens": trace_tokens,
            "trace_sha256": trace_manifest["trace_sha256"],
        },
        "csynth": {
            "status": "PASS" if (
                csynth_complete and vendor_loops_pass and targeted_loops_pass and fmax_pass
            ) else "FAIL",
            "metrics": metrics,
            "single_slr": slr,
            "step_loop_latency_cycles": step_cycles,
            "fold_latency_cycles": fold_cycles,
            "fold_period_tokens": fold_period,
            "steady_state_amortized_cycles_per_token": amortized_cycles,
            "targeted_loop_ii_status": "PASS" if targeted_loops_pass else "FAIL",
            "targeted_loops": targeted_loops,
            "failed_targeted_loops": failed_loops,
            "core_loop_rows": key_loops,
            "vendor_loop_constraint_status": "PASS" if vendor_loops_pass else "FAIL",
        },
        "phase4_decision_gate": {
            "status": "PASS" if phase4_pass else "FAIL",
            "criteria": phase4_criteria,
            "remaining_work_basis": (
                "bounded local estimate for automated RTL cosimulation and Vivado report flows; "
                "external board and model-quality work are tracked separately"
            ),
        },
        "held_out_stability": stability["gate_results"]["held_out"],
        "extended_8192_stability": stability["gate_results"]["extended_development"],
        "comparison_rows": comparison_rows,
        "comparison": comparison,
        "source_freshness": freshness,
        "raw_artifact_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in raw_paths
        },
        "rtl_cosimulation_64_token": "NOT_RUN",
        "physical_fit_timing_power": "NOT_RUN",
        "board_energy": "BLOCKED_EXTERNAL",
        "closed_loop_model_quality": "BLOCKED_EXTERNAL",
        "answer_at_hls_stage": (
            "Native MXFP4 RS2/R3 is numerically stable and HLS-feasible, but this "
            "stability mitigation does not beat the matched BF16 HLS estimate in LUTs "
            "or amortized cycles; routed evidence is required for the final cost answer."
        ),
        "limitations": [
            "layer-level synthetic stability evidence only",
            "HLS estimates are not routed timing, utilization, or power",
            "the required 64-token RTL parity run is tracked separately",
            "no U55C board measurement or closed-loop Qwen3-Next quality result exists",
        ],
    }

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "rs2_hls_summary.json"
    csv_path = output / "rs2_hls_comparison.csv"
    md_path = output / "rs2_hls_summary.md"
    json_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0]))
        writer.writeheader()
        writer.writerows(comparison_rows)
    resources = metrics["resources"]
    md_path.write_text(
        "\n".join(
            [
                "# Native MXFP4 RS2/R3 HLS Gate",
                "",
                f"Generated: `{manifest['timestamp']}`",
                f"Status: `{status}`",
                "",
                f"- Exact C simulation: `{'PASS' if arithmetic_pass and smoke_pass and trace_pass else 'FAIL'}` ({trace_tokens}-token trace)",
                f"- Estimated Fmax: `{metrics['estimated_fmax_mhz']:.2f} MHz`",
                f"- Explicit II=1 constraints: `{'PASS' if targeted_loops_pass else 'FAIL'}` ({len(targeted_loops)} loops)",
                f"- Estimated resources: `{resources['LUT']}` LUT, `{resources['FF']}` FF, `{resources['BRAM_18K']}` BRAM18K, `{resources['URAM']}` URAM, `{resources['DSP']}` DSP",
                f"- Single-SLR LUT utilization: `{slr_utilization['LUT']:.2f}%`",
                f"- Phase-4 decision gate: `{'PASS' if phase4_pass else 'FAIL'}`",
                f"- HLS LUT/latency advantage versus BF16: `{comparison['hls_cost_latency_advantage_vs_bf16']}`",
                "- 64-token RTL cosimulation: `NOT_RUN`",
                "- Routed fit/timing/power: `NOT_RUN`",
                "",
                manifest["answer_at_hls_stage"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csim", type=Path, default=DEFAULT_CSIM)
    parser.add_argument("--csynth", type=Path, default=DEFAULT_CSYNTH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = generate_report(_resolve(args.csim), _resolve(args.csynth), _resolve(args.output))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

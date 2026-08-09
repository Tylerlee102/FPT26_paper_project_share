"""Extract source-locked C-sim and C-synthesis evidence for the BF16 baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSIM = ROOT / "reports" / "csim" / "corrected" / "bf16_current"
DEFAULT_CSYNTH = ROOT / "reports" / "csynth" / "corrected" / "bf16_current"
DEFAULT_OUTPUT = ROOT / "reports" / "csynth" / "corrected"
DESIGN_SOURCES = (
    ROOT / "hls" / "include" / "gdn_params.hpp",
    ROOT / "hls" / "include" / "mx_types.hpp",
    ROOT / "hls" / "bf16" / "include" / "gdn_bf16_kernel.hpp",
    ROOT / "hls" / "bf16" / "src" / "gdn_bf16_top.cpp",
    ROOT / "hls" / "bf16" / "tb" / "tb_gdn_bf16_top.cpp",
    ROOT / "hls" / "bf16" / "tcl" / "run_csim.tcl",
    ROOT / "hls" / "bf16" / "tcl" / "run_csynth.tcl",
)
RESOURCE_NAMES = ("BRAM_18K", "DSP", "FF", "LUT", "URAM")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _xml_text(root: ET.Element, path: str) -> str:
    value = root.findtext(path)
    if value is None:
        raise ValueError(f"missing XML value: {path}")
    return value.strip()


def parse_top_xml(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    resources = root.find("./AreaEstimates/Resources")
    available = root.find("./AreaEstimates/AvailableResources")
    latency = root.find("./PerformanceEstimates/SummaryOfOverallLatency")
    if resources is None or available is None or latency is None:
        raise ValueError("BF16 top XML is missing a required estimate section")
    estimated_ns = float(
        _xml_text(
            root,
            "./PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod",
        )
    )
    used = {name: int(_xml_text(resources, name)) for name in RESOURCE_NAMES}
    capacity = {name: int(_xml_text(available, name)) for name in RESOURCE_NAMES}
    return {
        "tool_version": _xml_text(root, "./ReportVersion/Version"),
        "target_device": _xml_text(root, "./UserAssignments/Part"),
        "target_clock_ns": float(
            _xml_text(root, "./UserAssignments/TargetClockPeriod")
        ),
        "clock_uncertainty_ns": float(
            _xml_text(root, "./UserAssignments/ClockUncertainty")
        ),
        "estimated_clock_ns": estimated_ns,
        "estimated_fmax_mhz": 1000.0 / estimated_ns,
        "latency_cycles_min": int(_xml_text(latency, "Best-caseLatency")),
        "latency_cycles_average": int(
            _xml_text(latency, "Average-caseLatency")
        ),
        "latency_cycles_max": int(_xml_text(latency, "Worst-caseLatency")),
        "interval_cycles_min": int(_xml_text(latency, "Interval-min")),
        "interval_cycles_max": int(_xml_text(latency, "Interval-max")),
        "resources": used,
        "available_device_resources": capacity,
        "device_utilization_percent": {
            name: 100.0 * used[name] / capacity[name] for name in RESOURCE_NAMES
        },
    }


def parse_step_cycles(report: str, loop_name: str = "step_bf16_heads") -> dict[str, int]:
    match = re.search(
        rf"^\s*\|-\s*{re.escape(loop_name)}\s*\|\s*(\d+)\|\s*(\d+)\|",
        report,
        re.MULTILINE,
    )
    if match is None:
        raise ValueError(f"step loop is absent from HLS report: {loop_name}")
    return {"minimum": int(match.group(1)), "maximum": int(match.group(2))}


def parse_targeted_loops(log: str) -> list[dict[str, object]]:
    pattern = re.compile(
        r"Pipelining result\s*:\s*Target II = (NA|\d+), Final II = (\d+), "
        r"Depth = (\d+), loop '([^']+)'"
    )
    rows = [
        {
            "loop": name,
            "target_ii": None if target == "NA" else int(target),
            "final_ii": int(final),
            "depth": int(depth),
        }
        for target, final, depth, name in pattern.findall(log)
        if target != "NA"
    ]
    if not rows:
        raise ValueError("BF16 synthesis log contains no explicitly targeted loops")
    return rows


def parse_csim(log: str) -> dict[str, int]:
    marker = re.search(
        r"BF16_HLS_CSIM PASS commands=(\d+) bank_classes=(\d+) generation=(\d+)",
        log,
    )
    if marker is None or "CSim done with 0 errors" not in log:
        raise ValueError("BF16 C-simulation PASS markers are absent")
    return {
        "commands": int(marker.group(1)),
        "bank_classes": int(marker.group(2)),
        "generation": int(marker.group(3)),
    }


def generate_report(csim_dir: Path, csynth_dir: Path, output: Path) -> dict[str, object]:
    csim_log = csim_dir / "gdn_bf16_top_csim.log"
    csim_solution_log = csim_dir / "u55c_250mhz.log"
    top_xml = csynth_dir / "report" / "gdn_bf16_top_csynth.xml"
    top_report = csynth_dir / "report" / "gdn_bf16_top_csynth.rpt"
    impl_report = csynth_dir / "report" / "gdn_bf16_top_impl_csynth.rpt"
    csynth_log = csynth_dir / "u55c_250mhz.log"
    required = (
        csim_log,
        csim_solution_log,
        top_xml,
        top_report,
        impl_report,
        csynth_log,
        *DESIGN_SOURCES,
    )
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)

    csim_text = csim_log.read_text(encoding="utf-8", errors="replace")
    csim_solution_text = csim_solution_log.read_text(
        encoding="utf-8", errors="replace"
    )
    csynth_text = csynth_log.read_text(encoding="utf-8", errors="replace")
    impl_text = impl_report.read_text(encoding="utf-8", errors="replace")
    csim_result = parse_csim(csim_text + "\n" + csim_solution_text)
    metrics = parse_top_xml(top_xml)
    step_cycles = parse_step_cycles(impl_text)
    targeted_loops = parse_targeted_loops(csynth_text)

    csim_pass = (
        csim_result == {"commands": 6, "bank_classes": 2, "generation": 2}
        and "Finished Command csim_design" in csim_solution_text
    )
    targeted_ii_pass = all(
        row["target_ii"] == row["final_ii"] == 1 for row in targeted_loops
    )
    csynth_pass = (
        "Finished Command csynth_design" in csynth_text
        and "Loop Constraint Status: All loop constraints were satisfied"
        in csynth_text
        and targeted_ii_pass
        and metrics["estimated_fmax_mhz"] >= 200.0
    )
    latest_design_mtime = max(path.stat().st_mtime for path in DESIGN_SOURCES)
    source_freshness = {
        "csim": "PASS" if latest_design_mtime <= csim_log.stat().st_mtime + 1.0 else "FAIL",
        "csynth": "PASS"
        if latest_design_mtime <= csynth_log.stat().st_mtime + 1.0
        else "FAIL",
    }
    status = (
        "PASS"
        if csim_pass
        and csynth_pass
        and all(value == "PASS" for value in source_freshness.values())
        else "FAIL"
    )

    source_identity = describe_source_files(
        [*DESIGN_SOURCES, Path(__file__).resolve()]
    )
    raw_paths = (csim_log, csim_solution_log, top_xml, top_report, impl_report, csynth_log)
    manifest: dict[str, object] = {
        "schema": 1,
        "status": status,
        "scope": "matched BF16 persistent-state GDN HLS baseline",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "configuration": {
            "num_qk_heads": 16,
            "num_value_heads": 32,
            "key_dim": 128,
            "value_dim": 128,
            "num_layers": 36,
            "num_sequences": 1,
            "p_k": 16,
            "p_v": 8,
            "block_size": 32,
            "state_orientation": "KxV",
            "state_storage": "BF16",
            "multiply_operands": "BF16",
            "accumulation": "FP32",
        },
        "execution": {
            "csim": {
                "command": "vitis_hls -f X:/hls/bf16/tcl/run_csim.tcl",
                "exit_code": 0,
                "status": "PASS" if csim_pass else "FAIL",
            },
            "csynth": {
                "command": "vitis_hls -f X:/hls/bf16/tcl/run_csynth.tcl",
                "exit_code": 0,
                "status": "PASS" if csynth_pass else "FAIL",
            },
        },
        "csim": {
            "status": "PASS" if csim_pass else "FAIL",
            "commands_checked": csim_result["commands"],
            "physical_bank_classes_checked": csim_result["bank_classes"],
            "final_generation": csim_result["generation"],
            "coverage": [
                "RESET",
                "one sparse rank-one STEP",
                "one beta-zero persistence STEP",
                "complete 524288-element state READBACK",
                "URAM-backed layer and BRAM-backed layer LOAD/READBACK",
                "status, generation, and command counters",
            ],
            "required_64_token_rtl_parity": "NOT_RUN",
        },
        "csynth": {
            "status": "PASS" if csynth_pass else "FAIL",
            "metrics": metrics,
            "step_loop_latency_cycles": step_cycles,
            "targeted_loop_ii_status": "PASS" if targeted_ii_pass else "FAIL",
            "targeted_loops": targeted_loops,
            "vendor_loop_constraint_status": (
                "PASS"
                if "Loop Constraint Status: All loop constraints were satisfied"
                in csynth_text
                else "FAIL"
            ),
        },
        "source_freshness": source_freshness,
        "raw_artifact_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in raw_paths
        },
        "rtl_cosimulation_64_token": "NOT_RUN",
        "post_route_timing_and_drc": "SEE_REPORTS_VIVADO_BASELINES_BF16",
        "energy_measurement": "BLOCKED_EXTERNAL",
        "limitations": [
            "C-simulation uses a bounded hand-computable sparse test, not random-vector or 64-token RTL parity",
            "C-synthesis resources, timing, and latency are HLS estimates; the separate BF16 Vivado summary contains placed-and-routed measurements",
            "the HLS memory estimate is not used as proof that the declared all-layer state capacity fits",
            "no board power or energy measurement exists",
        ],
    }

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "bf16_hls_summary.json"
    md_path = output / "bf16_hls_summary.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    resources = metrics["resources"]
    md_path.write_text(
        "\n".join(
            [
                "# Matched BF16 HLS Baseline",
                "",
                f"Generated: `{manifest['timestamp']}`",
                f"Status: `{status}` for source-locked HLS C-sim and C-synthesis extraction",
                "",
                f"- C-simulation: `{'PASS' if csim_pass else 'FAIL'}` ({csim_result['commands']} commands, {csim_result['bank_classes']} physical bank classes, generation {csim_result['generation']})",
                f"- Target: `{metrics['target_device']}`, `{metrics['target_clock_ns']:.3f}` ns",
                f"- Estimated clock: `{metrics['estimated_clock_ns']:.3f}` ns (`{metrics['estimated_fmax_mhz']:.2f}` MHz)",
                f"- Estimated STEP loop: `{step_cycles['minimum']}` to `{step_cycles['maximum']}` cycles",
                f"- Estimated resources: `{resources['LUT']}` LUT, `{resources['FF']}` FF, `{resources['BRAM_18K']}` BRAM18K, `{resources['URAM']}` URAM, `{resources['DSP']}` DSP",
                f"- Explicit II=1 loop constraints: `{'PASS' if targeted_ii_pass else 'FAIL'}` ({len(targeted_loops)} loops)",
                "- 64-token BF16 RTL parity: `NOT_RUN`",
                "- Post-route timing/DRC: see `reports/vivado/baselines/bf16/bf16_vivado_summary.json`",
                "- Measured board energy: `BLOCKED_EXTERNAL`",
                "",
                "The baseline keeps the same recurrent boundary, KxV state layout, 36 layer slots,",
                "P_K=16, P_V=8, block size 32, U55C target, and 4 ns constraint as the",
                "uniform-MXFP4 kernel. BF16 operands are accumulated in FP32 and rounded to",
                "BF16 at the persistent-state and output boundaries.",
                "",
                "These are HLS estimates. The bounded C-simulation and inferred memory counts",
                "do not establish RTL parity, physical fit, routed timing, or energy on their own.",
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
    parser.add_argument("--csim", type=Path, default=DEFAULT_CSIM)
    parser.add_argument("--csynth", type=Path, default=DEFAULT_CSYNTH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = generate_report(
        _resolve(args.csim), _resolve(args.csynth), _resolve(args.output)
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

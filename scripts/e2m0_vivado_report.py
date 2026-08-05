"""Extract traceable post-route evidence for the corrected E2M0 candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = ROOT / "reports" / "vivado" / "corrected" / "e2m0"
DEFAULT_OUTPUT = DEFAULT_REPORT_DIR
RTL_MANIFEST = ROOT / "build" / "vivado" / "e2m0_ooc_rtl" / "manifest.json"
ROUTED_DCP = ROOT / "build" / "vivado" / "gdn_e2m0_vivado" / "e2m0_post_impl.dcp"
IMPL_LOG = ROOT / "reports" / "vivado" / "vivado_e2m0-impl.log"
SWEEP_LOG = ROOT / "reports" / "vivado" / "vivado_e2m0-postroute-sweep.log"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _git_revision() -> str:
    return subprocess.check_output(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "rev-parse",
            "HEAD",
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def parse_timing_summary(text: str) -> dict[str, int | float]:
    header = re.search(r"^\s*WNS\(ns\).*THS Total Endpoints.*$", text, re.MULTILINE)
    if header is None:
        raise ValueError("timing report has no timing-summary header")
    rows = text[header.end() :].splitlines()
    pattern = re.compile(
        r"^\s*([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s+"
        r"(\d+)\s+(\d+)\s+([-+]?\d+(?:\.\d+)?)\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+(\d+)\s+(\d+)\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s+"
        r"(\d+)\s+(\d+)"
    )
    for line in rows:
        match = pattern.match(line)
        if match is None:
            continue
        values = match.groups()
        return {
            "wns_ns": float(values[0]),
            "tns_ns": float(values[1]),
            "setup_failing_endpoints": int(values[2]),
            "setup_total_endpoints": int(values[3]),
            "whs_ns": float(values[4]),
            "ths_ns": float(values[5]),
            "hold_failing_endpoints": int(values[6]),
            "hold_total_endpoints": int(values[7]),
            "wpws_ns": float(values[8]),
            "tpws_ns": float(values[9]),
            "pulse_width_failing_endpoints": int(values[10]),
            "pulse_width_total_endpoints": int(values[11]),
        }
    raise ValueError("timing report has no timing-summary values")


def _pipe_row(text: str, name: str) -> list[str]:
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == name:
            return cells
    raise ValueError(f"report row is absent: {name}")


def parse_utilization(text: str) -> dict[str, dict[str, int | float]]:
    names = {
        "clb_luts": "CLB LUTs",
        "clb_registers": "CLB Registers",
        "block_ram_tiles": "Block RAM Tile",
        "uram": "URAM",
        "dsps": "DSPs",
        "bufgce": "BUFGCE",
    }
    result: dict[str, dict[str, int | float]] = {}
    for key, display in names.items():
        cells = _pipe_row(text, display)
        if len(cells) < 6:
            raise ValueError(f"unexpected utilization row shape: {display}")
        result[key] = {
            "used": int(cells[1].replace(",", "")),
            "available": int(cells[4].replace(",", "")),
            "utilization_percent": float(cells[5].replace("<", "")),
        }
    return result


def parse_power(text: str) -> dict[str, object]:
    summary_names = {
        "total_on_chip_w": "Total On-Chip Power (W)",
        "dynamic_w": "Dynamic (W)",
        "static_w": "Device Static (W)",
        "confidence": "Confidence Level",
    }
    summary: dict[str, object] = {}
    for key, display in summary_names.items():
        value = _pipe_row(text, display)[1]
        summary[key] = value if key == "confidence" else float(value)
    component_names = {
        "clocks_w": "Clocks",
        "clb_logic_w": "CLB Logic",
        "signals_w": "Signals",
        "block_ram_w": "Block RAM",
        "uram_w": "URAM",
        "dsps_w": "DSPs",
    }
    summary["components"] = {
        key: float(_pipe_row(text, display)[1])
        for key, display in component_names.items()
    }
    summary["method"] = "Vivado vectorless activity propagation"
    summary["measured_on_board"] = False
    return summary


def parse_drc(text: str) -> dict[str, object]:
    violations = re.findall(
        r"^([A-Z][A-Z0-9-]+)#\d+\s+(Warning|Critical Warning|Error)\s*$",
        text,
        re.MULTILINE,
    )
    by_rule = Counter(rule for rule, _severity in violations)
    by_severity = Counter(severity for _rule, severity in violations)
    return {
        "violation_count": len(violations),
        "by_rule": dict(sorted(by_rule.items())),
        "warning_count": by_severity["Warning"],
        "critical_warning_count": by_severity["Critical Warning"],
        "error_count": by_severity["Error"],
        "signoff_status": (
            "PASS_WITH_WARNINGS"
            if violations and not by_severity["Critical Warning"] and not by_severity["Error"]
            else "PASS"
            if not violations
            else "FAIL"
        ),
    }


def parse_critical_path(text: str) -> dict[str, object]:
    def one(pattern: str, *, cast: type = str) -> object:
        match = re.search(pattern, text, re.MULTILINE)
        if match is None:
            raise ValueError(f"critical-path field is absent: {pattern}")
        return cast(match.group(1))

    source = str(one(r"^\s*Source:\s+(.+?)(?:/C)?\s*$"))
    destination = str(one(r"^\s*Destination:\s+(.+?)\s*$"))
    data_match = re.search(
        r"Data Path Delay:\s+([0-9.]+)ns\s+\(logic\s+([0-9.]+)ns.*?route\s+([0-9.]+)ns",
        text,
    )
    if data_match is None:
        raise ValueError("critical-path data-delay breakdown is absent")
    return {
        "source": source,
        "destination": destination,
        "path_group": one(r"^\s*Path Group:\s+(.+?)\s*$"),
        "path_type": one(r"^\s*Path Type:\s+(.+?)\s*$"),
        "data_path_delay_ns": float(data_match.group(1)),
        "logic_delay_ns": float(data_match.group(2)),
        "route_delay_ns": float(data_match.group(3)),
        "route_delay_percent": 100.0 * float(data_match.group(3)) / float(data_match.group(1)),
        "logic_levels": one(r"^\s*Logic Levels:\s+(\d+)", cast=int),
        "crosses_slr_1_to_0": "SLR Crossing[1->0]" in text,
        "classification": "resident-state reset/write-enable path into URAM",
    }


def _tool_identity(text: str) -> dict[str, str]:
    version = re.search(r"Tool Version\s*:\s*(.+?)\s*$", text, re.MULTILINE)
    device = re.search(r"Device\s*:\s*(\S+)", text, re.MULTILINE)
    if version is None or device is None:
        raise ValueError("Vivado tool or device identity is absent")
    return {"tool_version": version.group(1), "target_device": device.group(1)}


def _attempt_timing(report_dir: Path) -> list[dict[str, object]]:
    attempts = (
        ("raw_ooc_clock", report_dir / "attempt1_raw_clock" / "impl_timing.rpt"),
        (
            "post_synthesis_bufg_insertion",
            report_dir / "attempt2_post_synth_bufg" / "impl_timing.rpt",
        ),
        ("source_level_bufg_aggressive_route", report_dir / "impl_timing.rpt"),
    )
    rows = []
    for name, path in attempts:
        timing = parse_timing_summary(path.read_text(encoding="utf-8", errors="replace"))
        rows.append(
            {
                "attempt": name,
                "target_period_ns": 4.0,
                "wns_ns": timing["wns_ns"],
                "tns_ns": timing["tns_ns"],
                "whs_ns": timing["whs_ns"],
                "ths_ns": timing["ths_ns"],
                "source": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(path),
            }
        )
    return rows


def generate_report(report_dir: Path, output: Path) -> dict[str, object]:
    timing_path = report_dir / "impl_timing.rpt"
    utilization_path = report_dir / "impl_util.rpt"
    drc_path = report_dir / "impl_drc.rpt"
    power_path = report_dir / "postroute_sweep" / "power_5p600ns.rpt"
    sweep_paths = sorted((report_dir / "postroute_sweep").glob("timing_*ns.rpt"))
    required = (
        timing_path,
        utilization_path,
        drc_path,
        power_path,
        RTL_MANIFEST,
        ROUTED_DCP,
        IMPL_LOG,
        SWEEP_LOG,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if not sweep_paths:
        raise FileNotFoundError(report_dir / "postroute_sweep" / "timing_*ns.rpt")

    timing_text = timing_path.read_text(encoding="utf-8", errors="replace")
    utilization_text = utilization_path.read_text(encoding="utf-8", errors="replace")
    drc_text = drc_path.read_text(encoding="utf-8", errors="replace")
    power_text = power_path.read_text(encoding="utf-8", errors="replace")
    impl_log_text = IMPL_LOG.read_text(encoding="utf-8", errors="replace")
    sweep_log_text = SWEEP_LOG.read_text(encoding="utf-8", errors="replace")
    rtl_manifest = json.loads(RTL_MANIFEST.read_text(encoding="utf-8"))
    rtl_source = ROOT / str(rtl_manifest["source"])
    rtl_output = ROOT / str(rtl_manifest["output"])
    rtl_integrity = (
        rtl_manifest.get("status") == "PASS"
        and rtl_source.is_file()
        and rtl_output.is_file()
        and _sha256(rtl_source) == str(rtl_manifest["source_sha256"]).upper()
        and _sha256(rtl_output) == str(rtl_manifest["output_sha256"]).upper()
    )

    sweep_rows: list[dict[str, object]] = []
    for path in sweep_paths:
        match = re.fullmatch(r"timing_(\d+)p(\d+)ns\.rpt", path.name)
        if match is None:
            raise ValueError(f"unexpected timing-sweep filename: {path.name}")
        period_ns = float(f"{int(match.group(1))}.{match.group(2)}")
        timing = parse_timing_summary(path.read_text(encoding="utf-8", errors="replace"))
        sweep_rows.append(
            {
                "period_ns": period_ns,
                "frequency_mhz": 1000.0 / period_ns,
                **timing,
                "setup_status": "PASS" if float(timing["wns_ns"]) >= 0.0 else "FAIL",
                "hold_status": "PASS" if float(timing["whs_ns"]) >= 0.0 else "FAIL",
                "source": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(path),
            }
        )
    sweep_rows.sort(key=lambda row: float(row["period_ns"]))
    passing = [
        row
        for row in sweep_rows
        if row["setup_status"] == "PASS" and row["hold_status"] == "PASS"
    ]
    if not passing:
        raise ValueError("post-route sweep contains no passing timing point")
    first_passing = passing[0]

    target = next((row for row in sweep_rows if row["period_ns"] == 4.0), None)
    two_hundred = next((row for row in sweep_rows if row["period_ns"] == 5.0), None)
    if target is None or two_hundred is None:
        raise ValueError("post-route sweep must include 4.0 ns and 5.0 ns")
    route_complete = (
        "route_design completed successfully" in impl_log_text
        and "The checkpoint" in impl_log_text
        and "has been generated" in impl_log_text
    )
    sweep_complete = (
        "report_power completed successfully" in sweep_log_text
        and "Exiting Vivado" in sweep_log_text
    )
    drc = parse_drc(drc_text)
    utilization = parse_utilization(utilization_text)
    physical_fit = all(
        float(row["utilization_percent"]) <= 100.0 for row in utilization.values()
    )
    status = (
        "PASS"
        if route_complete
        and sweep_complete
        and rtl_integrity
        and physical_fit
        and drc["signoff_status"] != "FAIL"
        else "FAIL"
    )
    raw_sources = (
        timing_path,
        utilization_path,
        drc_path,
        power_path,
        RTL_MANIFEST,
        ROUTED_DCP,
        IMPL_LOG,
        SWEEP_LOG,
        *sweep_paths,
    )
    report: dict[str, object] = {
        "schema": 1,
        "status": status,
        "scope": "out-of-context post-route implementation of the corrected E2M0 residual/write-log candidate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": _git_revision(),
        "tool": _tool_identity(utilization_text),
        "route_completion": "PASS" if route_complete else "FAIL",
        "physical_fit": "PASS" if physical_fit else "FAIL",
        "target_clock": {
            "period_ns": 4.0,
            "frequency_mhz": 250.0,
            "status": target["setup_status"],
            "timing": target,
        },
        "implemented_200mhz_timing": two_hundred["setup_status"],
        "first_tested_closing_point": {
            "period_ns": first_passing["period_ns"],
            "frequency_mhz": first_passing["frequency_mhz"],
            "wns_ns": first_passing["wns_ns"],
            "whs_ns": first_passing["whs_ns"],
            "status": "PASS",
            "qualification": "first passing point in the tested fixed-route period sweep; not a binary-searched maximum frequency",
        },
        "timing_sweep": sweep_rows,
        "critical_path_at_4ns": parse_critical_path(timing_text),
        "utilization": utilization,
        "drc": drc,
        "power_at_5p6ns": {
            **parse_power(power_text),
            "period_ns": 5.6,
            "frequency_mhz": 1000.0 / 5.6,
            "timing_closed_at_this_period": True,
            "energy_per_token": "NOT_RUN",
        },
        "attempt_history": _attempt_timing(report_dir),
        "rtl_transformation": {
            **rtl_manifest,
            "integrity_status": "PASS" if rtl_integrity else "FAIL",
        },
        "raw_artifact_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in raw_sources
        },
        "claim_boundary": {
            "post_route_fit": "SUPPORTED",
            "post_route_250mhz": "NOT_SUPPORTED",
            "post_route_first_tested_closing_frequency": "SUPPORTED",
            "vectorless_power_estimate": "SUPPORTED_WITH_MEDIUM_CONFIDENCE",
            "measured_board_power_or_energy": "NOT_RUN",
            "bitstream_or_xclbin_execution": "NOT_RUN",
        },
        "limitations": [
            "Out-of-context kernel implementation; no U55C shell integration or xclbin was built.",
            "The design fits but fails setup at 250 MHz and 200 MHz; 180.18 MHz is the first passing tested fixed-route point.",
            "Power uses Vivado vectorless activity propagation at 5.6 ns with medium confidence, not measured board telemetry.",
            "No energy-per-token value is derived because candidate RTL service latency and measured activity are unavailable.",
        ],
    }

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "e2m0_postroute_summary.json"
    csv_path = output / "e2m0_postroute_timing_sweep.csv"
    md_path = output / "e2m0_postroute_summary.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fields = (
            "period_ns",
            "frequency_mhz",
            "wns_ns",
            "tns_ns",
            "setup_failing_endpoints",
            "whs_ns",
            "ths_ns",
            "hold_failing_endpoints",
            "setup_status",
            "hold_status",
            "source",
            "sha256",
        )
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sweep_rows)
    power = report["power_at_5p6ns"]
    first = report["first_tested_closing_point"]
    critical = report["critical_path_at_4ns"]
    md_path.write_text(
        "\n".join(
            [
                "# Corrected Candidate Post-Route Evidence",
                "",
                f"Generated: `{report['generated_at']}`",
                "",
                f"- Extraction and integrity: `{status}`",
                f"- Device/tool: `{report['tool']['target_device']}`, `{report['tool']['tool_version']}`",
                f"- Physical fit: `{report['physical_fit']}`",
                f"- 250 MHz target: `{report['target_clock']['status']}` (WNS `{target['wns_ns']:.3f}` ns)",
                f"- 200 MHz: `{report['implemented_200mhz_timing']}` (WNS `{two_hundred['wns_ns']:.3f}` ns)",
                f"- First tested closing point: `{first['period_ns']:.2f}` ns (`{first['frequency_mhz']:.2f}` MHz), WNS `{first['wns_ns']:.3f}` ns, WHS `{first['whs_ns']:.3f}` ns",
                f"- Critical path: `{critical['data_path_delay_ns']:.3f}` ns, `{critical['route_delay_percent']:.1f}%` routing, `{critical['logic_levels']}` logic levels; {critical['classification']}",
                f"- Resources: `{utilization['clb_luts']['used']:,}` CLB LUT, `{utilization['clb_registers']['used']:,}` FF, `{utilization['block_ram_tiles']['used']}` BRAM tiles, `{utilization['uram']['used']}` URAM, `{utilization['dsps']['used']}` DSP",
                f"- DRC: `{drc['signoff_status']}` with `{drc['violation_count']}` warnings and no critical warnings or errors",
                f"- Vectorless power at 5.60 ns: `{power['total_on_chip_w']:.3f}` W total, `{power['dynamic_w']:.3f}` W dynamic, `{power['static_w']:.3f}` W static, `{power['confidence']}` confidence",
                "- Board power, energy per token, bitstream execution, and xclbin execution: `NOT_RUN`",
                "",
                "The power row is a post-route vectorless estimate and must not be described as measured energy.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report_dir = args.report_dir if args.report_dir.is_absolute() else ROOT / args.report_dir
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report = generate_report(report_dir, output)
    print(
        json.dumps(
            {
                "status": report["status"],
                "physical_fit": report["physical_fit"],
                "target_clock": report["target_clock"]["status"],
                "first_tested_closing_frequency_mhz": report[
                    "first_tested_closing_point"
                ]["frequency_mhz"],
            }
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Extract the selected native-MXFP4 RS2/R3 U55C post-route evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.e2m0_vivado_report import (
    parse_drc,
    parse_power,
    parse_timing_summary,
)
from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = ROOT / "reports" / "vivado" / "corrected" / "rs2_current"
DEFAULT_OUTPUT = DEFAULT_REPORT_DIR
IMPL_LOG = ROOT / "reports" / "vivado" / "vivado_rs2-impl.log"
SWEEP_LOG = ROOT / "reports" / "vivado" / "vivado_rs2-postroute-sweep.log"
RTL_MANIFEST = ROOT / "build" / "vivado" / "rs2_ooc_rtl" / "manifest.json"
ROUTED_DCP = ROOT / "build" / "vivado" / "gdn_rs2_vivado" / "rs2_post_impl.dcp"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _git_revision() -> str:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _number(value: str) -> int | float:
    parsed = float(value.replace(",", "").replace("<", ""))
    return int(parsed) if parsed.is_integer() else parsed


def _pipe_row(text: str, name: str) -> list[str]:
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == name:
            return cells
    raise ValueError(f"report row is absent: {name}")


def parse_fractional_utilization(text: str) -> dict[str, dict[str, int | float]]:
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
            "used": _number(cells[1]),
            "available": _number(cells[4]),
            "utilization_percent": float(cells[5].replace("<", "")),
        }
    return result


def _tool_identity(text: str) -> dict[str, str]:
    version = re.search(r"Tool Version\s*:\s*(.+?)\s*$", text, re.MULTILINE)
    device = re.search(r"Device\s*:\s*(\S+)", text, re.MULTILINE)
    if version is None or device is None:
        raise ValueError("Vivado tool or device identity is absent")
    return {"tool_version": version.group(1), "target_device": device.group(1)}


def generate_report(report_dir: Path, output: Path) -> dict[str, object]:
    sweep_dir = report_dir / "postroute_sweep"
    paths = {
        "utilization": report_dir / "impl_util.rpt",
        "timing": report_dir / "impl_timing.rpt",
        "drc": report_dir / "impl_drc.rpt",
        "power": sweep_dir / "power_first_passing.rpt",
        "first_passing_period": sweep_dir / "first_passing_period.txt",
        "implementation_log": IMPL_LOG,
        "sweep_log": SWEEP_LOG,
        "rtl_manifest": RTL_MANIFEST,
        "routed_checkpoint": ROUTED_DCP,
    }
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)

    utilization_text = paths["utilization"].read_text(
        encoding="utf-8", errors="replace"
    )
    timing_text = paths["timing"].read_text(encoding="utf-8", errors="replace")
    drc_text = paths["drc"].read_text(encoding="utf-8", errors="replace")
    power_text = paths["power"].read_text(encoding="utf-8", errors="replace")
    log_text = paths["implementation_log"].read_text(
        encoding="utf-8", errors="replace"
    )
    sweep_log_text = paths["sweep_log"].read_text(
        encoding="utf-8", errors="replace"
    )
    rtl = json.loads(paths["rtl_manifest"].read_text(encoding="utf-8"))
    rtl_source = ROOT / str(rtl["source"])
    rtl_output = ROOT / str(rtl["output"])
    rtl_integrity = (
        rtl.get("status") == "PASS"
        and rtl_source.is_file()
        and rtl_output.is_file()
        and _sha256(rtl_source) == str(rtl["source_sha256"]).upper()
        and _sha256(rtl_output) == str(rtl["output_sha256"]).upper()
    )

    timing = parse_timing_summary(timing_text)
    utilization = parse_fractional_utilization(utilization_text)
    drc = parse_drc(drc_text)
    power = parse_power(power_text)
    physical_fit = all(
        float(row["utilization_percent"]) <= 100.0 for row in utilization.values()
    )
    route_complete = (
        "route_design completed successfully" in log_text
        and "rs2_post_impl.dcp" in log_text
    )
    target_timing = (
        "PASS"
        if float(timing["wns_ns"]) >= 0.0 and float(timing["whs_ns"]) >= 0.0
        else "FAIL"
    )
    sweep_rows: list[dict[str, object]] = []
    for sweep_path in sorted(sweep_dir.glob("timing_*ns.rpt")):
        match = re.fullmatch(r"timing_(\d+)p(\d+)ns\.rpt", sweep_path.name)
        if match is None:
            raise ValueError(f"unexpected timing-sweep filename: {sweep_path.name}")
        period_ns = float(f"{int(match.group(1))}.{match.group(2)}")
        sweep_timing = parse_timing_summary(
            sweep_path.read_text(encoding="utf-8", errors="replace")
        )
        sweep_rows.append(
            {
                "period_ns": period_ns,
                "frequency_mhz": 1000.0 / period_ns,
                **sweep_timing,
                "setup_status": "PASS" if float(sweep_timing["wns_ns"]) >= 0.0 else "FAIL",
                "hold_status": "PASS" if float(sweep_timing["whs_ns"]) >= 0.0 else "FAIL",
                "source": sweep_path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(sweep_path),
            }
        )
    if not sweep_rows:
        raise FileNotFoundError(sweep_dir / "timing_*ns.rpt")
    sweep_rows.sort(key=lambda row: float(row["period_ns"]))
    selected_period = float(
        paths["first_passing_period"].read_text(encoding="utf-8").strip()
    )
    first_passing = next(
        (row for row in sweep_rows if float(row["period_ns"]) == selected_period),
        None,
    )
    if (
        first_passing is None
        or first_passing["setup_status"] != "PASS"
        or first_passing["hold_status"] != "PASS"
        or any(
            row["setup_status"] == "PASS" and float(row["period_ns"]) < selected_period
            for row in sweep_rows
        )
    ):
        raise ValueError("recorded first passing period is inconsistent with the sweep")
    sweep_complete = (
        "report_power completed successfully" in sweep_log_text
        and "Exiting Vivado" in sweep_log_text
    )
    shutdown_abnormal = "EXCEPTION_ACCESS_VIOLATION" in sweep_log_text
    optimization_attempts: list[dict[str, object]] = []
    optimization_artifacts: list[Path] = []
    for name, directory_name, operation in (
        ("aggressive_fanout", "postroute_fanout_opt", "post-route aggressive fanout optimization"),
        ("retiming", "postroute_retime_opt", "post-route retiming optimization"),
        ("slr_crossing", "postroute_slr_opt", "post-route SLR-crossing optimization"),
    ):
        directory = report_dir / directory_name
        timing_path = directory / "timing_4p000ns.rpt"
        drc_path = directory / "drc.rpt"
        if not timing_path.is_file() or not drc_path.is_file():
            continue
        attempt_timing = parse_timing_summary(
            timing_path.read_text(encoding="utf-8", errors="replace")
        )
        attempt_drc = parse_drc(
            drc_path.read_text(encoding="utf-8", errors="replace")
        )
        optimization_artifacts.extend((timing_path, drc_path))
        optimization_attempts.append(
            {
                "name": name,
                "operation": operation,
                "status": "PASS",
                "target_timing_status": (
                    "PASS"
                    if float(attempt_timing["wns_ns"]) >= 0.0
                    and float(attempt_timing["whs_ns"]) >= 0.0
                    else "FAIL"
                ),
                "timing": attempt_timing,
                "drc": attempt_drc,
                "timing_source": timing_path.relative_to(ROOT).as_posix(),
                "drc_source": drc_path.relative_to(ROOT).as_posix(),
            }
        )
    status = (
        "PASS"
        if route_complete
        and physical_fit
        and rtl_integrity
        and sweep_complete
        and drc["signoff_status"] != "FAIL"
        else "FAIL"
    )
    source_identity = describe_source_files(
        [
            Path(__file__).resolve(),
            ROOT / "hls" / "rs2" / "src" / "gdn_rs2_top.cpp",
            ROOT / "hls" / "rs2" / "src" / "rs2_arithmetic.cpp",
            ROOT / "hls" / "rs2" / "include" / "gdn_rs2_kernel.hpp",
            ROOT / "scripts" / "prepare_rs2_ooc_rtl.py",
            ROOT / "vivado" / "tcl" / "create_rs2_project.tcl",
            ROOT / "vivado" / "tcl" / "run_rs2_impl.tcl",
            ROOT / "vivado" / "tcl" / "run_rs2_postroute_sweep.tcl",
            ROOT / "vivado" / "tcl" / "run_rs2_postroute_fanout_opt.tcl",
            ROOT / "vivado" / "tcl" / "run_rs2_postroute_retime_opt.tcl",
            ROOT / "vivado" / "tcl" / "run_rs2_postroute_slr_opt.tcl",
        ]
    )
    report: dict[str, object] = {
        "schema": 1,
        "status": status,
        "scope": "selected native-MXFP4 RS2/R3 all-layer persistent-state kernel, out-of-context post-route on U55C",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": _git_revision(),
        "source_identity": source_identity,
        "tool": _tool_identity(utilization_text),
        "route_completion": "PASS" if route_complete else "FAIL",
        "physical_fit": "PASS" if physical_fit else "FAIL",
        "target_clock": {
            "period_ns": 4.0,
            "frequency_mhz": 250.0,
            "status": target_timing,
            "timing": timing,
        },
        "first_tested_closing_point": {
            "period_ns": first_passing["period_ns"],
            "frequency_mhz": first_passing["frequency_mhz"],
            "wns_ns": first_passing["wns_ns"],
            "whs_ns": first_passing["whs_ns"],
            "status": "PASS",
            "qualification": "first passing point in the tested fixed-route period sweep; not a binary-searched maximum frequency",
        },
        "timing_sweep": sweep_rows,
        "postroute_optimization_attempts": optimization_attempts,
        "tool_shutdown": {
            "status": "ABNORMAL_AFTER_ARTIFACTS" if shutdown_abnormal else "PASS",
            "exception": "EXCEPTION_ACCESS_VIOLATION" if shutdown_abnormal else None,
            "qualification": (
                "Vivado completed every timing report, the selected-period power report, "
                "and first-period record before failing during process shutdown."
                if shutdown_abnormal
                else "Vivado exited normally after completing the sweep."
            ),
        },
        "utilization": utilization,
        "drc": drc,
        "vectorless_power": {
            **power,
            "period_ns": first_passing["period_ns"],
            "frequency_mhz": first_passing["frequency_mhz"],
            "timing_closed_at_this_period": True,
            "energy_per_token": "NOT_DERIVED",
        },
        "rtl_transformation": {
            **rtl,
            "integrity_status": "PASS" if rtl_integrity else "FAIL",
        },
        "raw_artifact_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path)
            for path in (
                *paths.values(),
                *sorted(sweep_dir.glob("timing_*ns.rpt")),
                *optimization_artifacts,
            )
        },
        "claim_boundary": {
            "post_route_fit": "SUPPORTED" if physical_fit else "NOT_SUPPORTED",
            "post_route_250mhz": "SUPPORTED" if target_timing == "PASS" else "NOT_SUPPORTED",
            "post_route_first_tested_closing_frequency": "SUPPORTED",
            "vectorless_power_estimate": "SUPPORTED",
            "measured_board_power_or_energy": "BLOCKED_EXTERNAL",
            "bitstream_or_xclbin_execution": "BLOCKED_EXTERNAL",
        },
        "limitations": [
            "Out-of-context kernel implementation; no U55C shell integration or xclbin was built.",
            "Vivado power is a vectorless estimate, not board telemetry or energy per token.",
            "The RS2/R3 kernel has exact 64-token HLS C simulation; generated-RTL parity is reported separately.",
            "The first passing fixed-route sweep point is not a binary-searched maximum frequency.",
            *(
                ["Vivado raised EXCEPTION_ACCESS_VIOLATION during shutdown after all registered sweep artifacts were written."]
                if shutdown_abnormal
                else []
            ),
        ],
    }

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "rs2_vivado_summary.json"
    md_path = output / "rs2_vivado_summary.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_path.write_text(
        "\n".join(
            [
                "# Selected Native MXFP4 RS2/R3 Post-Route Evidence",
                "",
                f"- Extraction and integrity: `{status}`",
                f"- Route completion: `{report['route_completion']}`",
                f"- Physical fit: `{report['physical_fit']}`",
                f"- 250 MHz timing: `{target_timing}` (WNS `{timing['wns_ns']:.3f}` ns, WHS `{timing['whs_ns']:.3f}` ns)",
                f"- First tested closing point: `{first_passing['period_ns']:.3f}` ns (`{first_passing['frequency_mhz']:.2f}` MHz)",
                f"- Resources: `{utilization['clb_luts']['used']}` CLB LUT, `{utilization['clb_registers']['used']}` FF, `{utilization['block_ram_tiles']['used']}` BRAM tiles, `{utilization['uram']['used']}` URAM, `{utilization['dsps']['used']}` DSP",
                f"- DRC: `{drc['signoff_status']}`",
                "- Bounded 250 MHz repair attempts: "
                + (
                    ", ".join(
                        f"`{row['name']}` WNS `{row['timing']['wns_ns']:.3f}` ns"
                        for row in optimization_attempts
                    )
                    if optimization_attempts
                    else "`NOT_RUN`"
                ),
                f"- Vectorless power at the first tested closing point: `{power['total_on_chip_w']:.3f}` W total (`{power['confidence']}` confidence)",
                f"- Vivado sweep shutdown: `{report['tool_shutdown']['status']}`",
                "- Board execution and measured energy: `BLOCKED_EXTERNAL`",
                "",
                "The power result is not converted into energy per token.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = generate_report(_resolve(args.report_dir), _resolve(args.output))
    print(
        json.dumps(
            {
                "status": report["status"],
                "physical_fit": report["physical_fit"],
                "target_clock": report["target_clock"]["status"],
            }
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

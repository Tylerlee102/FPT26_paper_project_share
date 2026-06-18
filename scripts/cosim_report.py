from __future__ import annotations

import csv
import os
import shutil
from pathlib import Path

from reports.report_parsers import CosimSummary, parse_hls_cosim, parse_hls_latency_rb


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPORT = ROOT / "gdn_mxfp4_hls" / "u55c_250mhz" / "sim" / "report" / "gdn_top_cosim.rpt"
SIM_VERILOG_DIR = ROOT / "gdn_mxfp4_hls" / "u55c_250mhz" / "sim" / "verilog"
SIM_TV_DIR = ROOT / "gdn_mxfp4_hls" / "u55c_250mhz" / "sim" / "tv"
OUT_DIR = ROOT / "reports" / "cosim"


def _compare_c_rtl_outputs() -> list[str]:
    mismatches: list[str] = []
    for name in ("gmem5", "gmem6"):
        c_path = SIM_TV_DIR / "cdatafile" / f"c.gdn_top.autotvout_{name}.dat"
        rtl_path = SIM_TV_DIR / "rtldatafile" / f"rtl.gdn_top.autotvout_{name}.dat"
        if not c_path.exists() or not rtl_path.exists():
            mismatches.append(f"missing {name} output file")
            continue
        c_data = c_path.read_bytes()
        rtl_data = rtl_path.read_bytes()
        if len(c_data) != len(rtl_data) + 8:
            mismatches.append(f"{name} length mismatch: c={len(c_data)} rtl={len(rtl_data)}")
            continue
        if c_data[: len(rtl_data)] != rtl_data:
            mismatches.append(f"{name} content mismatch")
        if c_data[-8:] != bytes.fromhex("5A5AA5A50F0FF0F0"):
            mismatches.append(f"{name} missing HLS C-output sentinel trailer")
    return mismatches


def _recover_from_xsim(token_count: int) -> tuple[CosimSummary, str]:
    latency_path = SIM_VERILOG_DIR / "gdn_top.result.lat.rb"
    xsim_log = SIM_VERILOG_DIR / "xsim.log"
    if not latency_path.exists() or not xsim_log.exists():
        raise FileNotFoundError("Missing xsim latency/log files for cosim recovery")

    log_text = xsim_log.read_text(encoding="utf-8", errors="replace")
    completion = f"RTL Simulation : {token_count} / {token_count} [100.00%]"
    if completion not in log_text:
        raise RuntimeError(f"xsim did not complete {token_count}/{token_count} RTL transactions")

    mismatches = _compare_c_rtl_outputs()
    if mismatches:
        raise RuntimeError("; ".join(mismatches))

    summary = parse_hls_latency_rb(latency_path.read_text(encoding="utf-8", errors="replace"))
    report_text = "\n".join(
        [
            "Recovered HLS C/RTL cosimulation report",
            "",
            "Vitis HLS did not emit the wrapper report because xsim stayed alive after 100% RTL completion.",
            "Recovery criteria:",
            f"- xsim reached {token_count}/{token_count} RTL transactions.",
            "- RTL output buffers match C output buffers byte-for-byte, excluding the HLS C sentinel trailer.",
            "",
            "| RTL | Status | Latency-min | Latency-avg | Latency-max | Interval-min | Interval-avg | Interval-max | Total Execution |",
            "| Verilog | Pass | "
            f"{summary.latency_min_cycles} | {summary.latency_avg_cycles} | {summary.latency_max_cycles} | "
            f"{summary.interval_min_cycles} | {summary.interval_avg_cycles} | {summary.interval_max_cycles} | "
            f"{summary.total_execution_cycles} |",
            "",
        ]
    )
    return summary, report_text


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    token_count = int(os.environ.get("GDN_COSIM_VECTORS", "64"))
    if SOURCE_REPORT.exists():
        report_text = SOURCE_REPORT.read_text(encoding="utf-8", errors="replace")
        summary = parse_hls_cosim(report_text)
        source_label = SOURCE_REPORT.relative_to(ROOT).as_posix()
        recovered = False
    else:
        summary, report_text = _recover_from_xsim(token_count)
        source_label = (SIM_VERILOG_DIR / "gdn_top.result.lat.rb").relative_to(ROOT).as_posix()
        recovered = True

    copied_report = OUT_DIR / "gdn_top_cosim.rpt"
    if SOURCE_REPORT.exists():
        shutil.copyfile(SOURCE_REPORT, copied_report)
    else:
        copied_report.write_text(report_text, encoding="utf-8")

    latency_csv = OUT_DIR / "latency.csv"
    with latency_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rtl",
                "status",
                "latency_min_cycles",
                "latency_avg_cycles",
                "latency_max_cycles",
                "interval_min_cycles",
                "interval_avg_cycles",
                "interval_max_cycles",
                "total_execution_cycles",
                "tokens",
            ]
        )
        writer.writerow(
            [
                "verilog",
                summary.status,
                summary.latency_min_cycles,
                summary.latency_avg_cycles,
                summary.latency_max_cycles,
                summary.interval_min_cycles,
                summary.interval_avg_cycles,
                summary.interval_max_cycles,
                summary.total_execution_cycles,
                token_count,
            ]
        )

    summary_md = OUT_DIR / "summary.md"
    summary_md.write_text(
        "\n".join(
            [
                "# HLS C/RTL Cosimulation Summary",
                "",
                f"- Source report: `{source_label}`",
                "- RTL: Verilog/xsim",
                f"- Tokens: {token_count}",
                f"- Status: {summary.status}",
                f"- Latency: min {summary.latency_min_cycles}, avg {summary.latency_avg_cycles}, max {summary.latency_max_cycles} cycles",
                f"- Interval: min {summary.interval_min_cycles}, avg {summary.interval_avg_cycles}, max {summary.interval_max_cycles} cycles",
                f"- Total execution: {summary.total_execution_cycles} cycles",
                f"- Recovery: xsim reached {token_count}/{token_count} and C/RTL output buffers matched; Vitis wrapper report was not emitted."
                if recovered
                else "- Recovery: not used; parsed official Vitis HLS cosim report.",
                "",
                "Note: this summary reflects the most recent `GDN_COSIM_VECTORS` run. "
                "The checked-in default is 64 vectors.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {latency_csv.relative_to(ROOT)} and {summary_md.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

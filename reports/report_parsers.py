"""Small report parsers used by tests and later benchmark extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TimingSummary:
    wns_ns: float


@dataclass(frozen=True)
class UtilizationSummary:
    lut_pct: float
    bram_pct: float
    dsp_pct: float


@dataclass(frozen=True)
class PowerSummary:
    total_w: float


@dataclass(frozen=True)
class CosimSummary:
    status: str
    latency_min_cycles: int
    latency_avg_cycles: int
    latency_max_cycles: int
    interval_min_cycles: int
    interval_avg_cycles: int
    interval_max_cycles: int
    total_execution_cycles: int


def parse_wns(report_text: str) -> TimingSummary:
    match = re.search(r"\bWNS(?:\s*\(ns\))?\s*[:|]\s*(-?\d+(?:\.\d+)?)", report_text, re.IGNORECASE)
    if match:
        return TimingSummary(wns_ns=float(match.group(1)))

    match = re.search(r"\bSetup\s*:[^\n\r]*?Worst Slack\s*(-?\d+(?:\.\d+)?)\s*ns", report_text, re.IGNORECASE)
    if match:
        return TimingSummary(wns_ns=float(match.group(1)))

    raise ValueError("Could not find WNS in timing report")


def parse_utilization(report_text: str) -> UtilizationSummary:
    def pct_from_pipe_rows(*names: str) -> float | None:
        for line in report_text.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not cells:
                continue
            if cells[0] in names and cells[-1]:
                try:
                    return float(cells[-1])
                except ValueError:
                    continue
        return None

    def pct(name: str, *vivado_names: str) -> float:
        pipe_value = pct_from_pipe_rows(*vivado_names)
        if pipe_value is not None:
            return pipe_value

        pattern = rf"\b{name}\b[^\n\r]*?(\d+(?:\.\d+)?)\s*%"
        match = re.search(pattern, report_text, re.IGNORECASE)
        if not match:
            raise ValueError(f"Could not find {name} utilization percentage")
        return float(match.group(1))

    return UtilizationSummary(
        lut_pct=pct("LUT", "CLB LUTs", "LUT"),
        bram_pct=pct("BRAM", "Block RAM Tile", "BRAM"),
        dsp_pct=pct("DSP", "DSPs", "DSP"),
    )


def parse_total_power(report_text: str) -> PowerSummary:
    for line in report_text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == "Total On-Chip Power (W)" and len(cells) > 1:
            return PowerSummary(total_w=float(cells[1]))

    match = re.search(
        r"\b(?:Total\s+On-Chip\s+Power|Total\s+Power)\b[^\n\r]*?(\d+(?:\.\d+)?)\s*W",
        report_text,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError("Could not find total power in power report")
    return PowerSummary(total_w=float(match.group(1)))


def parse_hls_cosim(report_text: str) -> CosimSummary:
    def int_or_fallback(value: str, fallback: int) -> int:
        return fallback if value.upper() == "NA" else int(value)

    for line in report_text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == "Verilog":
            if len(cells) != 9:
                raise ValueError("Unexpected Verilog cosim row shape")
            latency_min = int(cells[2])
            latency_avg = int(cells[3])
            latency_max = int(cells[4])
            return CosimSummary(
                status=cells[1],
                latency_min_cycles=latency_min,
                latency_avg_cycles=latency_avg,
                latency_max_cycles=latency_max,
                interval_min_cycles=int_or_fallback(cells[5], latency_min),
                interval_avg_cycles=int_or_fallback(cells[6], latency_avg),
                interval_max_cycles=int_or_fallback(cells[7], latency_max),
                total_execution_cycles=int(cells[8]),
            )
    raise ValueError("Could not find Verilog row in HLS cosim report")


def parse_hls_latency_rb(report_text: str) -> CosimSummary:
    values: dict[str, int] = {}
    for key, value in re.findall(r'\$(\w+)\s*=\s*"(\d+)"', report_text):
        values[key] = int(value)

    required = {
        "MAX_LATENCY",
        "MIN_LATENCY",
        "AVER_LATENCY",
        "MAX_THROUGHPUT",
        "MIN_THROUGHPUT",
        "AVER_THROUGHPUT",
        "TOTAL_EXECUTE_TIME",
    }
    missing = sorted(required - set(values))
    if missing:
        raise ValueError(f"Missing latency fields: {', '.join(missing)}")

    return CosimSummary(
        status="Pass",
        latency_min_cycles=values["MIN_LATENCY"],
        latency_avg_cycles=values["AVER_LATENCY"],
        latency_max_cycles=values["MAX_LATENCY"],
        interval_min_cycles=values["MIN_THROUGHPUT"],
        interval_avg_cycles=values["AVER_THROUGHPUT"],
        interval_max_cycles=values["MAX_THROUGHPUT"],
        total_execution_cycles=values["TOTAL_EXECUTE_TIME"],
    )

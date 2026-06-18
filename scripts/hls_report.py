from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "gdn_mxfp4_hls" / "u55c_250mhz" / "syn" / "report"
OUT_DIR = ROOT / "reports" / "csynth"
U55C_CAPACITY = {
    "BRAM_18K": 2016,
    "DSP": 9024,
    "LUT": 1303680,
}


def _first_ints(line: str) -> list[int]:
    return [int(value) for value in re.findall(r"\b\d+\b", line)]


def _parse_inner_loop_ii(report_dir: Path) -> int | None:
    ii_values: list[int] = []
    for xml_report in report_dir.glob("*Pipeline*_csynth.xml"):
        text = xml_report.read_text(encoding="utf-8", errors="replace")
        ii_values.extend(int(value) for value in re.findall(r"<PipelineII>\s*(\d+)\s*</PipelineII>", text))
    if ii_values:
        return max(ii_values)

    csynth_report = report_dir / "csynth.rpt"
    if csynth_report.exists():
        text = csynth_report.read_text(encoding="utf-8", errors="replace")
        if "II=1" in text:
            return 1
    return None


def main() -> int:
    if not SOURCE_DIR.exists():
        print(f"Missing HLS synthesis report directory: {SOURCE_DIR}")
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.rpt", "*.xml"):
        for report in SOURCE_DIR.glob(pattern):
            shutil.copyfile(report, OUT_DIR / report.name)

    top_report = OUT_DIR / "gdn_top_csynth.rpt"
    if not top_report.exists():
        print(f"Missing top HLS report: {top_report}")
        return 2

    text = top_report.read_text(encoding="utf-8", errors="replace")
    estimated_ns = None
    for line in text.splitlines():
        if "ap_clk" in line and "ns" in line:
            values = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*ns", line)]
            if len(values) >= 2:
                estimated_ns = values[1]
                break
    if estimated_ns is None:
        raise ValueError("Could not parse estimated HLS clock")

    latency_cycles = None
    for line in text.splitlines():
        if (" ms|" in line or " us|" in line) and "|" in line:
            values = _first_ints(line)
            if len(values) >= 2:
                latency_cycles = values[0]
                break
    if latency_cycles is None:
        raise ValueError("Could not parse HLS latency")

    totals = None
    percents = None
    for line in text.splitlines():
        if totals is None and line.strip().startswith("|Total"):
            totals = _first_ints(line)
        if percents is None and line.strip().startswith("|Utilization (%)"):
            percents = _first_ints(line)
    if totals is None or len(totals) < 5:
        raise ValueError("Could not parse HLS utilization totals")

    fmax_mhz = 1000.0 / estimated_ns
    bram_pct = 100.0 * totals[0] / U55C_CAPACITY["BRAM_18K"]
    dsp_pct = 100.0 * totals[1] / U55C_CAPACITY["DSP"]
    lut_pct = 100.0 * totals[3] / U55C_CAPACITY["LUT"]
    inner_loop_ii = _parse_inner_loop_ii(OUT_DIR)
    util_md = OUT_DIR / "util.md"
    util_md.write_text(
        "\n".join(
            [
                "# HLS C-Synthesis Utilization",
                "",
                f"- Source report: `{top_report.relative_to(ROOT).as_posix()}`",
                f"- Estimated Fmax: {fmax_mhz:.2f} MHz",
                f"- Estimated clock: {estimated_ns:.3f} ns ({fmax_mhz:.2f} MHz)",
                f"- Latency: {latency_cycles} cycles",
                f"- Inner-loop II: {inner_loop_ii if inner_loop_ii is not None else 'unknown'}",
                f"- BRAM_18K: {totals[0]}",
                f"- DSP: {totals[1]}",
                f"- FF: {totals[2]}",
                f"- LUT: {totals[3]}",
                f"- URAM: {totals[4]}",
                f"- BRAM utilization: {bram_pct:.2f}%",
                f"- DSP utilization: {dsp_pct:.2f}%",
                f"- LUT utilization: {lut_pct:.2f}%",
                f"- Utilization percentage row: {percents if percents is not None else 'not reported numerically'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Copied HLS reports and wrote {util_md.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

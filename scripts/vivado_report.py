from __future__ import annotations

from pathlib import Path

from reports.report_parsers import parse_total_power, parse_utilization, parse_wns


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "vivado"


def _read(name: str) -> str:
    path = REPORT_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    synth_timing = parse_wns(_read("synth_timing.rpt"))
    impl_timing = parse_wns(_read("impl_timing.rpt"))
    impl_util = parse_utilization(_read("impl_util.rpt"))
    impl_power = parse_total_power(_read("impl_power.rpt"))

    summary = REPORT_DIR / "summary.md"
    summary.write_text(
        "\n".join(
            [
                "# Vivado Phase 5 Summary",
                "",
                f"- Synthesis WNS: {synth_timing.wns_ns:.3f} ns",
                f"- Implementation WNS: {impl_timing.wns_ns:.3f} ns",
                f"- LUT utilization: {impl_util.lut_pct:.2f}%",
                f"- BRAM utilization: {impl_util.bram_pct:.2f}%",
                f"- DSP utilization: {impl_util.dsp_pct:.2f}%",
                f"- Total on-chip power: {impl_power.total_w:.3f} W",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {summary.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

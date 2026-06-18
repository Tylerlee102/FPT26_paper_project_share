from __future__ import annotations

import unittest
import csv
from pathlib import Path

from reports.report_parsers import parse_hls_cosim, parse_hls_latency_rb, parse_total_power, parse_utilization, parse_wns


ROOT = Path(__file__).resolve().parents[1]


def _latest_hls_source_mtime() -> float:
    sources: list[Path] = []
    for pattern in ("hls/include/*.hpp", "hls/src/*.cpp", "hls/tb/*.cpp"):
        sources.extend(ROOT.glob(pattern))
    return max(path.stat().st_mtime for path in sources)


class TestReports(unittest.TestCase):
    def test_parse_timing_wns(self) -> None:
        summary = parse_wns("| WNS(ns) | 0.123 |")

        self.assertEqual(summary.wns_ns, 0.123)

    def test_parse_vivado_timing_worst_slack(self) -> None:
        summary = parse_wns("Setup : 0 Failing Endpoints, Worst Slack        0.956ns")

        self.assertEqual(summary.wns_ns, 0.956)

    def test_parse_utilization_percentages(self) -> None:
        text = """
        LUT     12345   100000  12.35%
        BRAM    200      2016   9.92%
        DSP       0      9024   0.00%
        """

        summary = parse_utilization(text)

        self.assertEqual(summary.lut_pct, 12.35)
        self.assertEqual(summary.bram_pct, 9.92)
        self.assertEqual(summary.dsp_pct, 0.0)

    def test_parse_vivado_pipe_utilization(self) -> None:
        text = """
        | CLB LUTs                   | 6549 |     0 |          0 |   1303680 |  0.50 |
        | Block RAM Tile             |    8 |     0 |          0 |      2016 |  0.40 |
        | DSPs                       |    7 |     0 |          0 |      9024 |  0.08 |
        """

        summary = parse_utilization(text)

        self.assertEqual(summary.lut_pct, 0.50)
        self.assertEqual(summary.bram_pct, 0.40)
        self.assertEqual(summary.dsp_pct, 0.08)

    def test_parse_total_power(self) -> None:
        summary = parse_total_power("Total On-Chip Power (W): 7.84 W")

        self.assertEqual(summary.total_w, 7.84)

    def test_parse_vivado_pipe_power(self) -> None:
        summary = parse_total_power("| Total On-Chip Power (W)  | 3.501        |")

        self.assertEqual(summary.total_w, 3.501)

    def test_parse_hls_cosim_report(self) -> None:
        text = """
        |   Verilog|      Pass|        1765625|        1765660|        1765696|        1765696|        1765696|        1765696|               3531321|
        """

        summary = parse_hls_cosim(text)

        self.assertEqual(summary.status, "Pass")
        self.assertEqual(summary.latency_avg_cycles, 1765660)
        self.assertEqual(summary.total_execution_cycles, 3531321)

    def test_parse_one_transaction_hls_cosim_report(self) -> None:
        text = """
        |   Verilog|      Pass|        10|        12|        14|        NA|        NA|        NA|               99|
        """

        summary = parse_hls_cosim(text)

        self.assertEqual(summary.interval_min_cycles, 10)
        self.assertEqual(summary.interval_avg_cycles, 12)
        self.assertEqual(summary.interval_max_cycles, 14)

    def test_parse_hls_latency_rb(self) -> None:
        text = """
        $MAX_LATENCY = "1765696"
        $MIN_LATENCY = "1765625"
        $AVER_LATENCY = "1765626"
        $MAX_THROUGHPUT = "1765696"
        $MIN_THROUGHPUT = "1765625"
        $AVER_THROUGHPUT = "1765626"
        $TOTAL_EXECUTE_TIME = "113000071"
        """

        summary = parse_hls_latency_rb(text)

        self.assertEqual(summary.status, "Pass")
        self.assertEqual(summary.latency_avg_cycles, 1765626)
        self.assertEqual(summary.total_execution_cycles, 113000071)

    def test_current_hls_cosim_report_passes_when_present(self) -> None:
        report = ROOT / "reports" / "cosim" / "gdn_top_cosim.rpt"
        if not report.exists():
            self.skipTest("HLS cosim report has not been generated")
        if report.stat().st_mtime + 1.0 < _latest_hls_source_mtime():
            self.skipTest("HLS cosim report predates current HLS sources")

        summary = parse_hls_cosim(report.read_text(encoding="utf-8", errors="replace"))

        self.assertEqual(summary.status, "Pass")
        self.assertGreater(summary.latency_avg_cycles, 0)

        latency_csv = ROOT / "reports" / "cosim" / "latency.csv"
        if latency_csv.exists():
            with latency_csv.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertGreaterEqual(int(row["tokens"]), 64)

    def test_current_vivado_reports_meet_phase5_thresholds_when_present(self) -> None:
        report_dir = ROOT / "reports" / "vivado"
        required = [
            "synth_timing.rpt",
            "impl_timing.rpt",
            "impl_util.rpt",
            "impl_power.rpt",
        ]
        missing = [name for name in required if not (report_dir / name).exists()]
        if missing:
            self.skipTest(f"Vivado reports have not been generated: {', '.join(missing)}")

        synth_timing = parse_wns((report_dir / "synth_timing.rpt").read_text(encoding="utf-8", errors="replace"))
        impl_timing = parse_wns((report_dir / "impl_timing.rpt").read_text(encoding="utf-8", errors="replace"))
        impl_util = parse_utilization((report_dir / "impl_util.rpt").read_text(encoding="utf-8", errors="replace"))
        impl_power = parse_total_power((report_dir / "impl_power.rpt").read_text(encoding="utf-8", errors="replace"))

        self.assertGreaterEqual(synth_timing.wns_ns, 0.0)
        self.assertGreaterEqual(impl_timing.wns_ns, 0.0)
        self.assertLess(impl_util.lut_pct, 80.0)
        self.assertLess(impl_util.dsp_pct, 80.0)
        self.assertLess(impl_util.bram_pct, 80.0)
        self.assertLess(impl_power.total_w, 25.0)


if __name__ == "__main__":
    unittest.main()

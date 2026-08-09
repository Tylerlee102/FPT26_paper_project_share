from pathlib import Path

import pytest

from scripts.rs2_vivado_report import (
    DEFAULT_REPORT_DIR,
    generate_report,
    parse_fractional_utilization,
)


def test_rs2_fractional_utilization_parser() -> None:
    parsed = parse_fractional_utilization(
        "\n".join(
            [
                "| CLB LUTs | 100 | 0 | 0 | 1303680 | <0.01 |",
                "| CLB Registers | 200 | 0 | 0 | 2607360 | <0.01 |",
                "| Block RAM Tile | 164.5 | 0 | 0 | 2016 | 8.16 |",
                "| URAM | 576 | 0 | 0 | 960 | 60.00 |",
                "| DSPs | 2 | 0 | 0 | 9024 | 0.02 |",
                "| BUFGCE | 1 | 0 | 0 | 288 | 0.35 |",
            ]
        )
    )
    assert parsed["block_ram_tiles"]["used"] == 164.5
    assert parsed["uram"]["used"] == 576


def test_real_rs2_route_when_available(tmp_path: Path) -> None:
    if not (DEFAULT_REPORT_DIR / "impl_util.rpt").is_file():
        pytest.skip("RS2 implementation is still running")
    report = generate_report(DEFAULT_REPORT_DIR, tmp_path)
    assert report["status"] == "PASS"
    assert report["route_completion"] == "PASS"
    assert report["physical_fit"] == "PASS"
    assert report["utilization"]["uram"]["used"] > 0
    assert report["vectorless_power"]["measured_on_board"] is False
    attempts = {
        row["name"]: row for row in report["postroute_optimization_attempts"]
    }
    assert set(attempts) == {"aggressive_fanout", "retiming", "slr_crossing"}
    assert all(row["status"] == "PASS" for row in attempts.values())
    assert all(row["target_timing_status"] == "FAIL" for row in attempts.values())
    assert (tmp_path / "rs2_vivado_summary.json").is_file()

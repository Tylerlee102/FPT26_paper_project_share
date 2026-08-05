from pathlib import Path

import pytest

from scripts.mxfp8_vivado_report import (
    DEFAULT_REPORT_DIR,
    generate_report,
    parse_fractional_utilization,
)


def test_fractional_bram_utilization_parser() -> None:
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


def test_real_mxfp8_route_when_available(tmp_path: Path) -> None:
    if not (DEFAULT_REPORT_DIR / "impl_util.rpt").is_file():
        pytest.skip("MXFP8 implementation is still running")
    report = generate_report(DEFAULT_REPORT_DIR, tmp_path)
    assert report["status"] == "PASS"
    assert report["route_completion"] == "PASS"
    assert report["physical_fit"] == "PASS"
    assert report["utilization"]["uram"]["used"] >= 512
    assert report["vectorless_power"]["measured_on_board"] is False
    assert (tmp_path / "mxfp8_vivado_summary.json").is_file()

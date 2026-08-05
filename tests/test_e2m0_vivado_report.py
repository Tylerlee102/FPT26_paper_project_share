from pathlib import Path

import pytest

from scripts.e2m0_vivado_report import (
    DEFAULT_REPORT_DIR,
    generate_report,
    parse_critical_path,
    parse_drc,
    parse_power,
    parse_timing_summary,
    parse_utilization,
)


def test_parsers_cover_timing_utilization_power_and_drc() -> None:
    timing = parse_timing_summary(
        "  WNS(ns) TNS(ns) TNS Failing Endpoints TNS Total Endpoints "
        "WHS(ns) THS(ns) THS Failing Endpoints THS Total Endpoints "
        "WPWS(ns) TPWS(ns) TPWS Failing Endpoints TPWS Total Endpoints\n"
        " -0.040 -0.941 53 306869 0.010 0.000 0 306555 2.050 0.000 0 116980\n"
    )
    assert timing["wns_ns"] == -0.04
    assert timing["setup_failing_endpoints"] == 53
    assert timing["hold_failing_endpoints"] == 0
    utilization = parse_utilization(
        "\n".join(
            [
                "| CLB LUTs | 208523 | 0 | 0 | 1303680 | 15.99 |",
                "| CLB Registers | 111027 | 0 | 0 | 2607360 | 4.26 |",
                "| Block RAM Tile | 353 | 0 | 0 | 2016 | 17.51 |",
                "| URAM | 624 | 0 | 0 | 960 | 65.00 |",
                "| DSPs | 44 | 0 | 0 | 9024 | 0.49 |",
                "| BUFGCE | 1 | 0 | 0 | 288 | 0.35 |",
            ]
        )
    )
    assert utilization["uram"]["used"] == 624
    power = parse_power(
        "\n".join(
            [
                "| Total On-Chip Power (W) | 6.991 |",
                "| Dynamic (W) | 3.582 |",
                "| Device Static (W) | 3.410 |",
                "| Confidence Level | Medium |",
                "| Clocks | 0.533 |",
                "| CLB Logic | 1.058 |",
                "| Signals | 1.078 |",
                "| Block RAM | 0.151 |",
                "| URAM | 0.708 |",
                "| DSPs | 0.054 |",
            ]
        )
    )
    assert power["total_on_chip_w"] == 6.991
    assert power["measured_on_board"] is False
    drc = parse_drc("DPIP-2#1 Warning\nDPOP-4#1 Warning\n")
    assert drc["signoff_status"] == "PASS_WITH_WARNINGS"
    assert drc["by_rule"] == {"DPIP-2": 1, "DPOP-4": 1}


def test_critical_path_parser_classifies_resident_uram_control() -> None:
    parsed = parse_critical_path(
        """
  Source: top/reset_reg/C
  Destination: top/resident_primary/EN_A
  Path Group: ap_clk
  Path Type: Setup (Max at Slow Process Corner)
  Data Path Delay: 4.971ns (logic 0.375ns (7.5%) route 4.596ns (92.5%))
  Logic Levels: 5 (LUT2=1 LUT5=1 LUT6=3)
  SLR Crossing[1->0]
"""
    )
    assert parsed["logic_levels"] == 5
    assert parsed["crosses_slr_1_to_0"] is True
    assert parsed["route_delay_percent"] == pytest.approx(92.456, rel=1e-3)


def test_real_corrected_postroute_evidence(tmp_path: Path) -> None:
    report = generate_report(DEFAULT_REPORT_DIR, tmp_path)
    assert report["status"] == "PASS"
    assert report["route_completion"] == "PASS"
    assert report["physical_fit"] == "PASS"
    assert report["target_clock"]["status"] == "FAIL"
    assert report["implemented_200mhz_timing"] == "FAIL"
    assert report["first_tested_closing_point"]["period_ns"] == 5.55
    assert report["first_tested_closing_point"]["frequency_mhz"] == pytest.approx(
        180.18018
    )
    assert report["utilization"]["clb_luts"]["used"] == 208_523
    assert report["utilization"]["uram"]["used"] == 624
    assert report["drc"]["signoff_status"] == "PASS_WITH_WARNINGS"
    assert report["drc"]["by_rule"] == {
        "DPIP-2": 10,
        "DPOP-3": 11,
        "DPOP-4": 16,
        "RTSTAT-10": 1,
    }
    assert report["power_at_5p6ns"]["total_on_chip_w"] == 6.991
    assert report["power_at_5p6ns"]["measured_on_board"] is False
    assert report["critical_path_at_4ns"]["classification"].startswith(
        "resident-state"
    )
    assert (tmp_path / "e2m0_postroute_summary.json").is_file()
    assert (tmp_path / "e2m0_postroute_timing_sweep.csv").is_file()
    assert (tmp_path / "e2m0_postroute_summary.md").is_file()

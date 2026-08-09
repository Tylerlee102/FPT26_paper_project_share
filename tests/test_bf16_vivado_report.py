from pathlib import Path

from scripts.bf16_vivado_report import DEFAULT_REPORT_DIR, generate_report


def test_real_bf16_physical_fit_attempt(tmp_path: Path) -> None:
    report = generate_report(DEFAULT_REPORT_DIR, tmp_path)
    assert report["status"] == "PASS"
    assert report["synthesis_completion"] == "PASS"
    assert report["placement_completion"] == "PASS"
    assert report["route_completion"] == "PASS"
    assert report["physical_fit"] == "PASS"
    assert report["target_clock"]["status"] == "FAIL"
    assert report["target_clock"]["timing"]["wns_ns"] == -3.02
    assert report["first_tested_closing_point"]["period_ns"] == 7.125
    assert report["first_tested_closing_point"]["wns_ns"] == 0.105
    assert report["utilization"]["uram"]["used"] == 928
    assert report["utilization"]["block_ram_tiles"]["used"] == 1602.5
    assert report["state_memory_organization"]["controlled_state_layout_preserved"]
    assert report["ideal_state_only_lower_bound"][
        "ideal_min_uram_if_uram_only"
    ] == 1024
    assert report["vectorless_power"]["total_on_chip_w"] == 5.648
    assert (tmp_path / "bf16_vivado_summary.json").exists()

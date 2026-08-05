from pathlib import Path

from scripts.bf16_vivado_report import DEFAULT_REPORT_DIR, generate_report


def test_real_bf16_physical_fit_attempt(tmp_path: Path) -> None:
    report = generate_report(DEFAULT_REPORT_DIR, tmp_path)
    assert report["status"] == "PASS"
    assert report["synthesis_completion"] == "PASS"
    assert report["physical_fit"] == "FAIL"
    assert report["capacity_drc"]["ramb36_fifo"] == {
        "required": 9216,
        "available": 2016,
    }
    assert report["ideal_state_only_lower_bound"]["ideal_min_uram"] == 1024
    assert report["vectorless_power"] == "NOT_RUN_PHYSICAL_FIT_FAILED"
    assert (tmp_path / "bf16_vivado_summary.json").exists()

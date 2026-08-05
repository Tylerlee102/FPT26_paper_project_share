from pathlib import Path

import pytest

from scripts.e2m0_hls_report import (
    DEFAULT_ARCHIVE,
    generate_report,
    parse_csim,
    parse_loop_cycles,
    parse_slr_utilization,
    parse_targeted_loops,
)


def test_e2m0_hls_parsers() -> None:
    assert parse_loop_cycles("|- step_e2m0_heads | 12| 34| x|", "step_e2m0_heads") == {
        "minimum": 12,
        "maximum": 34,
    }
    assert parse_targeted_loops(
        "Pipelining result : Target II = 1, Final II = 2, Depth = 10, loop 'x'"
    ) == [{"loop": "x", "target_ii": 1, "final_ii": 2, "depth": 10}]
    assert parse_slr_utilization(
        "|Utilization SLR (%)  | 6| 2| 14| 100| 35|\n"
    ) == {"BRAM_18K": 6.0, "DSP": 2.0, "FF": 14.0, "LUT": 100.0, "URAM": 35.0}
    assert parse_csim("PASS marker\nCSim done with 0 errors", "PASS marker")


def test_real_corrected_e2m0_hls_evidence(tmp_path: Path) -> None:
    report = generate_report(DEFAULT_ARCHIVE, tmp_path)
    assert report["status"] == "PASS"
    assert report["csim"]["arithmetic_267_case_status"] == "PASS"
    assert report["csim"]["exact_random_state_trace_tokens"] == 64
    assert report["csim"]["required_64_token_csim"] == "PASS"
    assert report["csim"]["required_64_token_rtl_cosimulation"] == "NOT_RUN"
    assert report["csynth"]["metrics"]["resources"]["LUT"] == 435_089
    assert report["csynth"]["metrics"]["estimated_fmax_mhz"] > 300.0
    assert report["csynth"]["configured_timing_budget_ns"] == 2.92
    assert report["csynth"]["configured_timing_shortfall_ns"] == pytest.approx(0.188)
    assert report["csynth"]["configured_timing_margin_status"] == "FAIL"
    assert report["csynth"]["targeted_loop_ii_status"] == "FAIL"
    assert len(report["csynth"]["failed_targeted_loops"]) == 3
    assert report["phase4_decision_gate"]["status"] == "FAIL"
    assert (
        report["phase4_decision_gate"]["criteria"][
            "configured_target_minus_uncertainty_timing_margin"
        ]
        == "FAIL"
    )
    assert report["hls_lut_and_nonfold_step_cost_advantage_vs_bf16"] == "FAIL"
    assert report["physical_fit"] == "NOT_RUN"
    assert report["board_energy_measurement"] == "NOT_RUN"
    assert (tmp_path / "e2m0_hls_summary.json").exists()
    assert (tmp_path / "e2m0_hls_comparison.csv").exists()

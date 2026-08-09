from pathlib import Path

from scripts.rs2_hls_report import (
    DEFAULT_CSIM,
    DEFAULT_CSYNTH,
    generate_report,
    parse_loop_cycles,
    parse_slr_resources,
    parse_targeted_loops,
)


def test_rs2_hls_parsers() -> None:
    assert parse_loop_cycles("|- step_rs2_heads | 12| 34| x|", "step_rs2_heads") == {
        "minimum": 12,
        "maximum": 34,
    }
    assert parse_targeted_loops(
        "Pipelining result : Target II = 1, Final II = 1, Depth = 3, loop 'inner'"
    ) == [{"loop": "inner", "target_ii": 1, "final_ii": 1, "depth": 3}]
    parsed = parse_slr_resources(
        "|Total                | 10| 20| 30| 40| 50|\r\n"
        "|Available SLR        | 100| 200| 300| 400| 500|\r\n"
    )
    assert parsed["utilization_percent"]["LUT"] == 10.0


def test_real_rs2_hls_evidence(tmp_path: Path) -> None:
    report = generate_report(DEFAULT_CSIM, DEFAULT_CSYNTH, tmp_path)
    assert report["status"] == "PASS"
    assert report["phase4_decision_gate"]["status"] == "PASS"
    assert report["csim"]["exact_trace64_status"] == "PASS"
    assert report["csynth"]["metrics"]["estimated_fmax_mhz"] >= 200.0
    assert report["csynth"]["targeted_loop_ii_status"] == "PASS"
    assert report["csynth"]["single_slr"]["utilization_percent"]["LUT"] < 80.0
    assert report["comparison"]["hls_cost_latency_advantage_vs_bf16"] == "FAIL"
    assert (tmp_path / "rs2_hls_summary.json").is_file()
    assert (tmp_path / "rs2_hls_comparison.csv").is_file()

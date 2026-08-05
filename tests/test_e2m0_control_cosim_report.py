from pathlib import Path

from scripts.e2m0_control_cosim_report import (
    generate_report,
    parse_cosim_report,
    parse_xsim_log,
)


def test_cosim_report_parser_requires_official_verilog_pass() -> None:
    parsed = parse_cosim_report(
        "| Verilog | Pass | 19971 | 19971 | 19971 | 20081 | 20081 | 20081 | 40052 |\n"
    )
    assert parsed["status"] == "PASS"
    assert parsed["latency_avg_cycles"] == 19_971
    assert parsed["total_execution_cycles"] == 40_052


def test_xsim_parser_requires_both_transactions_and_normal_finish() -> None:
    parsed = parse_xsim_log(
        "\n".join(
            [
                '// RTL Simulation : 0 / 2 [0.00%] @ "110000"',
                '// RTL Simulation : 1 / 2 [100.00%] @ "80858000"',
                '// RTL Simulation : 2 / 2 [100.00%] @ "161182000"',
                "$finish called at time : 161210 ns : File test.sv Line 1",
                "INFO: xsimkernel Simulation Memory Usage: 2755620 KB "
                "(Peak: 2755620 KB), Simulation CPU Usage: 20140 ms",
            ]
        )
    )
    assert parsed["status"] == "PASS"
    assert parsed["completed_transactions"] == 2
    assert parsed["finish_time_ns"] == 161_210


def test_real_e2m0_control_cosim_evidence(tmp_path: Path) -> None:
    report = generate_report(tmp_path)
    assert report["status"] == "PASS"
    assert report["official_hls_cosim"]["status"] == "PASS"
    assert report["rtl_simulation"]["completed_transactions"] == 2
    assert report["c_precheck"]["status"] == "PASS"
    assert report["c_postcheck"]["status"] == "PASS"
    assert report["recurrent_transition_covered"] is False
    assert report["required_64_token_rtl_parity"] == "NOT_RUN"
    assert (tmp_path / "e2m0_control_smoke_summary.json").is_file()
    assert (tmp_path / "e2m0_control_smoke_summary.md").is_file()
    assert (tmp_path / "raw" / "xsim.log").is_file()

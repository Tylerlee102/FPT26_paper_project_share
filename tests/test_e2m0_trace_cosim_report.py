import pytest

from scripts.e2m0_trace_cosim_report import parse_oom, parse_progress


def test_trace_progress_parser_requires_66_transactions() -> None:
    parsed = parse_progress(
        '// RTL Simulation : 0 / 66 [0.00%] @ "110000"\n'
        '// RTL Simulation : 66 / 66 [100.00%] @ "999000"\n'
    )
    assert parsed["completed_transactions"] == 66
    assert parsed["total_transactions"] == 66


def test_trace_progress_parser_rejects_other_transaction_count() -> None:
    with pytest.raises(ValueError, match="66 total"):
        parse_progress('// RTL Simulation : 2 / 2 [100.00%] @ "110000"')


def test_trace_oom_parser() -> None:
    parsed = parse_oom(
        "Out of memory on request for a fresh 8388608 bytes\n"
        "Total memory consumed so far :3820485232 bytes\n"
    )
    assert parsed == {
        "failed_allocation_bytes": 8_388_608,
        "simulator_reported_memory_consumed_bytes": 3_820_485_232,
    }

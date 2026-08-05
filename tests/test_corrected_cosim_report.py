from __future__ import annotations

from scripts.corrected_cosim_report import _parse_c_tb, _parse_hms, _parse_progress


def test_parse_progress_uses_last_completed_transaction() -> None:
    log = "\n".join(
        [
            '// RTL Simulation : 0 / 15 [0.00%] @ "110000"',
            '// RTL Simulation : 3 / 15 [100.00%] @ "236334000"',
        ]
    )
    assert _parse_progress(log) == (3, 15, 236334000)


def test_parse_c_tb_and_elapsed_time() -> None:
    assert _parse_c_tb("tb_gdn_top PASS hand_commands=12 oracle_steps=1") == (
        12,
        1,
    )
    assert _parse_hms("00:11:13") == 673

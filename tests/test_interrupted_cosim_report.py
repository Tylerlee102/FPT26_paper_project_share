from __future__ import annotations

from scripts.interrupted_cosim_report import (
    _normalize_relpath,
    _parse_progress,
    _parse_xsim_start,
)


def test_parse_progress_uses_last_completed_transaction() -> None:
    log = "\n".join(
        [
            '// RTL Simulation : 0 / 15 [0.00%] @ "110000"',
            '// RTL Simulation : 3 / 15 [100.00%] @ "236334000"',
        ]
    )
    assert _parse_progress(log) == (3, 15, 236334000)


def test_parse_xsim_start_and_normalize_windows_path() -> None:
    journal = "# Start of session at: Sat Aug  1 18:34:57 2026\n"
    assert _parse_xsim_start(journal) == "Sat Aug  1 18:34:57 2026"
    assert _normalize_relpath(r"reports\cosim\raw\xsim.log") == (
        "reports/cosim/raw/xsim.log"
    )

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.rs2_xsim_diagnostic import build


def test_bounded_xsim_attempt_is_archived_without_promoting_parity(
    tmp_path: Path,
) -> None:
    c_log = tmp_path / "c.log"
    xelab_log = tmp_path / "xelab.log"
    xsim_log = tmp_path / "xsim.log"
    c_log.write_text(
        "PASS: 8 encoded random-state tokens, exact outputs/counters, and final snapshot\n",
        encoding="utf-8",
    )
    xelab_log.write_text("Built simulation snapshot gdn_rs2_top\n", encoding="utf-8")
    xsim_log.write_text(
        "# xsim v2025.2 (64-bit)\n"
        "INFO: Starting XSIM\n"
        '// RTL Simulation : 0 / 10 [0.00%] @ "110000"\n',
        encoding="utf-8",
    )

    output = tmp_path / "report"
    report = build(c_log, xelab_log, xsim_log, output)

    assert report["status"] == "INCOMPLETE"
    assert report["required_64_token_rtl_parity"] == "NOT_RUN"
    assert report["milestones"] == {
        "eight_token_c_transaction_generation": "PASS",
        "xelab": "PASS",
        "xsim_launch": "PASS",
        "completed_transactions": 0,
        "total_transactions": 10,
    }
    saved = json.loads((output / "rs2_xsim_diagnostic.json").read_text())
    assert saved == report
    for relative, row in report["raw_artifacts"].items():
        archived = Path(relative)
        if not archived.is_absolute():
            archived = Path(__file__).resolve().parents[1] / archived
        assert row["sha256"] == hashlib.sha256(archived.read_bytes()).hexdigest().upper()

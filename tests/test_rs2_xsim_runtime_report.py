from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.rs2_xsim_runtime_report import build


def test_xsim_runtime_report_preserves_parity_boundary(tmp_path: Path) -> None:
    xsim = tmp_path / "xsim.log"
    direct = tmp_path / "direct.log"
    xsim.write_text(
        "RS2_DIRECT_RTL command=1 cycles=4447475 status=0 generation=1\n"
        "RS2_DIRECT_RTL_BENCHMARK PASS tokens=0\n"
        "run: Time (s): cpu = 00:00:00 ; elapsed = 00:08:22 .\n"
        "INFO: xsimkernel Simulation CPU Usage: 500609 ms\n",
        encoding="utf-8",
    )
    direct.write_text(
        "".join(
            f"RS2_DIRECT_RTL command=2 cycles={index + 1} status=0 generation=1\n"
            for index in range(66)
        ),
        encoding="utf-8",
    )

    report = build(xsim, direct, tmp_path / "report")

    assert report["status"] == "PASS"
    assert report["benchmark"]["cycles_per_second"] == pytest.approx(
        4447475 / 502
    )
    projection = report["full_trace_projection"]
    assert projection["cycles"] == sum(range(1, 67))
    assert projection["official_xsim_64_token_status"] == "NOT_RUN"
    saved = json.loads(
        (tmp_path / "report" / "rs2_xsim_runtime.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved == report

from __future__ import annotations

import json

import pytest

from scripts.direct_rtl_report import DEFAULT_EVIDENCE, parse_xsim_log


SAMPLE = """
DIRECT_RTL command=0 latched=0 cycles=33386 status=0 generation=0
DIRECT_RTL command=2 latched=2 cycles=5597299 status=0 generation=1
DIRECT_RTL command=3 latched=3 cycles=2192044 status=0 generation=1
DIRECT_RTL_SMOKE PASS reset_step_readback=3
INFO: xsimkernel Simulation Memory Usage: 83580 KB (Peak: 83580 KB), Simulation CPU Usage: 155374 ms
"""


def test_parse_direct_rtl_smoke() -> None:
    result = parse_xsim_log(SAMPLE)
    assert [row["cycles"] for row in result["commands"]] == [33386, 5597299, 2192044]
    assert result["xsim_kernel"]["peak_memory_kb"] == 83580
    assert all(status == "PASS" for status in result["checks"].values())


def test_rejects_wrong_latched_command() -> None:
    with pytest.raises(ValueError, match="latched"):
        parse_xsim_log(SAMPLE.replace("command=2 latched=2", "command=2 latched=0"))


def test_current_summary_when_present() -> None:
    path = DEFAULT_EVIDENCE / "direct_rtl_smoke_summary.json"
    if not path.exists():
        pytest.skip("direct RTL smoke report has not been generated")
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["required_64_token_rtl_parity"] == "NOT_RUN"
    assert report["generated_rtl"]["file_count"] >= 80
    assert report["simulator"]["peak_memory_kb"] < 1_000_000

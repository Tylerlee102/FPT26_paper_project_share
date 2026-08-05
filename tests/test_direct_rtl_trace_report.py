from __future__ import annotations

import json

import pytest

from scripts.direct_rtl_trace_report import (
    DEFAULT_EVIDENCE,
    ROOT,
    parse_trace_xsim_log,
    report_source_paths,
)


def _sample() -> str:
    lines = ["DIRECT_RTL command=0 latched=0 cycles=33386 status=0 generation=0"]
    for token in range(1, 65):
        lines.append(
            f"DIRECT_RTL command=2 latched=2 cycles={5_400_000 + token} "
            f"status=0 generation={token}"
        )
        lines.append(
            f"DIRECT_RTL_TRACE token={token} status=0 generation={token} PASS"
        )
    lines.extend(
        [
            "DIRECT_RTL command=3 latched=3 cycles=2192044 status=0 generation=64",
            "DIRECT_RTL_TRACE64 PASS tokens=64 outputs_per_token=4096 state_elements=524288",
            "INFO: xsimkernel Simulation Memory Usage: 90000 KB (Peak: 95000 KB), Simulation CPU Usage: 1000 ms",
        ]
    )
    return "\n".join(lines)


def test_parse_complete_trace() -> None:
    result = parse_trace_xsim_log(_sample())
    assert result["step_latency_cycles"]["count"] == 64
    assert result["token_rows"][-1] == (64, 0, 64)
    assert result["xsim_kernel"]["peak_memory_kb"] == 95000


def test_rejects_missing_token() -> None:
    with pytest.raises(ValueError, match="64 ordered token"):
        parse_trace_xsim_log(
            _sample().replace(
                "DIRECT_RTL_TRACE token=32 status=0 generation=32 PASS\n", ""
            )
        )


def test_reporter_source_tree_contains_hls_implementation() -> None:
    sources = set(report_source_paths())
    assert set((ROOT / "hls" / "include").glob("*.hpp")) <= sources
    assert set((ROOT / "hls" / "src").glob("*.cpp")) <= sources
    assert set((ROOT / "hls" / "tcl").glob("*.tcl")) <= sources
    assert ROOT / "hls" / "rtl_tb" / "tb_gdn_top_direct.sv" in sources


def test_current_summary_when_present() -> None:
    path = DEFAULT_EVIDENCE / "direct_rtl_trace64_summary.json"
    if not path.exists():
        pytest.skip("64-token direct RTL report has not been generated")
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["required_64_token_rtl_parity"] == "PASS"
    assert report["parity"]["ordered_tokens"] == 64
    assert report["parity"]["final_state_elements_compared"] == 524288
    assert report["source_identity"]["dirty_patch"]["sha256"]
    assert all(entry["exit_code"] == 0 for entry in report["execution"])

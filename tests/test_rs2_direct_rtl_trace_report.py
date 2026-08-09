from __future__ import annotations

import inspect

import pytest

from scripts.generate_rs2_direct_rtl_trace_assets import parse_trace
from scripts.rs2_direct_rtl_flow import _build_key, run_flow
from scripts.rs2_direct_rtl_trace_report import parse_simulation_log


def _sample_log() -> tuple[str, list[int]]:
    expected_live = parse_trace()["expected"]["live"]
    lines = ["RS2_DIRECT_RTL command=1 cycles=100 status=0 generation=1"]
    for token, live in enumerate(expected_live, start=1):
        generation = token + 1
        lines.append(
            f"RS2_DIRECT_RTL command=2 cycles={1000 + token} "
            f"status=0 generation={generation}"
        )
        lines.append(
            f"RS2_DIRECT_RTL_TOKEN token={token} status=0 "
            f"generation={generation} live={live} PASS"
        )
    lines.extend(
        [
            "RS2_DIRECT_RTL command=3 cycles=200 status=0 generation=65",
            "RS2_DIRECT_RTL_TRACE64 PASS tokens=64 transactions=66 "
            "outputs=262144 final_snapshot=PASS",
        ]
    )
    return "\n".join(lines), expected_live


def test_parse_complete_rs2_trace() -> None:
    text, expected_live = _sample_log()
    parsed = parse_simulation_log(text, expected_live)
    assert len(parsed["commands"]) == 66
    assert len(parsed["tokens"]) == 64
    assert parsed["step_latency_cycles"]["minimum"] == 1001
    assert parsed["step_latency_cycles"]["maximum"] == 1064


def test_rejects_missing_rs2_token_marker() -> None:
    text, expected_live = _sample_log()
    with pytest.raises(ValueError, match="64 ordered"):
        parse_simulation_log(
            text.replace(
                "RS2_DIRECT_RTL_TOKEN token=32 status=0 generation=33 "
                f"live={expected_live[31]} PASS\n",
                "",
            ),
            expected_live,
        )


def test_rs2_direct_flow_cache_excludes_token_limit() -> None:
    source = inspect.getsource(run_flow)
    assert "token_limit" not in inspect.getsource(_build_key)
    assert "build_cache_key" in source
    assert "36 * 3600 if token_limit == 64" in source
    assert 'evidence / "benchmarks"' in source

from __future__ import annotations

from scripts.generate_e2m0_direct_rtl_trace_assets import parse_trace


def test_e2m0_trace_dimensions_and_terminal_metadata() -> None:
    trace = parse_trace()
    dimensions = trace["dimensions"]
    assert dimensions["tokens"] == 64
    assert dimensions["num_qk_heads"] == 16
    assert dimensions["num_value_heads"] == 32
    assert dimensions["key_dim"] == 128
    assert dimensions["value_dim"] == 128
    assert dimensions["block_size"] == 32
    assert dimensions["stack_depth"] == 2
    assert dimensions["log_capacity"] == 7
    assert trace["expected"]["status"] == [0] * 64
    assert trace["expected"]["generation"] == list(range(2, 66))
    assert trace["final"]["status"] == 0
    assert trace["final"]["generation"] == 65
    assert trace["final"]["live"] == 1


def test_e2m0_trace_stream_and_snapshot_lengths() -> None:
    trace = parse_trace()
    dimensions = trace["dimensions"]
    streams = trace["streams"]
    assert len(streams["q"]) == 64 * dimensions["q_elements"]
    assert len(streams["q_scales"]) == 64 * dimensions["q_scales"]
    assert len(streams["v"]) == 64 * dimensions["v_elements"]
    assert len(streams["alpha"]) == 64 * dimensions["gate_elements"]
    assert len(trace["expected"]["command_counters"]) == 64 * 8
    assert len(trace["expected"]["output_mantissas"]) == 64 * 4096
    assert len(trace["expected"]["output_exponents"]) == 64 * 4096
    assert len(trace["initial"]["primary"]) == dimensions["state_elements"]
    assert len(trace["final"]["residual_scales"]) == dimensions["state_scales"]

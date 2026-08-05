from __future__ import annotations

from scripts.generate_direct_rtl_trace_assets import parse_trace


def test_verified_trace_dimensions_and_terminal_metadata() -> None:
    trace = parse_trace()
    dimensions = trace["dimensions"]
    assert dimensions == {
        "tokens": 64,
        "num_qk_heads": 16,
        "num_value_heads": 32,
        "key_dim": 128,
        "value_dim": 128,
        "block_size": 32,
        "counter_count": 8,
        "output_elements": 4096,
    }
    assert trace["status"] == [0] * 64
    assert trace["generation"] == list(range(1, 65))
    assert trace["readback_status"] == 0
    assert trace["readback_generation"] == 64
    assert len(trace["final_state"]) == 32 * 128 * 128
    assert len(trace["final_scales"]) == 32 * 128 * 4


def test_trace_stream_and_oracle_lengths() -> None:
    trace = parse_trace()
    streams = trace["streams"]
    assert len(streams["q"]) == 64 * 16 * 128
    assert len(streams["q_scales"]) == 64 * 16 * 4
    assert len(streams["v"]) == 64 * 32 * 128
    assert len(streams["alpha"]) == 64 * 32 * 2
    assert len(trace["command_counters"]) == 64 * 8
    assert len(trace["output_mantissas"]) == 64 * 4096
    assert len(trace["output_exponents"]) == 64 * 4096

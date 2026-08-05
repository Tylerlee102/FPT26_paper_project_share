import json
from pathlib import Path

import numpy as np

import scripts.long_sequence_stability as stability
from scripts.long_sequence_stability import TraceConfiguration
from scripts.write_log_stability import _trace_initial_state


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs" / "synthetic_trace_protocol.json"


class _RecordingGenerator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float, float, object]] = []

    def normal(self, mean: float, standard_deviation: float, *, size: object):
        self.calls.append(("normal", mean, standard_deviation, size))
        return np.zeros(size, dtype=np.float32)

    def uniform(self, low: float, high: float, *, size: object):
        self.calls.append(("uniform", low, high, size))
        return np.full(size, low, dtype=np.float32)


class _UnitGenerator:
    def normal(self, _mean: float, _standard_deviation: float, *, size: object):
        return np.ones(size, dtype=np.float32)

    def uniform(self, low: float, _high: float, *, size: object):
        return np.full(size, low, dtype=np.float32)


def _configuration(trace_family: str) -> TraceConfiguration:
    return TraceConfiguration(
        tokens=1,
        checkpoints=(1,),
        seed=0xFB72,
        split="protocol_test",
        trace_family=trace_family,
        num_value_heads=32,
        num_qk_heads=16,
        key_dim=128,
        value_dim=128,
        activation_block_size=32,
        state_block_size=32,
    )


def test_synthetic_trace_protocol_matches_executed_generators(monkeypatch) -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "PASS"
    assert protocol["schema"] == 3
    assert protocol["dimensions"] == {
        "num_qk_heads": 16,
        "num_value_heads": 32,
        "key_dim": 128,
        "value_dim": 128,
    }
    assert protocol["required_checkpoints"] == [64, 256, 1024, 4096, 8192]
    assert protocol["statistical_unit"]["independent_test_streams"] == 3
    assert protocol["statistical_unit"]["paired_conditions"] == 6

    recorder = _RecordingGenerator()
    monkeypatch.setattr(stability, "_token_rng", lambda *_: recorder)
    nominal = _configuration("nominal")
    stability._initial_state(nominal)
    stability._token_inputs(nominal, 0)

    initial = protocol["random_initial_state"]
    inputs = protocol["token_inputs"]
    nominal_ranges = protocol["trace_families"]["nominal"]
    expected = [
        (
            "normal",
            initial["mean"],
            initial["standard_deviation"],
            (32, 128, 128),
        ),
        (
            "normal",
            inputs["query"]["mean"],
            inputs["query"]["standard_deviation"],
            (16, 128),
        ),
        (
            "normal",
            inputs["key"]["mean"],
            inputs["key"]["standard_deviation"],
            (16, 128),
        ),
        (
            "normal",
            inputs["value"]["mean"],
            inputs["value"]["standard_deviation"],
            (32, 128),
        ),
        ("uniform", *nominal_ranges["alpha_uniform"], 32),
        ("uniform", *nominal_ranges["beta_uniform"], 32),
    ]
    assert recorder.calls == expected

    recorder.calls.clear()
    stability._token_inputs(_configuration("high_retention"), 0)
    high_retention = protocol["trace_families"]["high_retention"]
    assert recorder.calls[-2:] == [
        ("uniform", *high_retention["alpha_uniform"], 32),
        ("uniform", *high_retention["beta_uniform"], 32),
    ]


def test_synthetic_trace_protocol_matches_supplemental_stress_transforms(
    monkeypatch,
) -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    monkeypatch.setattr(stability, "_token_rng", lambda *_: _UnitGenerator())

    dynamic_zero = stability._token_inputs(_configuration("dynamic_range"), 0)
    dynamic_next_segment = stability._token_inputs(
        _configuration("dynamic_range"), 32
    )
    assert np.all(dynamic_zero[2] == np.float32(2.0**-4))
    assert np.all(dynamic_next_segment[2] == np.float32(2.0**-3))
    dynamic_contract = protocol["trace_families"]["dynamic_range"]
    assert dynamic_contract["value_scale_power"] == {
        "formula": "(token_zero_based // 32) % 9 - 4",
        "minimum": -4,
        "maximum": 4,
        "segment_tokens": 32,
        "period_tokens": 288,
    }

    cancellation_even = stability._token_inputs(_configuration("cancellation"), 0)
    cancellation_odd = stability._token_inputs(_configuration("cancellation"), 1)
    for index in (0, 1, 2):
        assert np.all(cancellation_even[index] == 1.0)
        assert np.all(cancellation_odd[index] == -1.0)
    stress = protocol["executed_supplemental_stress"]
    assert stress["tokens_per_family"] == 8192
    assert stress["token_rows"] == 81920
    assert stress["checkpoint_rows"] == 50


def test_synthetic_trace_protocol_matches_zero_initial_state() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    state = _trace_initial_state(_configuration("high_retention"), "zero")
    assert np.all(state == protocol["zero_initial_state"]["value"])


def test_synthetic_trace_protocol_matches_relative_l2_floor() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    floor = protocol["metrics"]["relative_l2_denominator_floor"]
    metrics = stability._error_metrics(
        np.zeros(1, dtype=np.float32), np.ones(1, dtype=np.float32)
    )
    assert metrics["rel_l2"] == 1.0 / floor


def test_synthetic_trace_protocol_matches_flattening_and_zero_norm_rules() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    metrics_contract = protocol["metrics"]
    assert metrics_contract["headwise_metrics"] == "NOT_RUN"
    assert metrics_contract["cosine_denominator_floor"] == 1e-24

    shaped_reference = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
    shaped_candidate = shaped_reference.copy()
    shaped_candidate[1, 2, 3] += 1.0
    shaped = stability._error_metrics(shaped_reference, shaped_candidate)
    flat = stability._error_metrics(shaped_reference.reshape(-1), shaped_candidate.reshape(-1))
    assert shaped == flat

    identical_zero = stability._error_metrics(
        np.zeros(4, dtype=np.float32), np.zeros(4, dtype=np.float32)
    )
    one_sided_zero = stability._error_metrics(
        np.zeros(4, dtype=np.float32), np.ones(4, dtype=np.float32)
    )
    assert identical_zero == {"cosine": 1.0, "rel_l2": 0.0, "max_abs": 0.0}
    assert one_sided_zero["cosine"] == 0.0

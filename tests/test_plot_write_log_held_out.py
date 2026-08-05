from __future__ import annotations

import pytest

from scripts.plot_write_log_held_out import _aggregate_traces


def _row(token: int, cosine: float, state: float) -> dict[str, str]:
    return {
        "token_index": str(token),
        "output_cosine_fp32": str(cosine),
        "state_rel_l2": str(state),
    }


def test_aggregate_traces_reports_mean_and_envelope() -> None:
    rows = _aggregate_traces(
        [
            [_row(1, 0.99, 0.08), _row(2, 0.98, 0.09)],
            [_row(1, 1.00, 0.10), _row(2, 0.96, 0.07)],
        ]
    )

    assert rows[0] == {
        "token_index": 1,
        "trace_count": 2,
        "output_cosine_mean": pytest.approx(0.995),
        "output_cosine_min": pytest.approx(0.99),
        "output_cosine_max": pytest.approx(1.0),
        "state_rel_l2_mean": pytest.approx(0.09),
        "state_rel_l2_min": pytest.approx(0.08),
        "state_rel_l2_max": pytest.approx(0.10),
    }


def test_aggregate_traces_rejects_token_mismatch() -> None:
    with pytest.raises(ValueError, match="trace token mismatch"):
        _aggregate_traces(
            [
                [_row(1, 0.99, 0.08)],
                [_row(2, 0.99, 0.08)],
            ]
        )

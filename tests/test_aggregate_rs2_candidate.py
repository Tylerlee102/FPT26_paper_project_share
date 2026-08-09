from __future__ import annotations

import json

from scripts.aggregate_rs2_candidate import OUTPUT_JSON


def test_rs2_candidate_test_and_extended_gates_pass() -> None:
    summary = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["candidate_evidence_status"] == "PASS"
    assert summary["gate_results"]["held_out"]["status"] == "PASS"
    assert summary["gate_results"]["held_out"]["run_count"] == 6
    assert summary["gate_results"]["extended_development"]["status"] == "PASS"
    assert summary["gate_results"]["extended_development"]["run_count"] == 2
    assert len(summary["runs"]) == 8


def test_rs2_candidate_clears_registered_all_token_thresholds() -> None:
    summary = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    gate = summary["quality_gate"]
    for result in summary["gate_results"].values():
        assert result["minimum_all_token_output_cosine"] >= gate[
            "minimum_all_token_output_cosine"
        ]
        assert result["maximum_all_token_state_relative_l2"] <= gate[
            "maximum_all_token_state_relative_l2"
        ]

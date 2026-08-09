from __future__ import annotations

from scripts.aggregate_rs2_encoded_candidate import aggregate


def test_held_out_encoded_gate_passes_all_registered_runs() -> None:
    summary = aggregate()
    held_out = summary["gate_results"]["held_out"]
    assert held_out["status"] == "PASS"
    assert held_out["run_count"] == 6
    assert held_out["minimum_all_token_output_cosine"] >= 0.99
    assert held_out["maximum_all_token_state_relative_l2"] <= 0.10
    assert held_out["cumulative_element_saturations"] == 0
    assert held_out["cumulative_accumulator_saturations"] == 0
    assert held_out["cumulative_scale_clamps"] == 0


def test_encoded_summary_remains_partial_until_8192_runs_exist() -> None:
    summary = aggregate()
    extended = summary["gate_results"]["extended_development"]
    assert extended["status"] in {"NOT_RUN", "PARTIAL", "PASS"}
    assert summary["status"] == (
        "PASS" if extended["status"] == "PASS" else "PARTIAL"
    )

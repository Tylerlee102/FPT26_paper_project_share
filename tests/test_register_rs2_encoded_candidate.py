from __future__ import annotations

from scripts.register_rs2_encoded_candidate import generate_registration
from scripts.rs2_encoded_stability import VARIANT


def test_registration_freezes_encoded_r3_and_retains_r2_failure(tmp_path) -> None:
    output = tmp_path / "registration.json"
    payload = generate_registration(output)
    assert output.is_file()
    assert payload["registration_status"] == "PASS"
    assert payload["candidate_evidence_status"] == "NOT_RUN"
    assert payload["candidate_name"] == VARIANT
    assert payload["controlled_configuration"]["log_capacity"] == 3
    assert payload["logical_state_bytes"]["encoded_candidate"] == 576_912
    assert payload["mitigation_history"][0]["status"] == "FAIL"
    assert payload["mitigation_history"][0]["all_token_state_relative_l2_max"] > 0.10
    assert payload["held_out_gate"]["status"] == "NOT_RUN"

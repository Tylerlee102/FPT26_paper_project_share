from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.register_rs2_candidate import CANDIDATE, OUTPUT


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_rs2_candidate_is_frozen_before_test_set_execution() -> None:
    registration = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert registration["registration_status"] == "PASS"
    assert registration["candidate_evidence_status"] == "NOT_RUN"
    assert registration["candidate_name"] == CANDIDATE
    assert registration["controlled_configuration"]["log_capacity"] == 2
    assert registration["held_out_gate"]["status"] == "NOT_RUN"
    assert registration["held_out_gate"]["run_count"] == 6
    assert registration["extended_development_gate"]["status"] == "NOT_RUN"
    assert registration["logical_state_bytes"]["planned_q1_15_hardware"] < 1048576
    for relative, expected in registration["frozen_source_sha256"].items():
        assert _sha256(ROOT / relative) == expected


def test_registered_development_rows_clear_frozen_thresholds() -> None:
    registration = json.loads(OUTPUT.read_text(encoding="utf-8"))
    gate = registration["quality_gate"]
    for result in registration["development_gate"]["results"].values():
        assert result["minimum_checkpoint_output_cosine"] >= gate[
            "minimum_checkpoint_output_cosine"
        ]
        assert result["minimum_all_token_output_cosine"] >= gate[
            "minimum_all_token_output_cosine"
        ]
        assert result["final_state_relative_l2"] <= gate[
            "maximum_final_state_relative_l2"
        ]
        assert result["maximum_all_token_state_relative_l2"] <= gate[
            "maximum_all_token_state_relative_l2"
        ]
        assert result["dropped_entries"] == 0

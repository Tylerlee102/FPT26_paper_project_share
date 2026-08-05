from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "e2m0_encoded_preregistration.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_encoded_registration_is_frozen_before_held_out_execution() -> None:
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    assert registration["registration_status"] == "PASS"
    assert registration["candidate_evidence_status"] == "NOT_RUN"
    assert registration["held_out_gate"]["status"] == "NOT_RUN"
    assert registration["held_out_gate"]["run_count"] == 6
    assert len(set(registration["held_out_gate"]["seeds"])) == 3
    assert registration["development_gate"]["seed"] not in set(
        registration["held_out_gate"]["seeds"]
    )
    for relative, expected in registration["frozen_source_sha256"].items():
        assert _sha256(ROOT / relative) == expected
    for relative, expected in registration["development_gate"][
        "verified_manifests"
    ].items():
        assert _sha256(ROOT / relative) == expected
    for relative, expected in registration["development_gate"][
        "verification_sha256"
    ].items():
        assert _sha256(ROOT / relative) == expected

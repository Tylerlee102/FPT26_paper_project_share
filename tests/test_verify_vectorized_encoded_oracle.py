from __future__ import annotations

import json

from scripts.verify_vectorized_encoded_oracle import DEFAULT_OUTPUT


def test_vectorized_encoded_oracle_report_passes() -> None:
    report = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["configuration"]["tokens"] == 64
    assert report["comparisons"]["output_mantissas"] == 64 * 32 * 128
    assert report["comparisons"]["final_state_elements"] == 32 * 128 * 128
    assert report["source_identity"]["dirty_patch"]["sha256"]

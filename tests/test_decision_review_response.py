from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESPONSE = ROOT / "docs" / "decision_review_response.md"


def test_decision_review_response_maps_every_numbered_comment() -> None:
    text = RESPONSE.read_text(encoding="utf-8")
    rows = re.findall(
        r"^\| (D[123]\.\d+) \|.*?\| (PASS|FAIL|NOT_RUN|BLOCKED_EXTERNAL) \|$",
        text,
        flags=re.MULTILINE,
    )
    assert len(rows) == 29
    assert len({row[0] for row in rows}) == 29
    assert Counter(status for _, status in rows) == {
        "PASS": 25,
        "BLOCKED_EXTERNAL": 4,
    }
    assert {f"D1.{index}" for index in range(1, 8)} <= {row[0] for row in rows}
    assert {f"D2.{index}" for index in range(1, 15)} <= {row[0] for row in rows}
    assert {f"D3.{index}" for index in range(1, 9)} <= {row[0] for row in rows}


def test_decision_response_preserves_nonpassing_evidence_boundaries() -> None:
    text = RESPONSE.read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", " ", text).lower()
    for phrase in (
        "matched bf16 and native-mxfp8 hls",
        "closed-loop real-model quality",
        "complete-model residency",
        "board parity and energy",
        "same-boundary native-fp4 gpu comparison remain externally blocked",
        "not paper ready",
        "visibly watermarked working draft",
    ):
        assert phrase in normalized
    assert "ready for human submission review" not in normalized
    assert "all release-required traceability and pdf-audit gates now pass" not in normalized

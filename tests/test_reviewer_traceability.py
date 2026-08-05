from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACEABILITY = ROOT / "docs" / "reviewer_traceability.md"
WORKBOOK = (
    ROOT / "legacy" / "reviewer_sources" / "overleaf-comments-2026-06-18.xlsx"
)
EXPECTED_WORKBOOK_SHA256 = (
    "C4A70E704BEBDC8126540B2FEEBB25A26FA3672DBE79F9AE08157E27FDA7E54E"
)
ALLOWED_STATUSES = {"PASS", "FAIL", "NOT_RUN", "BLOCKED_EXTERNAL"}
ROW_PATTERN = re.compile(
    r"^\| R(?P<index>\d{2}): `(?P<thread>[^`]+)` reply "
    r"(?P<reply>\d+) \|.*\| (?P<status>[A-Z_]+) \|$"
)


def test_authoritative_reviewer_ledger_is_complete_and_frozen() -> None:
    text = TRACEABILITY.read_text(encoding="utf-8")
    rows = [
        match.groupdict()
        for line in text.splitlines()
        if (match := ROW_PATTERN.match(line)) is not None
    ]
    assert len(rows) == 68
    assert [int(row["index"]) for row in rows] == list(range(1, 69))
    assert len({(row["thread"], row["reply"]) for row in rows}) == 68
    assert {row["status"] for row in rows} <= ALLOWED_STATUSES
    assert WORKBOOK.is_file()
    assert hashlib.sha256(WORKBOOK.read_bytes()).hexdigest().upper() == (
        EXPECTED_WORKBOOK_SHA256
    )


def test_reviewer_rows_are_promoted_after_hash_bound_visual_audit() -> None:
    text = TRACEABILITY.read_text(encoding="utf-8")
    rows = [
        match.groupdict()
        for line in text.splitlines()
        if (match := ROW_PATTERN.match(line)) is not None
    ]
    assert rows
    assert all(row["status"] == "PASS" for row in rows)
    assert (ROOT / "paper" / "corrected" / "paper_visual_audit.json").is_file()

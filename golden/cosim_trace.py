"""Helpers for checking byte-identical cosimulation traces."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CosimMismatch:
    row: int
    name: str
    expected: str
    actual: str


def compare_trace_csv(path: str | Path) -> list[CosimMismatch]:
    """Compare `expected_hex` and `actual_hex` columns in a cosim CSV trace."""

    mismatches: list[CosimMismatch] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"name", "expected_hex", "actual_hex"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"trace CSV is missing columns: {sorted(missing)}")
        for row_number, row in enumerate(reader, start=2):
            expected = (row["expected_hex"] or "").strip().lower()
            actual = (row["actual_hex"] or "").strip().lower()
            if expected != actual:
                mismatches.append(
                    CosimMismatch(
                        row=row_number,
                        name=(row["name"] or "").strip(),
                        expected=expected,
                        actual=actual,
                    )
                )
    return mismatches


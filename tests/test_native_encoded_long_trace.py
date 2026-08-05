from __future__ import annotations

import csv
import json

from scripts.native_encoded_long_trace import DEFAULT_TOKEN_CSV
from scripts.verify_native_encoded_long_trace import (
    DEFAULT_OUTPUT,
    verify_native_encoded_long_trace,
)


def test_native_encoded_long_trace_artifacts_pass_independent_verification() -> None:
    result = verify_native_encoded_long_trace()
    assert result["status"] == "PASS"
    assert result["rows_verified"] == 8192
    assert result["checkpoint_rows_verified"] == 5
    assert result["snapshots_verified"] == 6


def test_native_encoded_long_trace_verification_report_matches() -> None:
    report = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["rows_verified"] == 8192
    assert report["engineering_gate"] in {"PASS", "FAIL"}


def test_native_encoded_trace_crosses_diagnostic_limits_at_token_one() -> None:
    with DEFAULT_TOKEN_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 8192
    assert int(rows[0]["token_index"]) == 1
    assert all(float(row["output_cosine_fp32"]) < 0.99 for row in rows)
    assert all(float(row["state_rel_l2"]) > 0.10 for row in rows)

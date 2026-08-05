from __future__ import annotations

from pathlib import Path

from scripts.e2m0_rtl_completion_report import generate_report


def test_current_completion_report_preserves_the_partial_evidence_boundary(
    tmp_path: Path,
) -> None:
    report = generate_report(tmp_path / "report")
    assert report["status"] == "PARTIAL"
    assert report["hls_c_simulation"]["status"] == "PASS"
    assert report["direct_generated_rtl_load"]["status"] == "PASS"
    assert report["direct_generated_rtl_load"]["completed_transactions"] == 1
    assert report["official_hls_xsim"]["independent_attempts"] == 2
    assert report["rtl_simulation"]["completed_recurrent_steps"] == 0
    assert report["required_64_token_rtl_parity"] == "NOT_ESTABLISHED"
    assert report["parity"]["output_values_compared"] == 0

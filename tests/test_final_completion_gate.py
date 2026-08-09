from __future__ import annotations

import subprocess

import pytest

from scripts.final_completion_gate import (
    FINAL_GATES,
    GATE_NAMES,
    ROOT,
    evaluate,
    write_report,
)


def test_current_gate_uses_all_eleven_release_requirements() -> None:
    report = evaluate(FINAL_GATES)

    assert tuple(row["gate"] for row in FINAL_GATES) == GATE_NAMES
    assert report["gate_count"] == report["required_gate_count"] == 11
    assert all(row["release_required"] is True for row in FINAL_GATES)
    assert report["status"] == "FAIL"
    assert report["release_state"] == "NOT PAPER READY"
    assert report["paper_pdf_permitted"] is False
    assert report["required_nonpassing_gate_count"] == report["nonpassing_gate_count"]
    assert report["required_nonpassing_gate_count"] >= 1


def test_current_gate_preserves_empirical_and_external_failures() -> None:
    by_name = {row["gate"]: row for row in FINAL_GATES}

    assert by_name["prior_art_gap"]["status"] == "PASS"
    assert by_name["exact_official_recurrence_parity"]["status"] == "PASS"
    assert by_name["independent_bit_exact_mx_reference"]["status"] == "PASS"
    assert by_name["selected_method_pareto_advantage"]["status"] == "FAIL"
    assert (
        by_name["selected_method_pareto_advantage"]["substatus"]
        ["hls_lut_and_latency_vs_bf16"]
        == "FAIL"
    )
    assert by_name["closed_loop_real_model_quality"]["status"] in {
        "PASS",
        "FAIL",
        "BLOCKED_EXTERNAL",
    }
    assert by_name["real_board_parity_and_energy"]["status"] in {
        "PASS",
        "FAIL",
        "BLOCKED_EXTERNAL",
    }


def test_all_pass_is_the_only_ready_state() -> None:
    all_pass = tuple({**row, "status": "PASS"} for row in FINAL_GATES)
    report = evaluate(all_pass)

    assert report["status"] == "PASS"
    assert report["release_state"] == "READY FOR HUMAN SUBMISSION REVIEW"
    assert report["paper_pdf_permitted"] is True
    assert report["required_nonpassing_gate_count"] == 0


@pytest.mark.parametrize("status", ["FAIL", "NOT_RUN", "BLOCKED_EXTERNAL"])
def test_any_nonpass_status_blocks_release(status: str) -> None:
    gates = tuple(
        {**row, "status": status if index == 0 else "PASS"}
        for index, row in enumerate(FINAL_GATES)
    )
    report = evaluate(gates)

    assert report["status"] == "FAIL"
    assert report["release_state"] == "NOT PAPER READY"
    assert report["paper_pdf_permitted"] is False
    assert report["required_nonpassing_gate_count"] == 1


def test_invalid_status_is_rejected() -> None:
    invalid = ({"gate": "example", "status": "PENDING"},)

    with pytest.raises(ValueError, match="invalid final-gate status"):
        evaluate(invalid)


def test_written_gate_uses_live_source_revision(tmp_path) -> None:
    expected = subprocess.check_output(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "rev-parse",
            "HEAD",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    report = write_report(tmp_path / "gate.json", tmp_path / "gate.md")
    assert report["source_revision"] == expected

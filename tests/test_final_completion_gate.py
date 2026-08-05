from __future__ import annotations

import subprocess

import pytest

from scripts.final_completion_gate import FINAL_GATES, ROOT, evaluate, write_report


def test_current_gate_is_ready_despite_scoped_negative_outcomes() -> None:
    report = evaluate(FINAL_GATES)

    assert report["status"] == "PASS"
    assert report["release_state"] == "READY FOR HUMAN SUBMISSION REVIEW"
    assert report["paper_pdf_permitted"] is True
    assert report["nonpassing_gate_count"] == sum(
        row["status"] != "PASS" for row in FINAL_GATES
    )
    assert report["required_nonpassing_gate_count"] == sum(
        row["status"] != "PASS" and row.get("release_required", True)
        for row in FINAL_GATES
    )
    assert report["required_nonpassing_gate_count"] == 0
    assert report["nonpassing_gate_count"] >= 1
    assert next(row for row in FINAL_GATES if row["gate"] == "prior_art_gap")[
        "status"
    ] == "PASS"
    pareto = next(
        row for row in FINAL_GATES if row["gate"] == "selected_method_pareto_advantage"
    )
    assert pareto["status"] == "FAIL"
    assert pareto["release_required"] is False
    assert pareto["substatus"]["high_retention_1024_quality"] == "PASS"
    assert pareto["substatus"]["full_deterministic_recompute"] == "PASS"
    assert pareto["substatus"]["extended_8192_quality"] in {
        "PASS",
        "FAIL",
        "NOT_RUN",
    }
    assert pareto["substatus"]["hls_explicit_ii1_constraints"] == "FAIL"
    assert pareto["substatus"]["hls_configured_timing_margin"] == "FAIL"
    assert pareto["substatus"]["hls_lut_and_step_cost_vs_bf16"] == "FAIL"
    parity = next(row for row in FINAL_GATES if row["gate"] == "c_sim_and_rtl_parity")
    assert parity["status"] == "FAIL"
    assert parity["release_required"] is False
    assert parity["substatus"]["corrected_candidate_hls_c_sim_64_token"] == "PASS"
    assert parity["substatus"]["corrected_candidate_rtl_control_smoke"] == "PASS"
    assert parity["substatus"]["corrected_candidate_rtl_64_token"] == "FAIL"
    assert next(
        row for row in FINAL_GATES if row["gate"] == "matched_native_mxfp8_baseline"
    )["status"] == "PASS"
    assert next(
        row for row in FINAL_GATES if row["gate"] == "controlled_wider_physical_baselines"
    )["status"] == "FAIL"
    assert next(
        row for row in FINAL_GATES if row["gate"] == "closed_loop_real_model_quality"
    )["status"] == "BLOCKED_EXTERNAL"
    assert next(
        row for row in FINAL_GATES if row["gate"] == "real_board_parity_and_energy"
    )["status"] == "BLOCKED_EXTERNAL"
    physical = next(
        row for row in FINAL_GATES if row["gate"] == "physical_all_layer_state_bank_fit"
    )
    postroute = next(
        row for row in FINAL_GATES if row["gate"] == "post_route_timing_and_drc"
    )
    assert physical["status"] == "PASS"
    assert postroute["status"] == "PASS"
    assert postroute["substatus"]["target_250mhz_timing"] == "FAIL"


def test_all_pass_is_the_only_ready_state() -> None:
    all_pass = tuple({**row, "status": "PASS"} for row in FINAL_GATES)
    report = evaluate(all_pass)

    assert report["status"] == "PASS"
    assert report["paper_pdf_permitted"] is True


def test_scoped_negative_outcomes_do_not_block_release() -> None:
    release_ready = tuple(
        {
            **row,
            "status": "PASS" if row.get("release_required", True) else row["status"],
        }
        for row in FINAL_GATES
    )
    report = evaluate(release_ready)

    assert report["status"] == "PASS"
    assert report["paper_pdf_permitted"] is True
    assert report["required_nonpassing_gate_count"] == 0
    assert report["nonpassing_gate_count"] >= 1


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

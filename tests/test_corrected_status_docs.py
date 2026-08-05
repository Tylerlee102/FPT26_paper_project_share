import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = (
    "mxfp4_rs2_act_e2m1_e2m0_state_"
    "mxfp4rs2_log_r7_q1_15_int32_guard5"
)


def test_status_ledger_matches_machine_completion_gate() -> None:
    gate = json.loads((ROOT / "reports" / "final_completion_gate.json").read_text())
    counts = Counter(row["status"] for row in gate["gates"])
    status = (ROOT / "docs" / "implementation_status.md").read_text()
    assert counts == {
        "PASS": 8,
        "FAIL": 3,
        "BLOCKED_EXTERNAL": 2,
    }
    assert "All eight release-required gates now pass" in status
    assert gate["required_nonpassing_gate_count"] == 0
    assert gate["paper_pdf_permitted"] is True


def test_current_candidate_and_rtl_scope_are_consistent_across_docs() -> None:
    implementation = (ROOT / "docs" / "implementation_status.md").read_text()
    numerical = (ROOT / "docs" / "numerical_contract.md").read_text()
    protocol = (ROOT / "docs" / "experimental_protocol.md").read_text()
    prior_art = (ROOT / "docs" / "prior_art_matrix.md").read_text()
    for text in (implementation, numerical, protocol):
        assert CANDIDATE in text
    assert "Official Vitis HLS/XSIM completes two exact early-return commands" in implementation
    assert "No recurrent transition is covered" in implementation
    assert "Corrected candidate 64-token RTL parity | FAIL / NOT_ESTABLISHED" in numerical
    assert "Candidate-specific 64-token RTL parity | NOT_ESTABLISHED" in protocol
    assert "docs/synthetic_trace_protocol.json" in protocol
    assert "clipped zero-mean unit-variance" not in protocol
    assert "not claimed as a first or standalone novelty" in prior_art


def test_extended_development_replay_status_is_consistent_across_docs() -> None:
    summary = json.loads(
        (
            ROOT
            / "reports"
            / "benchmark"
            / "corrected"
            / "e2m0_encoded"
            / "extended_development"
            / "extended_summary.json"
        ).read_text(encoding="utf-8")
    )
    gate = json.loads((ROOT / "reports" / "final_completion_gate.json").read_text())
    pareto = next(
        row for row in gate["gates"] if row["gate"] == "selected_method_pareto_advantage"
    )
    assert summary["status"] == "PASS"
    assert summary["full_deterministic_recompute"] == "PASS"
    assert summary["recomputed_run_count"] == summary["run_count"] == 2
    assert pareto["substatus"]["extended_8192_quality"] == "PASS"
    for relative in (
        "docs/implementation_status.md",
        "docs/numerical_contract.md",
        "docs/experimental_protocol.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "8,192-token development" in text
        assert "0.099057" in text

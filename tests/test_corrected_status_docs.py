import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = (
    "mxfp4_rs2_act_rs2_state_"
    "mxfp4rs2_log_r3_q1_15_int32_guard5"
)


def test_status_ledger_matches_machine_completion_gate() -> None:
    gate = json.loads((ROOT / "reports" / "final_completion_gate.json").read_text())
    counts = Counter(row["status"] for row in gate["gates"])
    status = (ROOT / "docs" / "final_completion_gate.md").read_text()
    assert sum(counts.values()) == gate["gate_count"] == 11
    assert all(row["release_required"] is True for row in gate["gates"])
    assert "All eleven rows are release-required" in status
    assert gate["required_nonpassing_gate_count"] == sum(
        value for key, value in counts.items() if key != "PASS"
    )
    assert gate["paper_pdf_permitted"] is (
        gate["required_nonpassing_gate_count"] == 0
    )
    assert gate["release_state"] in status


def test_current_candidate_and_rtl_scope_are_consistent_across_docs() -> None:
    implementation = (ROOT / "docs" / "implementation_status.md").read_text()
    numerical = (ROOT / "docs" / "numerical_contract.md").read_text()
    protocol = (ROOT / "docs" / "experimental_protocol.md").read_text()
    prior_art = (ROOT / "docs" / "prior_art_matrix.md").read_text()
    for text in (implementation, numerical, protocol):
        assert CANDIDATE in text
    assert "first R3 fold boundary" in implementation
    assert "Uniform-MXFP4 RTL evidence is not transferred" in numerical
    assert "Uniform-MXFP4 RTL evidence is not transferred" in protocol
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
            / "rs2_encoded"
            / "rs2_encoded_candidate_summary.json"
        ).read_text(encoding="utf-8")
    )
    extended = summary["gate_results"]["extended_development"]
    assert extended["status"] in {"PARTIAL", "PASS"}
    if extended["status"] == "PASS":
        assert extended["run_count"] == 2
    for relative in (
        "docs/implementation_status.md",
        "docs/numerical_contract.md",
        "docs/experimental_protocol.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "8,192-token" in text

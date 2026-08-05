from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

import pytest

import scripts.paper_pack as paper_pack
from scripts.paper_pack import (
    FINAL_GATE,
    READY_RELEASE_STATE,
    require_audit_build_gate,
    require_release_gate,
)
from scripts.validate_paper_pack import validate_pack


ROOT = Path(__file__).resolve().parents[1]


def _write_gate(path: Path, statuses: list[str]) -> None:
    nonpassing = sum(status != "PASS" for status in statuses)
    ready = nonpassing == 0
    revision = subprocess.check_output(
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
    path.write_text(
        json.dumps(
            {
                "status": "PASS" if ready else "FAIL",
                "release_state": READY_RELEASE_STATE if ready else "NOT PAPER READY",
                "paper_pdf_permitted": ready,
                "gate_count": len(statuses),
                "required_gate_count": len(statuses),
                "nonpassing_gate_count": nonpassing,
                "required_nonpassing_gate_count": nonpassing,
                "source_revision": revision,
                "gates": [
                    {"gate": f"gate_{index}", "status": status}
                    for index, status in enumerate(statuses)
                ],
            }
        ),
        encoding="ascii",
    )


def test_release_gate_rejects_nonpassing_report(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    _write_gate(path, ["PASS", "NOT_RUN"])
    with pytest.raises(RuntimeError, match="paper pack blocked"):
        require_release_gate(path)


def test_release_gate_rejects_malformed_report(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    path.write_text("{", encoding="ascii")
    with pytest.raises(RuntimeError, match="invalid completion gate"):
        require_release_gate(path)


def test_release_gate_accepts_only_complete_pass_report(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    _write_gate(path, ["PASS", "PASS"])
    report = require_release_gate(path)
    assert report["paper_pdf_permitted"] is True
    assert report["release_state"] == READY_RELEASE_STATE


def test_release_gate_accepts_scoped_nonrequired_failure(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    _write_gate(path, ["PASS", "FAIL"])
    report = json.loads(path.read_text(encoding="utf-8"))
    report["gates"][1]["release_required"] = False
    report["status"] = "PASS"
    report["release_state"] = READY_RELEASE_STATE
    report["paper_pdf_permitted"] = True
    report["required_gate_count"] = 1
    report["required_nonpassing_gate_count"] = 0
    path.write_text(json.dumps(report), encoding="ascii")

    accepted = require_release_gate(path)
    assert accepted["nonpassing_gate_count"] == 1


def test_release_gate_rejects_stale_source_revision(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    _write_gate(path, ["PASS", "PASS"])
    report = json.loads(path.read_text(encoding="utf-8"))
    report["source_revision"] = "0" * 40
    path.write_text(json.dumps(report), encoding="ascii")
    with pytest.raises(RuntimeError, match="paper pack blocked"):
        require_release_gate(path)


def test_release_metadata_child_accepts_its_exact_source_parent(monkeypatch) -> None:
    source_revision = "1" * 40
    release_revision = "2" * 40
    monkeypatch.setattr(
        paper_pack, "_git_sha", lambda: (release_revision, "")
    )

    def fake_git(args: list[str]) -> str:
        if args == ["rev-parse", "HEAD^"]:
            return source_revision + "\n"
        if args == [
            "diff",
            "--name-only",
            f"{source_revision}..{release_revision}",
        ]:
            return "reports/final_completion_gate.json\n"
        raise AssertionError(f"unexpected git arguments: {args}")

    monkeypatch.setattr(paper_pack, "_git", fake_git)

    current, observed_revision = paper_pack._gate_revision_is_current(
        {"source_revision": source_revision}
    )

    assert current is True
    assert observed_revision == release_revision


def test_release_metadata_child_rejects_source_changes(monkeypatch) -> None:
    source_revision = "1" * 40
    release_revision = "2" * 40
    monkeypatch.setattr(
        paper_pack, "_git_sha", lambda: (release_revision, "")
    )

    def fake_git(args: list[str]) -> str:
        if args == ["rev-parse", "HEAD^"]:
            return source_revision + "\n"
        if args == [
            "diff",
            "--name-only",
            f"{source_revision}..{release_revision}",
        ]:
            return "scripts/paper_pack.py\n"
        raise AssertionError(f"unexpected git arguments: {args}")

    monkeypatch.setattr(paper_pack, "_git", fake_git)

    current, _ = paper_pack._gate_revision_is_current(
        {"source_revision": source_revision}
    )

    assert current is False


def test_audit_gate_accepts_upstream_pass_before_pdf_review(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    statuses = ["PASS"] * 11
    _write_gate(path, statuses)
    report = json.loads(path.read_text(encoding="utf-8"))
    report["status"] = "FAIL"
    report["release_state"] = "NOT PAPER READY"
    report["paper_pdf_permitted"] = False
    report["nonpassing_gate_count"] = 2
    report["required_nonpassing_gate_count"] = 2
    report["gates"][-2] = {
        "gate": "reviewer_traceability",
        "release_required": True,
        "status": "NOT_RUN",
    }
    report["gates"][-1] = {
        "gate": "paper_provenance_and_final_pdf_audit",
        "release_required": True,
        "status": "NOT_RUN",
    }
    for index, row in enumerate(report["gates"][:-2]):
        row["gate"] = f"upstream_{index}"
    path.write_text(json.dumps(report), encoding="ascii")

    accepted = require_audit_build_gate(path)
    assert accepted["paper_pdf_permitted"] is False


def test_audit_gate_rejects_nonpassing_upstream_gate(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    _write_gate(path, ["PASS"] * 11)
    report = json.loads(path.read_text(encoding="utf-8"))
    report["gates"][-2]["gate"] = "reviewer_traceability"
    report["gates"][-1]["gate"] = "paper_provenance_and_final_pdf_audit"
    report["gates"][0]["status"] = "FAIL"
    path.write_text(json.dumps(report), encoding="ascii")

    with pytest.raises(RuntimeError, match="upstream completion gates"):
        require_audit_build_gate(path)


def test_pack_validator_rejects_archived_nonpassing_gate(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    pack = tmp_path / "submission.zip"
    _write_gate(gate, ["PASS", "FAIL"])
    report = json.loads(gate.read_text(encoding="utf-8"))
    with zipfile.ZipFile(pack, "w") as archive:
        archive.write(gate, "reports/final_completion_gate.json")
        archive.writestr("git_sha.txt", report["source_revision"] + "\n")
    checks, _ = validate_pack(pack)
    release_check = next(
        check
        for check in checks
        if check.name == "authoritative final gate permits release"
    )
    assert release_check.passed is False
    assert release_check.detail.startswith("NOT PAPER READY;")


def test_current_release_gate_preserves_scoped_negative_outcomes() -> None:
    report = require_release_gate(FINAL_GATE)
    scoped = [
        row
        for row in report["gates"]
        if not row.get("release_required", True) and row["status"] != "PASS"
    ]

    assert report["release_state"] == READY_RELEASE_STATE
    assert report["required_nonpassing_gate_count"] == 0
    assert scoped


def test_pack_validator_reports_a_missing_explicit_pack(tmp_path: Path) -> None:
    checks, details = validate_pack(tmp_path / "missing.zip")

    assert details == []
    assert len(checks) == 1
    assert checks[0].name == "pack exists"
    assert checks[0].passed is False

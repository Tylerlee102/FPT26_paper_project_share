from __future__ import annotations

import json
from pathlib import Path

import scripts.build_working_draft as working


def test_working_draft_records_nonpassing_gates_without_waiving_them(
    tmp_path: Path, monkeypatch
) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "release_state": "NOT PAPER READY",
                "gates": [
                    {"gate": "software", "status": "PASS"},
                    {"gate": "board", "status": "BLOCKED_EXTERNAL"},
                    {"gate": "pareto", "status": "FAIL"},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(working, "FINAL_GATE", gate)
    monkeypatch.setattr(working, "_verify_assets", lambda: {"source_identity": {}})
    monkeypatch.setattr(working, "describe_source_files", lambda paths: {})
    monkeypatch.setattr(
        working,
        "_working_compiler",
        lambda build_dir: (["fake-compiler"], "fake", 1),
    )

    def fake_run(*args, **kwargs):
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        (build_dir / "working_draft.pdf").write_bytes(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF\n"
        )
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(working.subprocess, "run", fake_run)
    monkeypatch.setattr(working, "PdfReader", lambda path: type("R", (), {"pages": [1]})())
    output = tmp_path / "draft.pdf"
    manifest_path = tmp_path / "manifest.json"
    result = working.build(output, tmp_path / "build", manifest_path)
    assert result["submission_eligible"] is False
    assert result["release_state"] == "NOT PAPER READY"
    assert result["blocking_gates"] == [
        {"gate": "board", "status": "BLOCKED_EXTERNAL"},
        {"gate": "pareto", "status": "FAIL"},
    ]

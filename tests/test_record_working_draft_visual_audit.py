from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import scripts.record_working_draft_visual_audit as audit


def test_record_requires_every_page_and_preserves_blocking_gates(
    tmp_path: Path, monkeypatch
) -> None:
    pdf = tmp_path / "draft.pdf"
    pdf.write_bytes(b"%PDF-working-draft")
    build = tmp_path / "build.json"
    build.write_text(
        json.dumps(
            {
                "status": "PASS",
                "artifact_kind": "watermarked_working_draft",
                "submission_eligible": False,
                "release_state": "NOT PAPER READY",
                "blocking_gates": [{"gate": "board", "status": "BLOCKED_EXTERNAL"}],
                "output": str(pdf),
                "output_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest().upper(),
                "page_count": 1,
            }
        ),
        encoding="utf-8",
    )
    checks = tmp_path / "checklist.json"
    checks.write_text(
        json.dumps(
            {
                "auditor": "test",
                "pages": [
                    {
                        "page": 1,
                        "status": "PASS",
                        "checks": sorted(audit.REQUIRED_CHECKS),
                        "notes": "clean",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    renders = tmp_path / "renders"
    renders.mkdir()
    (renders / "page-01.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", 1200, 1600)
    )
    monkeypatch.setattr(audit, "PdfReader", lambda path: type("R", (), {"pages": [1]})())

    result = audit.record(build, checks, renders, tmp_path / "audit.json")

    assert result["status"] == "PASS"
    assert result["submission_eligible"] is False
    assert result["release_state"] == "NOT PAPER READY"
    assert result["blocking_gates"] == [
        {"gate": "board", "status": "BLOCKED_EXTERNAL"}
    ]
    assert result["pages"][0]["width"] == 1200

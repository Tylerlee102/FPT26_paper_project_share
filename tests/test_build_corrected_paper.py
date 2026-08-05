from __future__ import annotations

from pathlib import Path

import json

from scripts.build_corrected_paper import ROOT, main


def test_corrected_pdf_build_uses_explicit_noncanonical_outputs(
    tmp_path: Path, capsys
) -> None:
    output = tmp_path / "paper.pdf"
    build_dir = tmp_path / "build"
    manifest_path = tmp_path / "manifest.json"

    assert main(
        [
            "--output",
            str(output),
            "--build-dir",
            str(build_dir),
            "--manifest",
            str(manifest_path),
        ]
    ) == 0
    assert '"status": "PASS"' in capsys.readouterr().out
    assert output.read_bytes().startswith(b"%PDF-")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_output = (
        output.relative_to(ROOT).as_posix()
        if output.is_relative_to(ROOT)
        else str(output.resolve())
    )
    assert manifest["output"] == expected_output
    assert manifest["submission_eligible"] is False

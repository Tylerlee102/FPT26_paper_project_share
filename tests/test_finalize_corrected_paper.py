import hashlib
import json
from pathlib import Path

from scripts.finalize_corrected_paper import AUDIT_PDF, ROOT, main


def test_finalization_uses_explicit_noncanonical_outputs(
    tmp_path: Path, capsys
) -> None:
    output = tmp_path / "paper.pdf"
    manifest_path = tmp_path / "finalization.json"

    assert main(
        ["--output", str(output), "--manifest", str(manifest_path)]
    ) == 0
    assert '"status": "PASS"' in capsys.readouterr().out
    assert output.read_bytes() == AUDIT_PDF.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_output = (
        output.relative_to(ROOT).as_posix()
        if output.is_relative_to(ROOT)
        else str(output.resolve())
    )
    assert manifest["output"] == expected_output
    assert manifest["output_sha256"] == hashlib.sha256(
        output.read_bytes()
    ).hexdigest().upper()
    assert manifest["submission_eligible"] is True

from __future__ import annotations

from pathlib import Path

from scripts.build_corrected_paper import main


def test_corrected_pdf_build_is_blocked_until_upstream_gates_pass(
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
    ) == 1
    assert "blocked by upstream completion gates" in capsys.readouterr().out
    assert not output.exists()
    assert not manifest_path.exists()

from pathlib import Path

from scripts.finalize_corrected_paper import main


def test_finalization_is_blocked_until_every_release_gate_passes(
    tmp_path: Path, capsys
) -> None:
    output = tmp_path / "paper.pdf"
    manifest_path = tmp_path / "finalization.json"

    assert main(
        ["--output", str(output), "--manifest", str(manifest_path)]
    ) == 1
    assert "paper pack blocked by final completion gate" in capsys.readouterr().out
    assert not output.exists()
    assert not manifest_path.exists()

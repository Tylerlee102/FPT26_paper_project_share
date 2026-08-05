from __future__ import annotations

from pathlib import Path


MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"


def test_clean_target_preserves_corrected_evidence() -> None:
    clean = MAKEFILE.read_text(encoding="utf-8").split("clean:", 1)[1]
    assert "reports/cosim" not in clean
    assert "reports/csynth" not in clean
    assert "reports/test_tmp" in clean


def test_ci_uses_tests_and_authoritative_completion_gate() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    ci = text.split("ci:", 1)[1].split("clean:", 1)[0]
    assert "-m pytest" in ci
    assert "-m scripts.final_completion_gate" in ci
    assert "phase5" not in ci
    assert "phase6" not in ci

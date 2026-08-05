from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_fpt_source_is_anonymous_ieee_us_letter_candidate() -> None:
    paper = (ROOT / "paper" / "corrected" / "paper.tex").read_text(
        encoding="utf-8"
    )
    venue = (ROOT / "docs" / "venue_requirements_2026_08_02.md").read_text(
        encoding="utf-8"
    )

    assert r"\documentclass[conference]{IEEEtran}" in paper
    assert r"\author{\IEEEauthorblockN{Anonymous Authors}}" in paper
    assert r"\section*{Acknowledg" not in paper
    assert "a4paper" not in paper.lower()
    assert "Up to 8 content pages" in venue
    assert "unlimited reference pages" in venue
    assert "Final PDF media boxes remain `NOT_RUN`" in venue

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pypdf import PdfReader

from scripts.rs2_paper_figures import CHECKPOINTS, SERIES, generate


def _row(value: float) -> dict[str, object]:
    return {
        "value": value,
        "units": "test",
        "source": "test",
        "source_line": 1,
        "extractor": "test",
        "git_sha": "0" * 40,
        "timestamp": "2026-01-01T00:00:00+00:00",
    }


def test_rs2_paper_figures_use_canonical_numbers(tmp_path: Path) -> None:
    numbers: dict[str, dict[str, object]] = {}
    for series_index, (slug, _, _, _) in enumerate(SERIES):
        for token_index, token in enumerate(CHECKPOINTS):
            cosine = max(0.12, 1.0 - 0.025 * series_index - 0.005 * token_index)
            state = 1e-4 * (series_index + 1) * (token_index + 1)
            numbers[f"rs2_{slug}_token_{token}_output_cosine"] = _row(cosine)
            numbers[f"rs2_{slug}_token_{token}_state_relative_l2"] = _row(state)
    for slug, state_bytes, cosine, cycles in (
        ("bf16", 1048576, 0.9998, 4225856),
        ("mxfp8", 540672, 0.95, 6287680),
        ("candidate", 576912, 0.996, 43065280),
    ):
        numbers[f"rs2_tradeoff_{slug}_state_bytes"] = _row(state_bytes)
        numbers[f"rs2_tradeoff_{slug}_output_cosine"] = _row(cosine)
        numbers[f"rs2_tradeoff_{slug}_hls_cycles"] = _row(cycles)
    numbers["rs2_quality_minimum_cosine_gate"] = _row(0.90)
    numbers["rs2_quality_maximum_state_relative_l2_gate"] = _row(0.001)

    numbers_path = tmp_path / "numbers.json"
    output = tmp_path / "figures"
    manifest_path = output / "manifest.json"
    numbers_path.write_text(
        json.dumps(numbers, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = generate(numbers_path, output, manifest_path)

    assert manifest["status"] == "PASS"
    assert manifest["numbers"]["sha256"] == hashlib.sha256(
        numbers_path.read_bytes()
    ).hexdigest().upper()
    assert len(manifest["outputs"]) == 3
    assert manifest["threshold_keys"] == [
        "rs2_quality_minimum_cosine_gate",
        "rs2_quality_maximum_state_relative_l2_gate",
    ]
    for path in output.glob("*.pdf"):
        assert path.read_bytes().startswith(b"%PDF-")
        assert path.stat().st_size > 1000

    cosine_page = PdfReader(output / "rs2_output_cosine_vs_token.pdf").pages[0]
    state_page = PdfReader(output / "rs2_state_relative_l2_vs_token.pdf").pages[0]
    tradeoff_page = PdfReader(output / "rs2_memory_performance_accuracy.pdf").pages[0]
    for page in (cosine_page, state_page):
        assert float(page.mediabox.width) == pytest.approx(3.45 * 72.0)
        assert float(page.mediabox.height) == pytest.approx(2.85 * 72.0)
    assert float(tradeoff_page.mediabox.width) == pytest.approx(7.16 * 72.0)
    assert float(tradeoff_page.mediabox.height) == pytest.approx(3.55 * 72.0)

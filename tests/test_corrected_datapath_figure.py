from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

from scripts.corrected_datapath_figure import generate


ROOT = Path(__file__).resolve().parents[1]
NUMBERS = ROOT / "paper" / "corrected" / "numbers.json"


def test_corrected_datapath_figure_is_pdf_and_value_bound(tmp_path: Path) -> None:
    output = tmp_path / "datapath.pdf"
    manifest_path = tmp_path / "manifest.json"
    manifest = generate(NUMBERS, output, manifest_path)
    numbers = json.loads(NUMBERS.read_text(encoding="utf-8"))

    assert manifest["status"] == "PASS"
    assert output.read_bytes().startswith(b"%PDF-")
    assert output.stat().st_size > 2_500
    reader = PdfReader(output)
    assert len(reader.pages) == 1
    extracted = reader.pages[0].extract_text()
    for phrase in (
        "One-token recurrence-core STEP",
        "Persistent base state",
        "Recent-write log",
        "atomic fold after output",
        "logical STEP in: 8,832 B",
        "logical out: 24,576 B",
    ):
        assert phrase in extracted
    assert manifest_path.is_file()
    output_key = (
        output.relative_to(ROOT).as_posix()
        if output.is_relative_to(ROOT)
        else str(output)
    )
    assert manifest["outputs"][output_key] == hashlib.sha256(
        output.read_bytes()
    ).hexdigest().upper()
    for key, value in manifest["used_number_values"].items():
        assert numbers[key]["value"] == value
    assert len(manifest["source_identity"]["dirty_patch"]["sha256"]) == 64

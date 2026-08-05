from __future__ import annotations

import hashlib
from pathlib import Path

from pypdf import PdfReader

from scripts.corrected_long_trace_panel import generate


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = (
    ROOT / "paper" / "figures" / "corrected" / "long_trace_plot_manifest.json"
)


def test_corrected_long_trace_panel_is_verified_and_legible(tmp_path: Path) -> None:
    output = tmp_path / "long_panel.pdf"
    manifest_path = tmp_path / "long_panel_manifest.json"
    manifest = generate(UPSTREAM, output, manifest_path)

    assert manifest["status"] == "PASS"
    assert output.read_bytes().startswith(b"%PDF-")
    assert output.stat().st_size > 100_000
    reader = PdfReader(output)
    assert len(reader.pages) == 1
    extracted = reader.pages[0].extract_text()
    for phrase in (
        "Long-horizon synthetic recurrence drift",
        "Output cosine versus FP32",
        "Recurrent-state relative L2",
        "MXFP4 Q/DQ + MXFP8 state",
        "gate 0.99",
        "gate 0.10",
    ):
        assert phrase in extracted
    output_key = output.relative_to(ROOT).as_posix()
    assert manifest["outputs"][output_key] == hashlib.sha256(
        output.read_bytes()
    ).hexdigest().upper()
    assert len(manifest["source_identity"]["dirty_patch"]["sha256"]) == 64

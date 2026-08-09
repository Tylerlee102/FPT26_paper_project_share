from __future__ import annotations

import hashlib
from pathlib import Path

from pypdf import PdfReader

from scripts.tradeoff_evidence_figure import (
    DEFAULT_CAPACITY,
    DEFAULT_HLS,
    DEFAULT_LONG_CHECKPOINTS,
    DEFAULT_LONG_MANIFEST,
    DEFAULT_NATIVE_CHECKPOINTS,
    DEFAULT_NATIVE_MANIFEST,
    generate,
)


ROOT = Path(__file__).resolve().parents[1]


def test_tradeoff_figure_preserves_evidence_levels_and_missing_points(
    tmp_path: Path,
) -> None:
    output = tmp_path / "tradeoff.pdf"
    manifest_path = tmp_path / "tradeoff_manifest.json"
    manifest = generate(
        DEFAULT_CAPACITY,
        DEFAULT_LONG_CHECKPOINTS,
        DEFAULT_LONG_MANIFEST,
        DEFAULT_NATIVE_CHECKPOINTS,
        DEFAULT_NATIVE_MANIFEST,
        DEFAULT_HLS,
        output,
        manifest_path,
    )

    assert manifest["status"] == "PASS"
    assert output.read_bytes().startswith(b"%PDF-")
    assert output.stat().st_size > 3_000
    assert len(PdfReader(output).pages) == 1
    extracted = PdfReader(output).pages[0].extract_text()
    for phrase in (
        "Logical state, 36 cores",
        "Token-8,192 output cosine",
        "HLS max STEP",
        "Native MXFP4",
        "matched HLS not run",
        "Raw capacity is necessary",
        "phys PASS",
    ):
        assert phrase in extracted
    output_key = (
        output.relative_to(ROOT).as_posix()
        if output.is_relative_to(ROOT)
        else str(output)
    )
    assert manifest["outputs"][output_key] == hashlib.sha256(
        output.read_bytes()
    ).hexdigest().upper()
    assert manifest["used_values"]["storage_mib"]["BF16"] == 36.0
    assert manifest["used_values"]["storage_mib"]["MXFP4"] == 9.5625
    assert manifest["used_values"]["token_8192_output_cosine"]["Native MXFP4"] < 0.5
    assert set(manifest["used_values"]["hls_step_max_mcycles"]) == {
        "BF16",
        "Native MXFP4",
        "Native MXFP8",
    }
    assert "matched MXFP8 HLS baseline" not in manifest["not_run"]
    assert "Native MXFP8" in manifest["used_values"]["hls_step_max_mcycles"]
    assert len(manifest["source_identity"]["dirty_patch"]["sha256"]) == 64

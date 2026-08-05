import hashlib
import json
import struct
from pathlib import Path

from pypdf import PdfWriter

from scripts.record_paper_visual_audit import REQUIRED_CHECKS, record


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_visual_audit_requires_and_records_every_page(tmp_path: Path) -> None:
    pdf = tmp_path / "audit.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    with pdf.open("wb") as handle:
        writer.write(handle)
    build = tmp_path / "build.json"
    build.write_text(
        json.dumps(
            {
                "status": "PASS",
                "build_status": "PASS",
                "artifact_kind": "internal_audit_candidate",
                "submission_eligible": False,
                "output": str(pdf),
                "output_sha256": _sha256(pdf),
                "page_count": 2,
            }
        ),
        encoding="utf-8",
    )
    render_dir = tmp_path / "renders"
    render_dir.mkdir()
    png_header = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct.pack(">II", 1600, 2200)
    )
    for page in (1, 2):
        (render_dir / f"page-{page:02d}.png").write_bytes(png_header)
    checklist = tmp_path / "checklist.json"
    checklist.write_text(
        json.dumps(
            {
                "auditor": "test auditor",
                "pages": [
                    {
                        "page": page,
                        "status": "PASS",
                        "checks": sorted(REQUIRED_CHECKS),
                        "notes": "checked",
                    }
                    for page in (1, 2)
                ],
            }
        ),
        encoding="utf-8",
    )

    output = tmp_path / "visual.json"
    report = record(build, checklist, render_dir, output)

    assert report["status"] == "PASS"
    assert report["page_count"] == 2
    assert len(report["pages"]) == 2
    assert all(len(row["sha256"]) == 64 for row in report["pages"])

"""Validate and record a page-by-page audit of the corrected audit PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD_MANIFEST = (
    ROOT / "paper" / "corrected" / "paper_audit_build_manifest.json"
)
DEFAULT_CHECKLIST = ROOT / "paper" / "corrected" / "paper_visual_checklist.json"
DEFAULT_RENDER_DIR = ROOT / "reports" / "rendered" / "corrected_paper"
DEFAULT_OUTPUT = ROOT / "paper" / "corrected" / "paper_visual_audit.json"
REQUIRED_CHECKS = {
    "text_and_equations",
    "figures_and_legends",
    "tables",
    "captions_and_references",
    "margins_and_clipping",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"visual audit blocked: invalid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"visual audit blocked: {path} is not a JSON object")
    return payload


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"visual audit blocked: invalid PNG render {path}")
    return struct.unpack(">II", header[16:24])


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def record(
    build_manifest_path: Path,
    checklist_path: Path,
    render_dir: Path,
    output: Path,
) -> dict[str, object]:
    build = _load_json(build_manifest_path)
    if (
        build.get("status") != "PASS"
        or build.get("build_status") != "PASS"
        or build.get("artifact_kind") != "internal_audit_candidate"
        or build.get("submission_eligible") is not False
    ):
        raise RuntimeError("visual audit blocked: audit-PDF build is not PASS")
    pdf = ROOT / str(build.get("output", ""))
    if not pdf.is_file() or _sha256(pdf) != str(build.get("output_sha256", "")).upper():
        raise RuntimeError("visual audit blocked: audit PDF is missing or stale")
    page_count = len(PdfReader(pdf).pages)
    if page_count != int(build.get("page_count", -1)) or page_count < 1:
        raise RuntimeError("visual audit blocked: PDF page count is inconsistent")

    checklist = _load_json(checklist_path)
    rows = checklist.get("pages")
    if not isinstance(rows, list):
        raise RuntimeError("visual audit blocked: checklist pages must be a list")
    by_page = {
        int(row["page"]): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("page"), int)
    }
    if set(by_page) != set(range(1, page_count + 1)):
        raise RuntimeError("visual audit blocked: checklist must cover every PDF page once")
    auditor = str(checklist.get("auditor", "")).strip()
    if not auditor:
        raise RuntimeError("visual audit blocked: checklist auditor is missing")

    render_records: list[dict[str, object]] = []
    failures: list[str] = []
    for page in range(1, page_count + 1):
        row = by_page[page]
        checks = set(row.get("checks", [])) if isinstance(row.get("checks"), list) else set()
        if row.get("status") != "PASS":
            failures.append(f"page {page} status={row.get('status', 'missing')}")
        missing_checks = sorted(REQUIRED_CHECKS - checks)
        if missing_checks:
            failures.append(f"page {page} missing checks: {','.join(missing_checks)}")
        render = render_dir / f"page-{page:02d}.png"
        if not render.is_file():
            failures.append(f"page {page} render missing")
            continue
        width, height = _png_dimensions(render)
        if width < 1000 or height < 1000:
            failures.append(f"page {page} render is too small: {width}x{height}")
        render_records.append(
            {
                "page": page,
                "path": _display_path(render),
                "sha256": _sha256(render),
                "width": width,
                "height": height,
                "notes": str(row.get("notes", "")),
            }
        )
    if failures:
        raise RuntimeError("visual audit blocked: " + "; ".join(failures))

    result = {
        "schema": 1,
        "status": "PASS",
        "visual_audit_status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "auditor": auditor,
        "audit_candidate": _display_path(pdf),
        "audit_candidate_sha256": _sha256(pdf),
        "build_manifest": _display_path(build_manifest_path),
        "build_manifest_sha256": _sha256(build_manifest_path),
        "checklist": _display_path(checklist_path),
        "checklist_sha256": _sha256(checklist_path),
        "page_count": page_count,
        "required_checks": sorted(REQUIRED_CHECKS),
        "pages": render_records,
        "submission_eligible": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-manifest", type=Path, default=DEFAULT_BUILD_MANIFEST)
    parser.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    parser.add_argument("--render-dir", type=Path, default=DEFAULT_RENDER_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        result = record(
            _resolve(args.build_manifest),
            _resolve(args.checklist),
            _resolve(args.render_dir),
            _resolve(args.output),
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1
    print(json.dumps({"status": result["status"], "page_count": result["page_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

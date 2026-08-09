"""Record a page-by-page visual audit of the watermarked working draft."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from scripts.record_paper_visual_audit import (
    REQUIRED_CHECKS,
    _display_path,
    _load_json,
    _png_dimensions,
    _sha256,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD_MANIFEST = (
    ROOT / "paper" / "corrected" / "working_draft_build_manifest.json"
)
DEFAULT_CHECKLIST = (
    ROOT / "paper" / "corrected" / "working_draft_visual_checklist.json"
)
DEFAULT_RENDER_DIR = ROOT / "reports" / "rendered" / "working_draft"
DEFAULT_OUTPUT = ROOT / "paper" / "corrected" / "working_draft_visual_audit.json"


def record(
    build_manifest_path: Path,
    checklist_path: Path,
    render_dir: Path,
    output: Path,
) -> dict[str, object]:
    build = _load_json(build_manifest_path)
    if (
        build.get("status") != "PASS"
        or build.get("artifact_kind") != "watermarked_working_draft"
        or build.get("submission_eligible") is not False
    ):
        raise RuntimeError("working-draft audit blocked: build manifest is not PASS")
    pdf = ROOT / str(build.get("output", ""))
    if not pdf.is_file() or _sha256(pdf) != str(build.get("output_sha256", "")).upper():
        raise RuntimeError("working-draft audit blocked: PDF is missing or stale")
    page_count = len(PdfReader(pdf).pages)
    if page_count != int(build.get("page_count", -1)) or page_count < 1:
        raise RuntimeError("working-draft audit blocked: page count is inconsistent")

    checklist = _load_json(checklist_path)
    rows = checklist.get("pages")
    if not isinstance(rows, list):
        raise RuntimeError("working-draft audit blocked: checklist pages must be a list")
    by_page = {
        int(row["page"]): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("page"), int)
    }
    if set(by_page) != set(range(1, page_count + 1)):
        raise RuntimeError("working-draft audit blocked: checklist must cover every page once")
    auditor = str(checklist.get("auditor", "")).strip()
    if not auditor:
        raise RuntimeError("working-draft audit blocked: checklist auditor is missing")

    pages: list[dict[str, object]] = []
    failures: list[str] = []
    for page_number in range(1, page_count + 1):
        row = by_page[page_number]
        checks = set(row.get("checks", [])) if isinstance(row.get("checks"), list) else set()
        if row.get("status") != "PASS":
            failures.append(f"page {page_number} status={row.get('status', 'missing')}")
        missing = sorted(REQUIRED_CHECKS - checks)
        if missing:
            failures.append(f"page {page_number} missing checks: {','.join(missing)}")
        render = render_dir / f"page-{page_number:02d}.png"
        if not render.is_file():
            failures.append(f"page {page_number} render missing")
            continue
        width, height = _png_dimensions(render)
        if width < 1000 or height < 1000:
            failures.append(f"page {page_number} render is too small: {width}x{height}")
        pages.append(
            {
                "page": page_number,
                "path": _display_path(render),
                "sha256": _sha256(render),
                "width": width,
                "height": height,
                "notes": str(row.get("notes", "")),
            }
        )
    if failures:
        raise RuntimeError("working-draft audit blocked: " + "; ".join(failures))

    result: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "visual_audit_status": "PASS",
        "artifact_kind": "watermarked_working_draft",
        "submission_eligible": False,
        "release_state": build.get("release_state"),
        "blocking_gates": build.get("blocking_gates", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "auditor": auditor,
        "working_draft": _display_path(pdf),
        "working_draft_sha256": _sha256(pdf),
        "build_manifest": _display_path(build_manifest_path),
        "build_manifest_sha256": _sha256(build_manifest_path),
        "checklist": _display_path(checklist_path),
        "checklist_sha256": _sha256(checklist_path),
        "page_count": page_count,
        "required_checks": sorted(REQUIRED_CHECKS),
        "pages": pages,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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

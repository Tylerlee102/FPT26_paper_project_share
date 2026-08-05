"""Finalize exact audited PDF bytes only after every completion gate passes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from scripts.paper_pack import (
    AUDIT_BUILD_MANIFEST,
    AUDIT_PDF,
    CORRECTED_ASSET_MANIFEST,
    FINAL_GATE,
    FINALIZATION_MANIFEST,
    FINAL_PDF,
    VISUAL_AUDIT_MANIFEST,
    require_release_gate,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _manifest_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"paper finalization blocked: invalid {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"paper finalization blocked: {path} is not an object")
    return value


def finalize(
    audit_pdf: Path,
    build_manifest_path: Path,
    visual_audit_path: Path,
    output: Path,
    manifest_path: Path,
) -> dict[str, object]:
    release = require_release_gate(FINAL_GATE)
    build = _load(build_manifest_path)
    visual = _load(visual_audit_path)
    if (
        build.get("status") != "PASS"
        or build.get("build_status") != "PASS"
        or build.get("artifact_kind") != "internal_audit_candidate"
        or build.get("submission_eligible") is not False
    ):
        raise RuntimeError("paper finalization blocked: audit build is not valid")
    if not audit_pdf.is_file() or _sha256(audit_pdf) != str(
        build.get("output_sha256", "")
    ).upper():
        raise RuntimeError("paper finalization blocked: audit PDF is missing or stale")
    if (
        visual.get("status") != "PASS"
        or visual.get("visual_audit_status") != "PASS"
        or visual.get("submission_eligible") is not False
        or str(visual.get("audit_candidate_sha256", "")).upper() != _sha256(audit_pdf)
        or str(visual.get("build_manifest_sha256", "")).upper()
        != _sha256(build_manifest_path)
    ):
        raise RuntimeError("paper finalization blocked: visual audit is missing or stale")
    if _sha256(CORRECTED_ASSET_MANIFEST) != str(
        build.get("asset_manifest_sha256", "")
    ).upper():
        raise RuntimeError("paper finalization blocked: corrected assets changed after build")
    pages = len(PdfReader(audit_pdf).pages)
    if pages != int(visual.get("page_count", -1)) or pages < 1:
        raise RuntimeError("paper finalization blocked: audited page count is inconsistent")

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(audit_pdf, output)
    if _sha256(output) != _sha256(audit_pdf):
        output.unlink(missing_ok=True)
        raise RuntimeError("paper finalization blocked: exact-byte copy verification failed")
    manifest = {
        "schema": 1,
        "status": "PASS",
        "release_state": release["release_state"],
        "submission_eligible": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": release["source_revision"],
        "release_gate": FINAL_GATE.relative_to(ROOT).as_posix(),
        "release_gate_sha256": _sha256(FINAL_GATE),
        "audit_candidate": _manifest_path(audit_pdf),
        "audit_candidate_sha256": _sha256(audit_pdf),
        "visual_audit": _manifest_path(visual_audit_path),
        "visual_audit_sha256": _sha256(visual_audit_path),
        "output": _manifest_path(output),
        "output_sha256": _sha256(output),
        "page_count": pages,
        "copy_identity": "PASS",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-pdf", type=Path, default=AUDIT_PDF)
    parser.add_argument("--build-manifest", type=Path, default=AUDIT_BUILD_MANIFEST)
    parser.add_argument("--visual-audit", type=Path, default=VISUAL_AUDIT_MANIFEST)
    parser.add_argument("--output", type=Path, default=FINAL_PDF)
    parser.add_argument("--manifest", type=Path, default=FINALIZATION_MANIFEST)
    args = parser.parse_args(argv)
    try:
        result = finalize(
            _resolve(args.audit_pdf),
            _resolve(args.build_manifest),
            _resolve(args.visual_audit),
            _resolve(args.output),
            _resolve(args.manifest),
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1
    print(json.dumps({"status": result["status"], "output": result["output"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

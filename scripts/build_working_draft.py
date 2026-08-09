"""Build a visibly marked manuscript without weakening the release gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from scripts.build_corrected_paper import _compiler, _verify_assets
from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "paper" / "corrected" / "working_draft.tex"
PAPER = ROOT / "paper" / "corrected" / "paper.tex"
FINAL_GATE = ROOT / "reports" / "final_completion_gate.json"
DEFAULT_OUTPUT = ROOT / "paper" / "corrected" / "mxfp4_gdn_working_draft.pdf"
DEFAULT_BUILD_DIR = ROOT / "paper" / "corrected" / "build_working_draft"
DEFAULT_MANIFEST = ROOT / "paper" / "corrected" / "working_draft_build_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _working_compiler(build_dir: Path) -> tuple[list[str], str, int]:
    command, version, passes = _compiler(build_dir)
    paper_arg = str(PAPER)
    wrapper_arg = str(WRAPPER)
    command = [wrapper_arg if arg == paper_arg else arg for arg in command]
    return command, version, passes


def build(output: Path, build_dir: Path, manifest_path: Path) -> dict[str, object]:
    assets = _verify_assets()
    gate = json.loads(FINAL_GATE.read_text(encoding="utf-8"))
    blocking = [
        {"gate": row["gate"], "status": row["status"]}
        for row in gate["gates"]
        if row["status"] != "PASS"
    ]
    build_dir.mkdir(parents=True, exist_ok=True)
    command, tool_version, passes = _working_compiler(build_dir)
    logs: list[str] = []
    for _ in range(passes):
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        logs.extend((result.stdout, result.stderr))
        if result.returncode != 0:
            raise RuntimeError(
                f"working-draft compilation failed with exit code {result.returncode}"
            )
    log_path = build_dir / "working_draft_build.log"
    log_path.write_text("\n".join(logs), encoding="utf-8")
    built_pdf = build_dir / "working_draft.pdf"
    if not built_pdf.is_file() or not built_pdf.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("working-draft compiler did not produce working_draft.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_pdf, output)
    page_count = len(PdfReader(output).pages)
    if page_count == 0:
        raise RuntimeError("working-draft PDF has no pages")

    manifest = {
        "schema": 1,
        "status": "PASS",
        "artifact_kind": "watermarked_working_draft",
        "submission_eligible": False,
        "release_state": gate["release_state"],
        "blocking_gates": blocking,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_manifest_sha256": _sha256(
            ROOT / "paper" / "corrected" / "asset_manifest.json"
        ),
        "asset_source_identity": assets["source_identity"],
        "build_source_identity": describe_source_files(
            [Path(__file__).resolve(), PAPER, WRAPPER]
        ),
        "command": command,
        "tool_version": tool_version,
        "build_log": _relative(log_path),
        "build_log_sha256": _sha256(log_path),
        "output": _relative(output),
        "output_sha256": _sha256(output),
        "page_count": page_count,
        "visual_audit_status": "NOT_RUN",
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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    try:
        result = build(
            _resolve(args.output),
            _resolve(args.build_dir),
            _resolve(args.manifest),
        )
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1
    print(json.dumps({"status": result["status"], "output": result["output"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

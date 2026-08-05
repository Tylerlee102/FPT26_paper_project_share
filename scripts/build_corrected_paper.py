"""Build a non-submission audit PDF after all upstream evidence gates pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from scripts.evidence_source_snapshot import describe_source_files
from scripts.paper_pack import FINAL_GATE, require_audit_build_gate


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "corrected" / "paper.tex"
ASSET_MANIFEST = ROOT / "paper" / "corrected" / "asset_manifest.json"
DEFAULT_OUTPUT = ROOT / "paper" / "corrected" / "paper_audit_candidate.pdf"
DEFAULT_BUILD_DIR = ROOT / "paper" / "corrected" / "build"
DEFAULT_MANIFEST = (
    ROOT / "paper" / "corrected" / "paper_audit_build_manifest.json"
)
LOCAL_TECTONIC = ROOT / ".tools" / "tectonic" / "tectonic.exe"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _manifest_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _verify_assets() -> dict[str, object]:
    manifest = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS":
        raise RuntimeError(
            "corrected paper build blocked: corrected source assets are not PASS"
        )
    for relative, expected in manifest.get("inputs_sha256", {}).items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != str(expected).upper():
            raise RuntimeError(f"corrected paper build blocked: stale asset input {relative}")
    for relative, expected in manifest.get("outputs_sha256", {}).items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != str(expected).upper():
            raise RuntimeError(f"corrected paper build blocked: stale asset output {relative}")
    return manifest


def _compiler(build_dir: Path) -> tuple[list[str], str, int]:
    latexmk = shutil.which("latexmk")
    if latexmk:
        version = subprocess.run(
            [latexmk, "-v"], capture_output=True, text=True, check=False
        ).stdout.splitlines()[0]
        return (
            [
                latexmk,
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-file-line-error",
                f"-outdir={build_dir}",
                str(PAPER),
            ],
            version,
            1,
        )
    pdflatex = shutil.which("pdflatex")
    if pdflatex:
        version_result = subprocess.run(
            [pdflatex, "--version"], capture_output=True, text=True, check=False
        )
        version = version_result.stdout.splitlines()[0]
        return (
            [
                pdflatex,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-file-line-error",
                f"-output-directory={build_dir}",
                str(PAPER),
            ],
            version,
            2,
        )
    tectonic = shutil.which("tectonic")
    if not tectonic and LOCAL_TECTONIC.is_file():
        tectonic = str(LOCAL_TECTONIC)
    if tectonic:
        version_result = subprocess.run(
            [tectonic, "--version"], capture_output=True, text=True, check=False
        )
        version = version_result.stdout.splitlines()[0]
        return (
            [
                tectonic,
                "--color",
                "never",
                "-Z",
                f"search-path={ROOT}",
                "--keep-logs",
                "--outdir",
                str(build_dir),
                str(PAPER),
            ],
            version,
            1,
        )
    raise RuntimeError(
        "corrected paper build blocked: latexmk, pdflatex, and tectonic are unavailable"
    )


def build(output: Path, build_dir: Path, manifest_path: Path) -> dict[str, object]:
    upstream_gate = require_audit_build_gate(FINAL_GATE)
    assets = _verify_assets()
    build_dir.mkdir(parents=True, exist_ok=True)
    command, tool_version, passes = _compiler(build_dir)
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
                f"corrected paper compilation failed with exit code {result.returncode}"
            )
    log_path = build_dir / "paper_build.log"
    log_path.write_text("\n".join(logs), encoding="utf-8")
    built_pdf = build_dir / "paper.pdf"
    if not built_pdf.is_file() or not built_pdf.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("corrected paper compiler did not produce paper.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_pdf, output)
    reader = PdfReader(output)
    if not reader.pages:
        raise RuntimeError("corrected paper PDF has no pages")

    source_identity = describe_source_files(
        [Path(__file__), PAPER, ROOT / "scripts" / "corrected_paper_assets.py"]
    )
    manifest = {
        "schema": 1,
        "status": "PASS",
        "build_status": "PASS",
        "artifact_kind": "internal_audit_candidate",
        "submission_eligible": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "upstream_gate_sha256": _sha256(FINAL_GATE),
        "upstream_release_state": upstream_gate["release_state"],
        "asset_manifest_sha256": _sha256(ASSET_MANIFEST),
        "asset_source_identity": assets["source_identity"],
        "build_source_identity": source_identity,
        "command": command,
        "exit_code": 0,
        "tool_version": tool_version,
        "build_log": _manifest_path(log_path),
        "build_log_sha256": _sha256(log_path),
        "output": _manifest_path(output),
        "output_sha256": _sha256(output),
        "page_count": len(reader.pages),
        "visual_audit_status": "NOT_RUN",
        "limitations": [
            "this audit candidate is not the final submission PDF",
            "successful compilation is not a page-by-page visual audit",
            "exact-byte finalization remains blocked until every final gate passes",
        ],
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
    except RuntimeError as exc:
        print(str(exc))
        return 1
    print(json.dumps({"status": result["status"], "output": result["output"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

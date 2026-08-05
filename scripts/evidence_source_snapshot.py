"""Create a deterministic Git patch and hash manifest for corrected source."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATCH = ROOT / "docs" / "evidence" / "current_corrected_source.patch"
DEFAULT_MANIFEST = (
    ROOT / "docs" / "evidence" / "current_corrected_source_snapshot.json"
)
DEFAULT_GLOBS = (
    "AGENTS.md",
    "Makefile",
    "README.md",
    "pyproject.toml",
    "docs/*.md",
    "docs/*.json",
    "golden/*.py",
    "hls/bf16/include/*.hpp",
    "hls/bf16/src/*.cpp",
    "hls/bf16/tb/*.cpp",
    "hls/bf16/tcl/*.tcl",
    "hls/e2m0/include/*.hpp",
    "hls/e2m0/src/*.cpp",
    "hls/e2m0/tb/*.cpp",
    "hls/e2m0/tcl/*.tcl",
    "hls/include/*.hpp",
    "hls/rtl_tb/*.sv",
    "hls/src/*.cpp",
    "hls/tb/*.cpp",
    "hls/tcl/*.tcl",
    "paper/*.md",
    "paper/*.tex",
    "paper/corrected/*.tex",
    "paper/corrected/snippets/*.tex",
    "paper/corrected/tables/*.tex",
    "reports/README.md",
    "reports/known_issues.md",
    "scripts/*.py",
    "tests/*.py",
    "vivado/constraints/*.xdc",
    "vivado/tcl/*.tcl",
)
DEFAULT_EXCLUDES = (
    # The evidence ledger records this snapshot's hash, so including it would
    # create a self-referential manifest that becomes stale when updated.
    "docs/evidence_manifest.md",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git executable not found")
    return executable


def _run_git(arguments: list[str], *, allowed: tuple[int, ...] = (0,)) -> bytes:
    command = [
        _git(),
        "-c",
        f"safe.directory={ROOT.as_posix()}",
        *arguments,
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode not in allowed:
        raise RuntimeError(
            f"git command failed ({result.returncode}): {' '.join(arguments)}\n"
            + result.stderr.decode("utf-8", errors="replace")
        )
    return result.stdout


def _collect_files(
    patterns: list[str], excludes: tuple[str, ...] = DEFAULT_EXCLUDES
) -> list[Path]:
    excluded = set(excludes)
    files = {
        path.resolve()
        for pattern in patterns
        for path in ROOT.glob(pattern)
        if path.is_file() and path.relative_to(ROOT).as_posix() not in excluded
    }
    if not files:
        raise ValueError("source patterns matched no files")
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def _is_tracked(relative_path: str) -> bool:
    command = [
        _git(),
        "-c",
        f"safe.directory={ROOT.as_posix()}",
        "ls-files",
        "--error-unmatch",
        "--",
        relative_path,
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def describe_source_files(paths: list[Path]) -> dict[str, object]:
    """Fingerprint exact source bytes and their patch against the current HEAD."""
    revision = _run_git(["rev-parse", "HEAD"]).decode("ascii").strip()
    patch_parts: list[bytes] = []
    file_manifest: dict[str, dict[str, object]] = {}
    resolved_root = ROOT.resolve()
    for path in sorted(
        {item.resolve() for item in paths},
        key=lambda item: item.relative_to(resolved_root).as_posix(),
    ):
        relative = path.relative_to(resolved_root).as_posix()
        tracked = _is_tracked(relative)
        if tracked:
            patch = _run_git(
                ["diff", "--binary", "--no-ext-diff", "HEAD", "--", relative]
            )
        else:
            patch = _run_git(
                ["diff", "--no-index", "--binary", "--", "/dev/null", relative],
                allowed=(0, 1),
            )
        if patch:
            patch_parts.append(patch if patch.endswith(b"\n") else patch + b"\n")
        file_manifest[relative] = {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
            "git_state": "tracked" if tracked else "untracked",
            "changed_from_revision": bool(patch),
        }
    patch_bytes = b"".join(patch_parts)
    return {
        "git_revision": revision,
        "files": file_manifest,
        "dirty_patch": {
            "sha256": _sha256_bytes(patch_bytes),
            "bytes": len(patch_bytes),
            "changed_file_count": sum(
                bool(item["changed_from_revision"])
                for item in file_manifest.values()
            ),
        },
        "method": (
            "Concatenated git diff --binary output against HEAD for tracked files "
            "and git diff --no-index --binary /dev/null output for untracked files, "
            "ordered by repository-relative path."
        ),
    }


def create_snapshot(
    patterns: list[str],
    patch_path: Path,
    manifest_path: Path,
) -> dict[str, object]:
    files = _collect_files(patterns)
    revision = _run_git(["rev-parse", "HEAD"]).decode("ascii").strip()
    patch_parts: list[bytes] = []
    file_manifest: dict[str, dict[str, object]] = {}
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        tracked = _is_tracked(relative)
        if tracked:
            patch = _run_git(
                ["diff", "--binary", "--no-ext-diff", "HEAD", "--", relative]
            )
        else:
            patch = _run_git(
                ["diff", "--no-index", "--binary", "--", "/dev/null", relative],
                allowed=(0, 1),
            )
        if patch:
            patch_parts.append(patch if patch.endswith(b"\n") else patch + b"\n")
        file_manifest[relative] = {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
            "git_state": "tracked" if tracked else "untracked",
            "changed_from_revision": bool(patch),
        }

    patch_bytes = b"".join(patch_parts)
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_bytes(patch_bytes)
    manifest: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_revision": revision,
        "patterns": patterns,
        "excluded_paths": list(DEFAULT_EXCLUDES),
        "files": file_manifest,
        "dirty_patch": {
            "path": patch_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256_bytes(patch_bytes),
            "bytes": len(patch_bytes),
            "changed_file_count": sum(
                bool(item["changed_from_revision"])
                for item in file_manifest.values()
            ),
        },
        "method": (
            "Concatenated git diff --binary output against HEAD for every matched "
            "tracked file and git diff --no-index --binary /dev/null output for "
            "every matched untracked file, ordered by repository-relative path."
        ),
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
    parser.add_argument("--glob", action="append", dest="patterns")
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    manifest = create_snapshot(
        args.patterns or list(DEFAULT_GLOBS),
        _resolve(args.patch),
        _resolve(args.manifest),
    )
    print(json.dumps(manifest["dirty_patch"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

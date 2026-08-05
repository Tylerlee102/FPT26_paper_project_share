from __future__ import annotations

import hashlib
import shutil

from scripts.evidence_source_snapshot import (
    DEFAULT_EXCLUDES,
    DEFAULT_GLOBS,
    ROOT,
    _collect_files,
    describe_source_files,
)


def test_default_snapshot_includes_current_hls_paper_and_status_sources() -> None:
    assert "AGENTS.md" in DEFAULT_GLOBS
    assert "Makefile" in DEFAULT_GLOBS
    assert "README.md" in DEFAULT_GLOBS
    assert "pyproject.toml" in DEFAULT_GLOBS
    assert "docs/*.json" in DEFAULT_GLOBS
    assert "hls/bf16/include/*.hpp" in DEFAULT_GLOBS
    assert "hls/bf16/src/*.cpp" in DEFAULT_GLOBS
    assert "hls/bf16/tb/*.cpp" in DEFAULT_GLOBS
    assert "hls/bf16/tcl/*.tcl" in DEFAULT_GLOBS
    assert "hls/e2m0/include/*.hpp" in DEFAULT_GLOBS
    assert "hls/e2m0/src/*.cpp" in DEFAULT_GLOBS
    assert "hls/e2m0/tb/*.cpp" in DEFAULT_GLOBS
    assert "hls/e2m0/tcl/*.tcl" in DEFAULT_GLOBS
    assert "paper/*.md" in DEFAULT_GLOBS
    assert "paper/corrected/*.tex" in DEFAULT_GLOBS
    assert "paper/corrected/snippets/*.tex" in DEFAULT_GLOBS
    assert "paper/corrected/tables/*.tex" in DEFAULT_GLOBS
    assert "reports/README.md" in DEFAULT_GLOBS
    assert "reports/known_issues.md" in DEFAULT_GLOBS
    assert "docs/evidence_manifest.md" in DEFAULT_EXCLUDES
    collected = {
        path.relative_to(ROOT).as_posix()
        for path in _collect_files(list(DEFAULT_GLOBS))
    }
    assert "docs/implementation_status.md" in collected
    assert "docs/synthetic_trace_protocol.json" in collected
    assert "hls/e2m0/src/gdn_e2m0_top.cpp" in collected
    assert "paper/corrected/paper.tex" in collected
    assert "paper/corrected/snippets/corrected_result_macros.tex" in collected
    assert "docs/evidence_manifest.md" not in collected


def test_describe_source_files_covers_tracked_and_untracked_bytes() -> None:
    tracked = ROOT / "golden" / "gdn_fp32.py"
    temporary = ROOT / "build" / "test_source_identity" / "untracked.txt"
    shutil.rmtree(temporary.parent, ignore_errors=True)
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text("source identity fixture\n", encoding="ascii")
    try:
        result = describe_source_files([temporary, tracked])
        relative = temporary.relative_to(ROOT).as_posix()
        assert result["git_revision"]
        assert result["files"][relative]["git_state"] == "untracked"
        assert result["files"][relative]["sha256"] == hashlib.sha256(
            temporary.read_bytes()
        ).hexdigest().upper()
        assert result["dirty_patch"]["bytes"] > 0
        assert len(result["dirty_patch"]["sha256"]) == 64
    finally:
        shutil.rmtree(temporary.parent, ignore_errors=True)

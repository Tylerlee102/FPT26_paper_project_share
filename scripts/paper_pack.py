from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "paper" / "pack"
FINAL_GATE = ROOT / "reports" / "final_completion_gate.json"
FALLBACK_SHA = "0" * 40
READY_RELEASE_STATE = "READY FOR HUMAN SUBMISSION REVIEW"
AUDIT_EXEMPT_GATES = frozenset(
    {"reviewer_traceability", "paper_provenance_and_final_pdf_audit"}
)
CORRECTED_PAPER = ROOT / "paper" / "corrected"
CORRECTED_NUMBERS = CORRECTED_PAPER / "numbers.json"
CORRECTED_PROVENANCE = CORRECTED_PAPER / "provenance.json"
CORRECTED_ASSET_MANIFEST = CORRECTED_PAPER / "asset_manifest.json"
AUDIT_PDF = CORRECTED_PAPER / "paper_audit_candidate.pdf"
AUDIT_BUILD_MANIFEST = CORRECTED_PAPER / "paper_audit_build_manifest.json"
VISUAL_AUDIT_MANIFEST = CORRECTED_PAPER / "paper_visual_audit.json"
FINAL_PDF = CORRECTED_PAPER / "paper.pdf"
FINALIZATION_MANIFEST = CORRECTED_PAPER / "paper_finalization_manifest.json"
RELEASE_METADATA_PATHS = frozenset(
    {
        "docs/final_completion_gate.md",
        "paper/corrected/paper_finalization_manifest.json",
        "reports/final_completion_gate.json",
    }
)


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git_sha() -> tuple[str, str]:
    try:
        sha = _git(["rev-parse", "HEAD"]).strip()
        if len(sha) == 40:
            return sha, ""
    except Exception as exc:
        return FALLBACK_SHA, f"No git commit was available: {exc}\n"
    return FALLBACK_SHA, "Git returned an invalid HEAD SHA.\n"


def _git_log(note: str) -> str:
    if note:
        return note
    try:
        return _git(["log", "--oneline", "--decorate", "--max-count=50"])
    except Exception as exc:
        return f"Could not read git log: {exc}\n"


def _git_status() -> str:
    try:
        status = _git(["status", "--short"])
        return status if status else "clean\n"
    except Exception as exc:
        return f"Could not read git status: {exc}\n"


def _git_diff_stat() -> str:
    try:
        diff = _git(["diff", "--stat"])
        return diff if diff else "no unstaged diff\n"
    except Exception as exc:
        return f"Could not read git diff stat: {exc}\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_gate(path: Path) -> dict[str, object]:
    if not path.exists():
        raise RuntimeError(f"completion gate is missing: {path}")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid completion gate: {exc}") from exc
    if not isinstance(report, dict):
        raise RuntimeError("completion gate must be a JSON object")
    gates = report.get("gates")
    if not isinstance(gates, list) or not gates:
        raise RuntimeError("completion gate must contain a non-empty gates list")
    if any(
        not isinstance(row, dict)
        or not isinstance(row.get("gate"), str)
        or not isinstance(row.get("status"), str)
        for row in gates
    ):
        raise RuntimeError("completion gate rows are malformed")
    names = [str(row["gate"]) for row in gates]
    if len(names) != len(set(names)):
        raise RuntimeError("completion gate names are not unique")
    return report


def _gate_revision_is_current(report: dict[str, object]) -> tuple[bool, str]:
    current_revision, _ = _git_sha()
    source_revision = str(report.get("source_revision", ""))
    if source_revision == current_revision:
        return True, current_revision
    if len(source_revision) != 40 or source_revision == FALLBACK_SHA:
        return False, current_revision
    try:
        parent_revision = _git(["rev-parse", "HEAD^"]).strip()
        changed_paths = {
            line.strip()
            for line in _git(
                ["diff", "--name-only", f"{source_revision}..{current_revision}"]
            ).splitlines()
            if line.strip()
        }
    except Exception:
        return False, current_revision
    release_metadata_only = (
        parent_revision == source_revision
        and bool(changed_paths)
        and changed_paths <= RELEASE_METADATA_PATHS
    )
    return release_metadata_only, current_revision


def _archive_bytes(
    archive: zipfile.ZipFile,
    entries: dict[str, dict[str, object]],
    arcname: str,
    value: bytes,
    *,
    source: str,
) -> None:
    if arcname in entries:
        return
    archive.writestr(arcname, value)
    entries[arcname] = {
        "sha256": _sha256_bytes(value),
        "bytes": len(value),
        "source": source,
    }


def _archive_file(
    archive: zipfile.ZipFile,
    entries: dict[str, dict[str, object]],
    path: Path,
    *,
    arcname: str | None = None,
) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    name = arcname or _rel(path)
    _archive_bytes(archive, entries, name, path.read_bytes(), source=_rel(path))


def _archive_glob(
    archive: zipfile.ZipFile,
    entries: dict[str, dict[str, object]],
    pattern: str,
) -> None:
    for path in sorted(ROOT.glob(pattern)):
        if path.is_file():
            _archive_file(archive, entries, path)


def require_release_gate(path: Path = FINAL_GATE) -> dict[str, object]:
    """Reject submission packaging unless every release-required gate passes."""
    try:
        report = _load_gate(path)
    except RuntimeError as exc:
        raise RuntimeError(f"paper pack blocked: {exc}") from exc
    revision_current, current_revision = _gate_revision_is_current(report)
    gates = report.get("gates")
    required = [
        row
        for row in (gates or [])
        if isinstance(row, dict) and row.get("release_required", True)
    ]
    valid_gates = (
        isinstance(gates, list)
        and bool(gates)
        and bool(required)
        and all(
            isinstance(row, dict) and row.get("status") == "PASS"
            for row in required
        )
    )
    ready = (
        report.get("status") == "PASS"
        and report.get("paper_pdf_permitted") is True
        and report.get("release_state") == READY_RELEASE_STATE
        and report.get("required_nonpassing_gate_count") == 0
        and report.get("required_gate_count") == len(required)
        and report.get("gate_count") == len(gates or [])
        and revision_current
        and valid_gates
    )
    if not ready:
        state = report.get("release_state", "unknown")
        count = report.get("required_nonpassing_gate_count", "unknown")
        raise RuntimeError(
            "paper pack blocked by final completion gate: "
            f"release_state={state}, required_nonpassing_gate_count={count}, "
            f"source_revision={report.get('source_revision', 'unknown')}, "
            f"current_revision={current_revision}"
        )
    return report


def require_audit_build_gate(path: Path = FINAL_GATE) -> dict[str, object]:
    """Permit only an internal audit candidate after every upstream gate passes.

    Reviewer traceability and the paper/PDF audit are intentionally excluded:
    they consume the audit candidate. The resulting PDF is never the final
    submission artifact; exact-byte finalization remains behind
    :func:`require_release_gate`.
    """
    try:
        report = _load_gate(path)
    except RuntimeError as exc:
        raise RuntimeError(f"corrected audit PDF blocked: {exc}") from exc
    revision_current, current_revision = _gate_revision_is_current(report)
    gates = report["gates"]
    names = {str(row["gate"]) for row in gates}
    missing_exemptions = sorted(AUDIT_EXEMPT_GATES - names)
    upstream = [
        row
        for row in gates
        if row.get("release_required", True)
        and str(row["gate"]) not in AUDIT_EXEMPT_GATES
    ]
    nonpassing = [
        f"{row['gate']}={row['status']}"
        for row in upstream
        if row["status"] != "PASS"
    ]
    if missing_exemptions or not upstream or nonpassing or not revision_current:
        detail = ", ".join(nonpassing) or "none"
        raise RuntimeError(
            "corrected audit PDF blocked by upstream completion gates: "
            f"nonpassing={detail}; "
            f"missing_exemptions={','.join(missing_exemptions) or 'none'}; "
            f"source_revision={report.get('source_revision', 'unknown')}; "
            f"current_revision={current_revision}"
        )
    return report


def _phase7_status_lines(
    release_commit_sha: str,
    source_revision: str,
    output: Path,
    release: dict[str, object],
) -> list[str]:
    lines = [
        "# Corrected Paper Pack Status",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Release commit SHA: `{release_commit_sha}`",
        f"Evaluated source revision: `{source_revision}`",
        f"Pack path: `{output.relative_to(ROOT).as_posix()}`",
        "",
        f"Release state: **{release['release_state']}**",
        "",
    ]
    numbers = json.loads(CORRECTED_NUMBERS.read_text(encoding="utf-8"))
    lines.extend(
        [
            "## Controlled Answer",
            "",
            (
                "- MXFP4 floating-Q/DQ token-8192 output cosine: "
                f"`{numbers['qdq_mxfp4_token_8192_output_cosine']['value']}`"
            ),
            (
                "- Native encoded MXFP4 token-8192 output cosine: "
                f"`{numbers['native_encoded_mxfp4_token_8192_output_cosine']['value']}`"
            ),
            (
                "- Native encoded MXFP4 token-8192 state relative L2: "
                f"`{numbers['native_encoded_mxfp4_token_8192_state_relative_l2']['value']}`"
            ),
            (
                "- Native encoded MXFP4/BF16 LUT ratio: "
                f"`{numbers['uniform_mxfp4_to_bf16_lut_ratio']['value']}`"
            ),
            (
                "- Corrected-candidate/BF16 LUT ratio: "
                f"`{numbers['corrected_candidate_to_bf16_lut_ratio']['value']}`"
            ),
            "",
            "The final PDF is an exact-byte copy of the page-audited candidate.",
            "No legacy paper numbers or unsupported H100/TDP comparisons are canonical.",
            "",
        ]
    )
    return lines


def build_pack() -> Path:
    release = require_release_gate()
    release_commit_sha, sha_note = _git_sha()
    source_revision = str(release["source_revision"])
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    output = PACK_DIR / f"submission_{release_commit_sha}.zip"
    phase7_status = ROOT / "reports" / "phase7_status.md"
    phase7_status.parent.mkdir(parents=True, exist_ok=True)
    phase7_status.write_text(
        "\n".join(
            _phase7_status_lines(
                release_commit_sha, source_revision, output, release
            )
        ),
        encoding="utf-8",
    )

    required = [
        ROOT / "AGENTS.md",
        FINAL_GATE,
        CORRECTED_NUMBERS,
        CORRECTED_PROVENANCE,
        CORRECTED_ASSET_MANIFEST,
        CORRECTED_PAPER / "paper.tex",
        CORRECTED_PAPER / "snippets" / "corrected_result_macros.tex",
        AUDIT_PDF,
        AUDIT_BUILD_MANIFEST,
        VISUAL_AUDIT_MANIFEST,
        CORRECTED_PAPER / "paper_visual_checklist.json",
        FINAL_PDF,
        FINALIZATION_MANIFEST,
        phase7_status,
        ROOT / "reports" / "known_issues.md",
        ROOT / "docs" / "reviewer_traceability.md",
        ROOT / "docs" / "reviewer_traceability_status.json",
        ROOT / "docs" / "evidence_manifest.md",
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required paper-pack file(s): {', '.join(missing)}")

    numbers = json.loads(CORRECTED_NUMBERS.read_text(encoding="utf-8"))
    provenance = json.loads(CORRECTED_PROVENANCE.read_text(encoding="utf-8"))
    if set(numbers) != set(provenance):
        raise RuntimeError("corrected paper numbers and provenance keys differ")
    evidence_sources: set[Path] = set()
    for key, record in numbers.items():
        if not isinstance(record, dict):
            raise RuntimeError(f"corrected number {key} is not an object")
        source = str(record.get("source", ""))
        if source and source != "external":
            path = ROOT / source
            if not path.is_file():
                raise FileNotFoundError(f"corrected number source is missing: {source}")
            evidence_sources.add(path)

    assets = json.loads(CORRECTED_ASSET_MANIFEST.read_text(encoding="utf-8"))
    asset_paths = {
        ROOT / relative
        for field in ("inputs_sha256", "outputs_sha256", "verified_figure_sha256")
        for relative in assets.get(field, {})
    }

    entries: dict[str, dict[str, object]] = {}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in required:
            _archive_file(archive, entries, path)
        _archive_file(
            archive,
            entries,
            CORRECTED_NUMBERS,
            arcname="paper/numbers.json",
        )
        _archive_file(
            archive,
            entries,
            CORRECTED_PROVENANCE,
            arcname="paper/provenance.json",
        )
        for path in sorted(evidence_sources | asset_paths):
            _archive_file(archive, entries, path)
        for pattern in (
            "paper/corrected/tables/*.tex",
            "paper/corrected/snippets/*.tex",
            "paper/corrected/build/*",
            "paper/figures/corrected/*",
            "docs/*.md",
            "docs/evidence/**/*",
            "reports/benchmark/corrected/**/*",
            "reports/csim/corrected/**/*",
            "reports/csynth/corrected/**/*",
            "reports/cosim/corrected/**/*",
            "reports/vivado/corrected/**/*",
            "reports/environment/**/*",
            "reports/golden/official_parity/**/*",
            "reports/test_results/*.log",
            "reports/rendered/corrected_paper/*.png",
            "data/calibration/*.sha256",
            "golden/*.py",
            "scripts/*.py",
            "tests/*.py",
            "hls/**/*.cpp",
            "hls/**/*.hpp",
            "hls/**/*.sv",
            "hls/**/*.tcl",
        ):
            _archive_glob(archive, entries, pattern)
        for name, value in (
            ("git_sha.txt", source_revision + "\n"),
            ("git_log.txt", _git_log(sha_note)),
            ("git_status.txt", _git_status()),
            ("git_diff_stat.txt", _git_diff_stat()),
        ):
            _archive_bytes(
                archive,
                entries,
                name,
                value.encode("utf-8"),
                source=f"generated:{name}",
            )
        manifest = {
            "schema": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "git_sha": source_revision,
            "release_commit_sha": release_commit_sha,
            "release_gate_sha256": _sha256(FINAL_GATE),
            "final_pdf_sha256": _sha256(FINAL_PDF),
            "canonical_aliases": {
                "paper/numbers.json": _rel(CORRECTED_NUMBERS),
                "paper/provenance.json": _rel(CORRECTED_PROVENANCE),
            },
            "entries": entries,
        }
        _archive_bytes(
            archive,
            entries,
            "pack_manifest.json",
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            source="generated:pack_manifest.json",
        )

    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the paper-pack reproducibility archive.")
    parser.parse_args(argv)
    try:
        output = build_pack()
    except RuntimeError as exc:
        print(str(exc))
        return 1
    print(output.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .paper_pack import require_release_gate


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "paper" / "pack"
REPORT = ROOT / "reports" / "phase7_validation.md"
FALLBACK_SHA = "0" * 40


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        sha = result.stdout.strip()
        return sha if len(sha) == 40 else FALLBACK_SHA
    except Exception:
        return FALLBACK_SHA


def _default_pack() -> Path:
    return PACK_DIR / f"submission_{_git_sha()}.zip"


def _has_any(names: set[str], prefix: str, suffix: str = "") -> bool:
    return any(name.startswith(prefix) and name.endswith(suffix) for name in names)


def _read_json_from_zip(archive: zipfile.ZipFile, name: str) -> dict[str, object]:
    with archive.open(name) as handle:
        return json.loads(handle.read().decode("utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _archive_sha256(archive: zipfile.ZipFile, name: str) -> str:
    return _sha256_bytes(archive.read(name))


def validate_pack(pack: Path) -> tuple[list[Check], list[str]]:
    checks: list[Check] = []
    details: list[str] = []
    if not pack.exists():
        return [Check("pack exists", False, f"{pack} is missing")], details

    with zipfile.ZipFile(pack) as archive:
        names_list = archive.namelist()
        names = set(names_list)
        counts = Counter(names_list)

        duplicates = sorted(name for name, count in counts.items() if count > 1)
        checks.append(Check("no duplicate archive entries", not duplicates, ", ".join(duplicates) or "none"))

        required_exact = {
            "AGENTS.md",
            "paper/numbers.json",
            "paper/provenance.json",
            "paper/corrected/numbers.json",
            "paper/corrected/provenance.json",
            "paper/corrected/asset_manifest.json",
            "paper/corrected/paper.tex",
            "paper/corrected/paper_audit_candidate.pdf",
            "paper/corrected/paper_audit_build_manifest.json",
            "paper/corrected/paper_visual_audit.json",
            "paper/corrected/paper_visual_checklist.json",
            "paper/corrected/paper.pdf",
            "paper/corrected/paper_finalization_manifest.json",
            "paper/corrected/snippets/corrected_result_macros.tex",
            "reports/final_completion_gate.json",
            "reports/phase7_status.md",
            "reports/known_issues.md",
            "docs/reviewer_traceability.md",
            "docs/reviewer_traceability_status.json",
            "docs/evidence_manifest.md",
            "pack_manifest.json",
            "git_sha.txt",
            "git_log.txt",
            "git_status.txt",
            "git_diff_stat.txt",
        }
        missing = sorted(required_exact - names)
        checks.append(Check("required exact files", not missing, ", ".join(missing) or "all present"))

        class_checks = [
            (
                "corrected PDF figures",
                _has_any(names, "paper/figures/corrected/", ".pdf"),
            ),
            (
                "corrected LaTeX tables",
                _has_any(names, "paper/corrected/tables/", ".tex"),
            ),
            (
                "corrected Vivado reports",
                _has_any(names, "reports/vivado/corrected/", ".rpt"),
            ),
            (
                "corrected HLS synthesis reports",
                _has_any(names, "reports/csynth/corrected/", ".rpt")
                or _has_any(names, "reports/csynth/corrected/", ".json"),
            ),
            (
                "corrected RTL/cosim evidence",
                _has_any(names, "reports/cosim/corrected/", ".rpt")
                or _has_any(names, "reports/cosim/corrected/", ".json"),
            ),
            ("calibration SHA manifests", _has_any(names, "data/calibration/", ".sha256")),
            (
                "corrected benchmark CSVs",
                _has_any(names, "reports/benchmark/corrected/", ".csv"),
            ),
        ]
        for label, passed in class_checks:
            checks.append(Check(label, passed, "present" if passed else "missing"))

        try:
            release = _read_json_from_zip(
                archive, "reports/final_completion_gate.json"
            )
            with archive.open("git_sha.txt") as handle:
                packed_revision = handle.read().decode("ascii").strip()
            gates = release.get("gates")
            required = [
                row
                for row in (gates or [])
                if isinstance(row, dict) and row.get("release_required", True)
            ]
            release_ready = (
                release.get("status") == "PASS"
                and release.get("paper_pdf_permitted") is True
                and release.get("release_state")
                == "READY FOR HUMAN SUBMISSION REVIEW"
                and release.get("required_nonpassing_gate_count") == 0
                and isinstance(gates, list)
                and bool(gates)
                and bool(required)
                and release.get("gate_count") == len(gates)
                and release.get("required_gate_count") == len(required)
                and release.get("source_revision") == packed_revision
                and all(
                    isinstance(row, dict) and row.get("status") == "PASS"
                    for row in required
                )
            )
            checks.append(
                Check(
                    "authoritative final gate permits release",
                    release_ready,
                    (
                        f"{release.get('release_state', 'unknown')}; "
                        f"source_revision={release.get('source_revision', 'unknown')}; "
                        f"packed_revision={packed_revision}"
                    ),
                )
            )
            missing_gate_evidence = sorted(
                {
                    str(path)
                    for row in gates
                    if isinstance(row, dict)
                    for path in row.get("evidence", [])
                    if isinstance(path, str) and path not in names
                }
            )
            checks.append(
                Check(
                    "all final-gate evidence is packed",
                    not missing_gate_evidence,
                    ", ".join(missing_gate_evidence[:10]) or "all present",
                )
            )
        except Exception as exc:
            checks.append(Check("authoritative final gate parse", False, str(exc)))

        try:
            numbers = _read_json_from_zip(archive, "paper/numbers.json")
            provenance = _read_json_from_zip(archive, "paper/provenance.json")
            checks.append(Check("numbers/provenance key match", set(numbers) == set(provenance), f"{len(numbers)} numbers, {len(provenance)} provenance records"))
            canonical_match = (
                archive.read("paper/numbers.json")
                == archive.read("paper/corrected/numbers.json")
                and archive.read("paper/provenance.json")
                == archive.read("paper/corrected/provenance.json")
            )
            checks.append(
                Check(
                    "canonical aliases use corrected evidence",
                    canonical_match,
                    "byte-identical" if canonical_match else "mismatch",
                )
            )
            missing_sources = []
            for key, record_obj in numbers.items():
                record = record_obj if isinstance(record_obj, dict) else {}
                source = str(record.get("source", ""))
                if source != "external" and source and source not in names:
                    missing_sources.append(f"{key}->{source}")
            checks.append(Check("non-external number sources are packed", not missing_sources, ", ".join(missing_sources[:10]) or "all present"))
            details.append(f"Canonical numbers: {len(numbers)}")
        except Exception as exc:
            checks.append(Check("numbers/provenance parse", False, str(exc)))

        try:
            asset = _read_json_from_zip(
                archive, "paper/corrected/asset_manifest.json"
            )
            stale_assets = []
            for field in ("inputs_sha256", "outputs_sha256", "verified_figure_sha256"):
                for name, expected in asset.get(field, {}).items():
                    if name not in names or _archive_sha256(archive, name) != str(
                        expected
                    ).upper():
                        stale_assets.append(name)
            checks.append(
                Check(
                    "corrected asset hashes",
                    asset.get("status") == "PASS" and not stale_assets,
                    ", ".join(stale_assets[:10]) or "all match",
                )
            )
        except Exception as exc:
            checks.append(Check("corrected asset manifest parse", False, str(exc)))

        try:
            build = _read_json_from_zip(
                archive, "paper/corrected/paper_audit_build_manifest.json"
            )
            visual = _read_json_from_zip(
                archive, "paper/corrected/paper_visual_audit.json"
            )
            finalization = _read_json_from_zip(
                archive, "paper/corrected/paper_finalization_manifest.json"
            )
            audit_name = "paper/corrected/paper_audit_candidate.pdf"
            final_name = "paper/corrected/paper.pdf"
            audit_hash = _archive_sha256(archive, audit_name)
            final_hash = _archive_sha256(archive, final_name)
            final_valid = (
                build.get("status") == "PASS"
                and build.get("build_status") == "PASS"
                and build.get("artifact_kind") == "internal_audit_candidate"
                and build.get("submission_eligible") is False
                and str(build.get("output_sha256", "")).upper() == audit_hash
                and visual.get("status") == "PASS"
                and visual.get("visual_audit_status") == "PASS"
                and str(visual.get("audit_candidate_sha256", "")).upper()
                == audit_hash
                and finalization.get("status") == "PASS"
                and finalization.get("submission_eligible") is True
                and finalization.get("copy_identity") == "PASS"
                and str(finalization.get("release_gate_sha256", "")).upper()
                == _archive_sha256(
                    archive, "reports/final_completion_gate.json"
                )
                and str(finalization.get("audit_candidate_sha256", "")).upper()
                == audit_hash
                and str(finalization.get("output_sha256", "")).upper()
                == final_hash
                and audit_hash == final_hash
            )
            checks.append(
                Check(
                    "audited PDF exact-byte finalization",
                    final_valid,
                    f"audit={audit_hash}; final={final_hash}",
                )
            )
            stale_pages = [
                str(row.get("path", ""))
                for row in visual.get("pages", [])
                if not isinstance(row, dict)
                or str(row.get("path", "")) not in names
                or _archive_sha256(archive, str(row.get("path", "")))
                != str(row.get("sha256", "")).upper()
            ]
            checks.append(
                Check(
                    "visual-audit page renders",
                    not stale_pages
                    and len(visual.get("pages", []))
                    == int(visual.get("page_count", -1))
                    and bool(visual.get("pages")),
                    ", ".join(stale_pages[:10]) or "all match",
                )
            )
        except Exception as exc:
            checks.append(Check("paper finalization manifests parse", False, str(exc)))

        try:
            manifest = _read_json_from_zip(archive, "pack_manifest.json")
            listed = manifest.get("entries", {})
            stale_entries = [
                name
                for name, record in listed.items()
                if name not in names
                or not isinstance(record, dict)
                or _archive_sha256(archive, name)
                != str(record.get("sha256", "")).upper()
            ]
            unlisted = sorted(names - set(listed) - {"pack_manifest.json"})
            header_valid = (
                str(manifest.get("release_gate_sha256", "")).upper()
                == _archive_sha256(
                    archive, "reports/final_completion_gate.json"
                )
                and str(manifest.get("final_pdf_sha256", "")).upper()
                == _archive_sha256(archive, "paper/corrected/paper.pdf")
                and str(manifest.get("git_sha", ""))
                == archive.read("git_sha.txt").decode("ascii").strip()
            )
            checks.append(
                Check(
                    "pack-manifest hashes and coverage",
                    header_valid and not stale_entries and not unlisted,
                    (
                        f"header={'PASS' if header_valid else 'FAIL'}; "
                        f"stale={','.join(stale_entries[:5]) or 'none'}; "
                        f"unlisted={','.join(unlisted[:5]) or 'none'}"
                    ),
                )
            )
        except Exception as exc:
            checks.append(Check("pack manifest parse", False, str(exc)))

    return checks, details


def write_report(pack: Path, checks: list[Check], details: list[str]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    passed = all(check.passed for check in checks)
    lines = [
        "# Phase 7 Pack Validation",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Pack: `{pack.relative_to(ROOT).as_posix() if pack.exists() else pack.as_posix()}`",
        f"Overall status: {'PASS' if passed else 'FAIL'}",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {'PASS' if check.passed else 'FAIL'} | {check.detail} |")
    if details:
        lines.extend(["", "## Details", ""])
        lines.extend(f"- {detail}" for detail in details)
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Phase 7 paper-pack archive.")
    parser.add_argument("--pack", type=Path, default=_default_pack())
    args = parser.parse_args(argv)
    try:
        require_release_gate()
    except RuntimeError as exc:
        print(str(exc))
        return 1
    pack = args.pack if args.pack.is_absolute() else ROOT / args.pack
    checks, details = validate_pack(pack)
    write_report(pack, checks, details)
    print(REPORT.relative_to(ROOT).as_posix())
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

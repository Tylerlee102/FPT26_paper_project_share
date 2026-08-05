import hashlib
import json
import zipfile
from pathlib import Path

from scripts.validate_paper_pack import validate_pack


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _json(value: dict[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")


def test_corrected_pack_validator_accepts_complete_consistent_archive(
    tmp_path: Path,
) -> None:
    revision = "a" * 40
    audit_pdf = b"%PDF-1.4\nsynthetic audited bytes\n"
    final_pdf = bytes(audit_pdf)
    render = b"\x89PNG\r\n\x1a\nsynthetic page render"
    source = _json({"metric": 1})
    number_record = {
        "value": 1,
        "units": "count",
        "source": "reports/source.json",
        "source_line": 1,
        "extractor": "test",
        "git_sha": revision,
        "timestamp": "2026-08-02T00:00:00+00:00",
    }
    numbers = _json({"metric": number_record})
    provenance = bytes(numbers)
    gate = _json(
        {
            "status": "PASS",
            "paper_pdf_permitted": True,
            "release_state": "READY FOR HUMAN SUBMISSION REVIEW",
            "gate_count": 1,
            "required_gate_count": 1,
            "nonpassing_gate_count": 0,
            "required_nonpassing_gate_count": 0,
            "source_revision": revision,
            "gates": [{"gate": "all", "status": "PASS", "evidence": []}],
        }
    )
    asset = _json(
        {
            "status": "PASS",
            "inputs_sha256": {},
            "outputs_sha256": {},
            "verified_figure_sha256": {},
        }
    )
    build = _json(
        {
            "status": "PASS",
            "build_status": "PASS",
            "artifact_kind": "internal_audit_candidate",
            "submission_eligible": False,
            "output_sha256": _sha(audit_pdf),
            "asset_manifest_sha256": _sha(asset),
        }
    )
    visual = _json(
        {
            "status": "PASS",
            "visual_audit_status": "PASS",
            "submission_eligible": False,
            "audit_candidate_sha256": _sha(audit_pdf),
            "build_manifest_sha256": _sha(build),
            "page_count": 1,
            "pages": [
                {
                    "page": 1,
                    "path": "reports/rendered/corrected_paper/page-01.png",
                    "sha256": _sha(render),
                }
            ],
        }
    )
    finalization = _json(
        {
            "status": "PASS",
            "submission_eligible": True,
            "copy_identity": "PASS",
            "release_gate_sha256": _sha(gate),
            "audit_candidate_sha256": _sha(audit_pdf),
            "output_sha256": _sha(final_pdf),
        }
    )
    files: dict[str, bytes] = {
        "AGENTS.md": b"test\n",
        "paper/numbers.json": numbers,
        "paper/provenance.json": provenance,
        "paper/corrected/numbers.json": numbers,
        "paper/corrected/provenance.json": provenance,
        "paper/corrected/asset_manifest.json": asset,
        "paper/corrected/paper.tex": b"test\n",
        "paper/corrected/paper_audit_candidate.pdf": audit_pdf,
        "paper/corrected/paper_audit_build_manifest.json": build,
        "paper/corrected/paper_visual_audit.json": visual,
        "paper/corrected/paper_visual_checklist.json": b"{}\n",
        "paper/corrected/paper.pdf": final_pdf,
        "paper/corrected/paper_finalization_manifest.json": finalization,
        "paper/corrected/snippets/corrected_result_macros.tex": b"test\n",
        "paper/corrected/tables/result.tex": b"test\n",
        "paper/figures/corrected/result.pdf": b"%PDF-1.4\nfigure\n",
        "reports/final_completion_gate.json": gate,
        "reports/phase7_status.md": b"PASS\n",
        "reports/known_issues.md": b"none\n",
        "reports/source.json": source,
        "reports/vivado/corrected/impl.rpt": b"test\n",
        "reports/csynth/corrected/summary.json": b"{}\n",
        "reports/cosim/corrected/summary.json": b"{}\n",
        "reports/benchmark/corrected/summary.csv": b"x\n1\n",
        "reports/rendered/corrected_paper/page-01.png": render,
        "data/calibration/manifest.sha256": b"0  input\n",
        "docs/reviewer_traceability.md": b"PASS\n",
        "docs/reviewer_traceability_status.json": b"{}\n",
        "docs/evidence_manifest.md": b"PASS\n",
        "git_sha.txt": (revision + "\n").encode("ascii"),
        "git_log.txt": b"test\n",
        "git_status.txt": b"clean\n",
        "git_diff_stat.txt": b"none\n",
    }
    entry_manifest = {
        name: {"sha256": _sha(value), "bytes": len(value), "source": name}
        for name, value in files.items()
    }
    files["pack_manifest.json"] = _json(
        {
            "schema": 1,
            "git_sha": revision,
            "release_gate_sha256": _sha(gate),
            "final_pdf_sha256": _sha(final_pdf),
            "entries": entry_manifest,
        }
    )
    pack = tmp_path / "submission.zip"
    with zipfile.ZipFile(pack, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in files.items():
            archive.writestr(name, value)

    checks, _ = validate_pack(pack)
    failures = [check for check in checks if not check.passed]
    assert not failures, "; ".join(
        f"{check.name}: {check.detail}" for check in failures
    )

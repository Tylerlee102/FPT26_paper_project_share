"""Summarize reviewer-remediation rows against the audited paper candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACEABILITY = ROOT / "docs" / "reviewer_traceability.md"
VISUAL_AUDIT = ROOT / "paper" / "corrected" / "paper_visual_audit.json"
DEFAULT_OUTPUT = ROOT / "docs" / "reviewer_traceability_status.json"
ALLOWED = {"PASS", "FAIL", "NOT_RUN", "BLOCKED_EXTERNAL"}
EXPECTED_COMMENT_ROWS = 68
EXPECTED_DIRECTIVE_ROWS = 25


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _rows(path: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    pattern = re.compile(r"\|\s*(R\d+)(?::[^|]*)?\s*\||\|\s*(Directive-\d+)\s*\|")
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = pattern.match(line)
        if not match:
            continue
        fields = [item.strip() for item in line.split("|")[1:-1]]
        status = fields[-1] if fields else ""
        row_id = match.group(1) or match.group(2)
        result.append({"id": row_id, "status": status, "source_line": line_number})
    return result


def summarize(
    traceability_path: Path,
    visual_audit_path: Path,
    output: Path,
) -> dict[str, object]:
    rows = _rows(traceability_path)
    comments = [row for row in rows if str(row["id"]).startswith("R")]
    directives = [row for row in rows if str(row["id"]).startswith("Directive-")]
    if len(comments) != EXPECTED_COMMENT_ROWS:
        raise RuntimeError(
            f"reviewer traceability blocked: expected {EXPECTED_COMMENT_ROWS} "
            f"comment rows, found {len(comments)}"
        )
    if len(directives) != EXPECTED_DIRECTIVE_ROWS:
        raise RuntimeError(
            f"reviewer traceability blocked: expected {EXPECTED_DIRECTIVE_ROWS} "
            f"directive rows, found {len(directives)}"
        )
    invalid = [row for row in rows if row["status"] not in ALLOWED]
    if invalid:
        raise RuntimeError(
            f"reviewer traceability blocked: invalid status {invalid[0]['status']}"
        )

    visual_pass = False
    visual_hash = None
    if visual_audit_path.is_file():
        visual = json.loads(visual_audit_path.read_text(encoding="utf-8"))
        visual_pass = (
            isinstance(visual, dict)
            and visual.get("status") == "PASS"
            and visual.get("visual_audit_status") == "PASS"
        )
        visual_hash = _sha256(visual_audit_path)
    statuses = [str(row["status"]) for row in rows]
    if not visual_pass:
        status = "NOT_RUN"
    elif "FAIL" in statuses:
        status = "FAIL"
    elif "BLOCKED_EXTERNAL" in statuses:
        status = "BLOCKED_EXTERNAL"
    elif "NOT_RUN" in statuses:
        status = "NOT_RUN"
    else:
        status = "PASS"
    counts = Counter(statuses)
    report = {
        "schema": 1,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "traceability_source": traceability_path.relative_to(ROOT).as_posix(),
        "traceability_source_sha256": _sha256(traceability_path),
        "visual_audit": (
            visual_audit_path.relative_to(ROOT).as_posix()
            if visual_audit_path.is_file()
            else None
        ),
        "visual_audit_sha256": visual_hash,
        "visual_audit_status": "PASS" if visual_pass else "NOT_RUN",
        "comment_row_count": len(comments),
        "directive_row_count": len(directives),
        "status_counts": {key: counts.get(key, 0) for key in sorted(ALLOWED)},
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traceability", type=Path, default=TRACEABILITY)
    parser.add_argument("--visual-audit", type=Path, default=VISUAL_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = summarize(
            _resolve(args.traceability),
            _resolve(args.visual_audit),
            _resolve(args.output),
        )
    except (RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 1
    print(json.dumps({"status": report["status"], "rows": len(report["rows"])}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

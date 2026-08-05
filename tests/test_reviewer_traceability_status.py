from pathlib import Path
import json

from scripts.reviewer_traceability_status import summarize


def test_current_traceability_is_not_run_without_audited_pdf(tmp_path: Path) -> None:
    output = tmp_path / "traceability.json"
    report = summarize(
        Path("docs/reviewer_traceability.md").resolve(),
        tmp_path / "missing_visual_audit.json",
        output,
    )

    assert report["status"] == "NOT_RUN"
    assert report["visual_audit_status"] == "NOT_RUN"
    assert report["comment_row_count"] == 68
    assert report["directive_row_count"] == 25
    assert output.is_file()


def test_traceability_failure_is_not_hidden_by_not_run_rows(
    tmp_path: Path,
) -> None:
    traceability = tmp_path / "traceability.md"
    rows = [
        f"| R{index:02d}: `thread` reply 0 | item | "
        f"{'FAIL' if index == 1 else 'NOT_RUN'} |"
        for index in range(1, 69)
    ]
    rows.extend(
        f"| Directive-{index:02d} | issue | action | evidence | section | PASS |"
        for index in range(1, 26)
    )
    traceability.write_text("\n".join(rows), encoding="utf-8")
    visual = tmp_path / "visual.json"
    visual.write_text(
        json.dumps({"status": "PASS", "visual_audit_status": "PASS"}),
        encoding="utf-8",
    )

    report = summarize(
        traceability,
        visual,
        tmp_path / "traceability_status.json",
    )

    assert report["status"] == "FAIL"

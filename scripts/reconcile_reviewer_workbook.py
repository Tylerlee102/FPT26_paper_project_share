"""Reconcile the authoritative Overleaf comment export with the review ledger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


LEGACY_MAP: dict[tuple[str, int], tuple[str, ...]] = {
    ("6a33db3e6572004fe08a8096", 0): ("Legacy-01",),
    ("6a33ddd5dc32bf2129204dad", 0): ("Legacy-02",),
    ("6a33f47fdc32bf2129205845", 0): ("Legacy-03",),
    ("6a33f4b76572004fe08a8bc5", 0): ("Legacy-04",),
    ("6a33f510537013d3d71a2f20", 0): ("Legacy-05",),
    ("6a33f59d87496cf05d0b1b90", 0): ("Legacy-06", "Legacy-07"),
    ("6a33faa0dc32bf2129205b87", 0): ("Legacy-08",),
    ("6a33fb05537013d3d71a3253", 0): ("Legacy-09",),
    ("6a33fb116572004fe08a8f14", 0): ("Legacy-10",),
    ("6a33fb1a34ed05fee4df6674", 0): ("Legacy-12",),
    ("6a33fb2234ed05fee4df667a", 0): ("Legacy-13",),
    ("6a33fb366572004fe08a8f26", 0): ("Legacy-14",),
    ("6a33fb6cdc32bf2129205be9", 0): ("Legacy-15",),
    ("6a33fb6cdc32bf2129205be9", 1): ("Legacy-16",),
    ("6a33fbbb34ed05fee4df66c5", 0): ("Legacy-11",),
    ("6a33fbfedc32bf2129205c3a", 0): ("Legacy-17",),
    ("6a33fc1887496cf05d0b1ed2", 0): ("Legacy-18",),
    ("6a33fc586572004fe08a8fb7", 0): ("Legacy-19",),
    ("6a33fcab87496cf05d0b1f19", 0): ("Legacy-20",),
    ("6a33fd0287496cf05d0b1f47", 0): ("Legacy-21",),
    ("6a33fd9fdc32bf2129205d0f", 0): ("Legacy-22",),
    ("6a33fdcb34ed05fee4df67c1", 0): ("Legacy-23",),
    ("6a33fdea87496cf05d0b1fb9", 0): ("Legacy-24",),
    ("6a33fe146572004fe08a9093", 0): ("Legacy-25",),
    ("6a33fe26537013d3d71a3406", 0): ("Legacy-26",),
    ("6a33feb7537013d3d71a3455", 0): ("Legacy-27", "Legacy-28"),
    ("6a33fef334ed05fee4df6848", 0): ("Legacy-29",),
    ("6a33ff3a537013d3d71a349a", 0): ("Legacy-30",),
    ("6a33ff6b537013d3d71a34b1", 0): ("Legacy-31",),
    ("6a33ffd2dc32bf2129205e28", 0): ("Legacy-32",),
    ("6a33ffd2dc32bf2129205e28", 1): ("Legacy-33",),
    ("6a34002987496cf05d0b20d7", 0): ("Legacy-34",),
    ("6a340079537013d3d71a3524", 0): ("Legacy-35",),
    ("6a3400db6572004fe08a91ed", 0): ("Legacy-36",),
    ("6a34013034ed05fee4df6970", 0): ("Legacy-37",),
    ("6a3401ee537013d3d71a35d2", 0): ("Legacy-38",),
    ("6a34029534ed05fee4df6a1c", 0): ("Legacy-39",),
    ("6a34029534ed05fee4df6a1c", 1): ("Legacy-39",),
    ("6a34032fdc32bf2129205fb8", 0): ("Legacy-40",),
    ("6a3403836572004fe08a9332", 0): ("Legacy-41",),
    ("6a340541537013d3d71a3780", 0): ("Legacy-42",),
    ("6a34059134ed05fee4df6b80", 0): ("Legacy-43",),
    ("6a3405b56572004fe08a944f", 0): ("Legacy-44",),
    ("6a3406c3dc32bf2129206182", 0): ("Legacy-45",),
    ("6a34070b87496cf05d0b2470", 0): ("Legacy-42",),
    ("6a340744dc32bf21292061c0", 0): ("Legacy-46",),
    ("6a3407b9537013d3d71a38a7", 0): ("Legacy-47",),
    ("6a340841537013d3d71a38cf", 0): ("Legacy-48",),
    ("6a3408d6537013d3d71a3904", 0): ("Legacy-49",),
    ("6a340d9a6572004fe08a97e9", 0): ("Legacy-50",),
    ("6a340e24537013d3d71a3b4a", 0): ("Legacy-51",),
    ("6a340e956572004fe08a985e", 0): ("Legacy-52",),
    ("6a340e9e537013d3d71a3b86", 0): ("Legacy-53",),
    ("6a340ec5dc32bf21292064cf", 0): ("Legacy-54",),
    ("6a340ef1537013d3d71a3ba5", 0): ("Legacy-55",),
    ("6a340f28dc32bf2129206501", 0): ("Legacy-56",),
    ("6a34143d34ed05fee4df720b", 0): ("Legacy-57",),
    ("6a34146987496cf05d0b2a61", 0): ("Legacy-58",),
    ("6a34152087496cf05d0b2aa7", 0): ("Legacy-59",),
    ("6a34155687496cf05d0b2abd", 0): ("Legacy-44",),
    ("6a3415786572004fe08a9b69", 0): ("Legacy-60",),
    ("6a3415976572004fe08a9b77", 0): ("Legacy-61",),
    ("6a3415b76572004fe08a9b80", 0): ("Legacy-62",),
    ("6a3415f634ed05fee4df72cd", 0): ("Legacy-63",),
    ("6a341638537013d3d71a3ec2", 0): ("Legacy-64",),
    ("6a34179f6572004fe08a9c24", 0): ("Legacy-65",),
    ("6a33db0434ed05fee4df5807", 0): ("Legacy-67",),
    ("6a3417b734ed05fee4df7361", 0): ("Legacy-66",),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _column_index(cell_reference: str) -> int:
    letters = re.match(r"[A-Z]+", cell_reference)
    if letters is None:
        raise ValueError(f"invalid cell reference: {cell_reference}")
    index = 0
    for character in letters.group(0):
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.findall(f".//{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def _sheet_target(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationship_id = None
    for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
        if sheet.attrib.get("name") == sheet_name:
            relationship_id = sheet.attrib[f"{{{REL_NS}}}id"]
            break
    if relationship_id is None:
        raise ValueError(f"worksheet not found: {sheet_name}")

    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relationship in relationships.findall(f"{{{PKG_REL_NS}}}Relationship"):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib["Target"].replace("\\", "/")
            return target.lstrip("/") if target.startswith("xl/") else f"xl/{target.lstrip('/')}"
    raise ValueError(f"worksheet relationship not found: {relationship_id}")


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> object:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.findall(f".//{{{MAIN_NS}}}t")
        )
    value_node = cell.find(f"{{{MAIN_NS}}}v")
    if value_node is None or value_node.text is None:
        return None
    value = value_node.text
    if cell_type == "s":
        return shared_strings[int(value)]
    if cell_type == "b":
        return value == "1"
    if cell_type in {"str", "e"}:
        return value
    number = float(value)
    return int(number) if number.is_integer() else number


def read_xlsx_values(path: Path, sheet_name: str) -> list[list[object]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _shared_strings(archive)
        sheet = ET.fromstring(archive.read(_sheet_target(archive, sheet_name)))

    sparse: dict[tuple[int, int], object] = {}
    max_row = 0
    max_column = 0
    for cell in sheet.findall(f".//{{{MAIN_NS}}}c"):
        reference = cell.attrib["r"]
        row_match = re.search(r"\d+$", reference)
        if row_match is None:
            raise ValueError(f"cell reference lacks row: {reference}")
        row = int(row_match.group(0)) - 1
        column = _column_index(reference)
        sparse[(row, column)] = _cell_value(cell, shared_strings)
        max_row = max(max_row, row + 1)
        max_column = max(max_column, column + 1)

    return [
        [sparse.get((row, column)) for column in range(max_column)]
        for row in range(max_row)
    ]


def parse_legacy_rows(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| Legacy-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            raise ValueError(f"unexpected legacy table row: {line}")
        legacy_id, concern, action, evidence, section, status = cells
        rows[legacy_id] = {
            "concern": concern,
            "action": action,
            "evidence": evidence,
            "section": section,
            "status": status,
        }
    if len(rows) != 67:
        raise ValueError(f"expected 67 legacy topics, found {len(rows)}")
    return rows


def _join_unique(values: list[str]) -> str:
    return "; ".join(OrderedDict.fromkeys(values))


def _markdown_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")


def _status_for(legacy_rows: list[dict[str, str]]) -> str:
    statuses = {row["status"] for row in legacy_rows}
    if "BLOCKED_EXTERNAL" in statuses:
        return "BLOCKED_EXTERNAL"
    return "NOT_RUN"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--artifact-json", type=Path, required=True)
    parser.add_argument("--legacy-ledger", type=Path, required=True)
    parser.add_argument("--traceability", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    workbook_values = read_xlsx_values(args.workbook, "Comments")
    artifact_payload = json.loads(args.artifact_json.read_text(encoding="utf-8"))
    artifact_values = artifact_payload["values"]
    workbook_values = [
        [None if value == "" else value for value in row] for row in workbook_values
    ]
    if workbook_values != artifact_values:
        differences = []
        row_count = max(len(workbook_values), len(artifact_values))
        for row_index in range(row_count):
            direct_row = workbook_values[row_index] if row_index < len(workbook_values) else []
            artifact_row = artifact_values[row_index] if row_index < len(artifact_values) else []
            column_count = max(len(direct_row), len(artifact_row))
            for column_index in range(column_count):
                direct = direct_row[column_index] if column_index < len(direct_row) else None
                artifact = artifact_row[column_index] if column_index < len(artifact_row) else None
                if direct != artifact:
                    differences.append(
                        {
                            "cell": f"R{row_index + 1}C{column_index + 1}",
                            "direct": direct,
                            "artifact": artifact,
                            "direct_type": type(direct).__name__,
                            "artifact_type": type(artifact).__name__,
                        }
                    )
                if len(differences) == 10:
                    break
            if len(differences) == 10:
                break
        raise AssertionError(
            "artifact-tool extraction differs from independent XLSX XML parse: "
            + json.dumps(differences, ensure_ascii=False)
        )
    expected_headers = [
        "Thread ID",
        "Reply #",
        "Author",
        "Date",
        "Comment",
        "Highlighted Text",
        "Context",
        "Char Position",
    ]
    if workbook_values[0] != expected_headers:
        raise AssertionError(f"unexpected headers: {workbook_values[0]}")

    raw_records = []
    for excel_row, values in enumerate(workbook_values[1:], start=2):
        raw_records.append({"excel_row": excel_row, "values": values})

    exact_counts = Counter(
        json.dumps(record["values"], ensure_ascii=False, separators=(",", ":"))
        for record in raw_records
    )
    exact_duplicate_extras = sum(count - 1 for count in exact_counts.values())

    messages: OrderedDict[tuple[str, int], dict[str, object]] = OrderedDict()
    for record in raw_records:
        values = record["values"]
        key = (str(values[0]), int(values[1]))
        candidate = {
            "thread_id": key[0],
            "reply_number": key[1],
            "author": str(values[2]),
            "date": str(values[3]),
            "comment": str(values[4]),
            "highlighted_text": values[5],
            "context": values[6],
            "char_position": values[7],
            "raw_rows": [record["excel_row"]],
        }
        if key not in messages:
            messages[key] = candidate
            continue
        current = messages[key]
        for field in ("author", "date", "comment", "char_position"):
            if current[field] != candidate[field]:
                raise AssertionError(f"conflicting duplicate message {key}: {field}")
        current["raw_rows"].append(record["excel_row"])
        current_completeness = len(str(current["highlighted_text"] or "")) + len(
            str(current["context"] or "")
        )
        candidate_completeness = len(str(candidate["highlighted_text"] or "")) + len(
            str(candidate["context"] or "")
        )
        if candidate_completeness > current_completeness:
            raw_rows = current["raw_rows"]
            messages[key] = candidate
            messages[key]["raw_rows"] = raw_rows

    reviewer_messages = [
        message
        for message in messages.values()
        if str(message["author"]).casefold() == "jason.blocklove"
    ]
    author_messages = [message for message in messages.values() if message not in reviewer_messages]
    reviewer_keys = {
        (str(message["thread_id"]), int(message["reply_number"]))
        for message in reviewer_messages
    }
    if reviewer_keys != set(LEGACY_MAP):
        missing = sorted(reviewer_keys - set(LEGACY_MAP))
        extra = sorted(set(LEGACY_MAP) - reviewer_keys)
        raise AssertionError(f"reviewer mapping mismatch; missing={missing}, extra={extra}")
    if len(reviewer_messages) != 68 or len(author_messages) != 4:
        raise AssertionError(
            f"expected 68 reviewer and 4 author messages, got "
            f"{len(reviewer_messages)} and {len(author_messages)}"
        )

    legacy = parse_legacy_rows(args.legacy_ledger)
    reconciliation_rows = []
    for index, message in enumerate(reviewer_messages, start=1):
        key = (str(message["thread_id"]), int(message["reply_number"]))
        legacy_ids = LEGACY_MAP[key]
        mapped = [legacy[legacy_id] for legacy_id in legacy_ids]
        raw_rows = [int(value) for value in message["raw_rows"]]
        highlighted = str(message["highlighted_text"] or "")
        exact_concern = str(message["comment"])
        if highlighted:
            exact_concern += f' [highlighted: "{highlighted}"]'
        reconciliation_rows.append(
            {
                "source_index": index,
                "thread_id": message["thread_id"],
                "reply_number": message["reply_number"],
                "reviewer": message["author"],
                "date": message["date"],
                "comment_text": message["comment"],
                "highlighted_text": message["highlighted_text"],
                "context": message["context"],
                "char_position": message["char_position"],
                "raw_workbook_rows": ";".join(str(value) for value in raw_rows),
                "source_cell": f"Comments!E{raw_rows[0]}",
                "legacy_topic_ids": ";".join(legacy_ids),
                "concern": exact_concern,
                "required_action": _join_unique([row["action"] for row in mapped]),
                "paper_section": _join_unique([row["section"] for row in mapped]),
                "status": _status_for(mapped),
            }
        )

    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    raw_csv = args.evidence_dir / "reviewer_workbook_rows.csv"
    with raw_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["excel_row", *expected_headers])
        for record in raw_records:
            writer.writerow([record["excel_row"], *record["values"]])

    reconciliation_csv = args.evidence_dir / "reviewer_workbook_reconciliation.csv"
    with reconciliation_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(reconciliation_rows[0]))
        writer.writeheader()
        writer.writerows(reconciliation_rows)

    workbook_hash = _sha256(args.workbook)
    artifact_hash = _sha256(args.artifact_json)
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    reconciliation_report = args.evidence_dir / "reviewer_workbook_reconciliation.md"
    reconciliation_report.write_text(
        "\n".join(
            [
                "# Reviewer Workbook Reconciliation",
                "",
                f"- Timestamp (UTC): `{timestamp}`",
                f"- Preserved source: `{args.workbook.as_posix()}`",
                f"- Source SHA256: `{workbook_hash}`",
                f"- Source size: `{args.workbook.stat().st_size}` bytes",
                "- Worksheet/table: `Comments!A1:H94`",
                f"- Artifact-tool extraction: `{args.artifact_json.as_posix()}`",
                f"- Artifact extraction SHA256: `{artifact_hash}`",
                "- Independent verification: Python standard-library ZIP/XML parse matched the artifact-tool 94x8 semantic value matrix after canonicalizing empty-string cells to null.",
                f"- Raw exported message rows: `{len(raw_records)}`",
                f"- Distinct thread/reply message keys: `{len(messages)}`",
                f"- Distinct reviewer messages: `{len(reviewer_messages)}`",
                f"- Distinct author messages excluded from reviewer ledger: `{len(author_messages)}`",
                f"- Exact duplicate extra rows: `{exact_duplicate_extras}`",
                f"- Additional same-message variant rows: `{len(raw_records) - len(messages) - exact_duplicate_extras}`",
                "- Reconciliation result: `PASS`",
                "",
                "The 67-topic derivative note is not a one-row-per-source-message export. It splits two multi-part reviewer messages and combines three comment pairs. The authoritative ledger therefore contains 68 rows, one for each distinct `jason.blocklove` thread/reply message. Duplicate exporter rows are retained in the raw CSV and referenced by row number.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    ledger_lines = [
        "## Authoritative 68-Comment Ledger",
        "",
        "Each row below corresponds to one distinct reviewer thread/reply message in the preserved workbook. Exact text and full context are retained in `docs/evidence/reviewer_workbook_reconciliation.csv`.",
        "",
        "| Source comment | Reviewer | Concern | Required action | Evidence path | Paper section | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in reconciliation_rows:
        raw_rows = row["raw_workbook_rows"].replace(";", ", ")
        source = f"R{int(row['source_index']):02d}: `{row['thread_id']}` reply {row['reply_number']}"
        display_concern = str(row["comment_text"])
        highlighted = str(row["highlighted_text"] or "").replace("\r\n", " ").replace(
            "\n", " "
        )
        highlighted = re.sub(r"\s+", " ", highlighted).strip()
        if highlighted:
            if len(highlighted) > 160:
                highlighted = highlighted[:157].rstrip() + "..."
            display_concern += f' [highlighted: "{highlighted}"]'
        evidence = (
            f"`legacy/reviewer_sources/overleaf-comments-2026-06-18.xlsx` "
            f"(`Comments!E{raw_rows.split(', ')[0]}`; raw rows {raw_rows}); "
            f"`docs/evidence/reviewer_workbook_reconciliation.csv`"
        )
        ledger_lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    source,
                    row["reviewer"],
                    display_concern,
                    row["required_action"],
                    evidence,
                    row["paper_section"],
                    row["status"],
                )
            )
            + " |"
        )

    current_traceability = args.traceability.read_text(encoding="utf-8")
    tail_marker = "## Gated Remediation Concerns"
    if tail_marker not in current_traceability:
        raise ValueError(f"missing traceability marker: {tail_marker}")
    tail = tail_marker + current_traceability.split(tail_marker, maxsplit=1)[1]
    closure_marker = "## Closure Rule"
    if closure_marker not in tail:
        raise ValueError(f"missing closure marker: {closure_marker}")
    gated_section = tail.split(closure_marker, maxsplit=1)[0].rstrip()
    traceability_text = "\n".join(
        [
            "# Reviewer Traceability",
            "",
            "## Source Availability",
            "",
            "| Reviewer | Concern | Required action | Evidence path | Paper section | Status |",
            "|---|---|---|---|---|---|",
            f"| Authoritative reviewer workbook | Verify source integrity and reconcile one row per distinct reviewer message. | Preserve, hash, extract, independently cross-check, and map all reviewer messages. | `legacy/reviewer_sources/overleaf-comments-2026-06-18.xlsx` (SHA256 `{workbook_hash}`); `docs/evidence/reviewer_workbook_reconciliation.md`; `docs/evidence/reviewer_workbook_reconciliation.csv` | All | PASS |",
            "",
            "The named workbook was recovered from the local Downloads directory and preserved byte-for-byte. The originally referenced attachment UUID remains absent, but the recovered file is the exact workbook named by `paper/comment_fix_review_2026_06_18.txt`. Artifact-tool extraction and an independent ZIP/XML parser agree on every semantic cell in `Comments!A1:H94` after empty-string cells are canonicalized to null.",
            "",
            *ledger_lines,
            "",
            gated_section,
            "",
            "## Closure Rule",
            "",
            "Authoritative reviewer-source ingestion is `PASS`. Final reviewer remediation remains `BLOCKED_EXTERNAL`: the artifact-release policy still requires an author decision, and all other comment actions require verification against a future evidence-supported final PDF. The project remains NOT PAPER READY.",
            "",
        ]
    )
    args.traceability.write_text(traceability_text, encoding="utf-8", newline="\n")

    print(
        json.dumps(
            {
                "status": "PASS",
                "workbook_sha256": workbook_hash,
                "raw_rows": len(raw_records),
                "distinct_message_keys": len(messages),
                "reviewer_messages": len(reviewer_messages),
                "author_messages": len(author_messages),
                "exact_duplicate_extra_rows": exact_duplicate_extras,
                "same_message_variant_extra_rows": len(raw_records)
                - len(messages)
                - exact_duplicate_extras,
                "raw_csv": str(raw_csv),
                "reconciliation_csv": str(reconciliation_csv),
                "traceability": str(args.traceability),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

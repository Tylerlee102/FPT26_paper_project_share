import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "evidence" / "citation_archival_audit_2026_08_06_v4.csv"
AUDIT_NOTE = ROOT / "docs" / "evidence" / "citation_archival_audit_2026_08_06_v4.md"
SUPERSEDED_AUDITS = (
    ROOT / "docs" / "evidence" / "citation_archival_audit_2026_08_02.csv",
    ROOT / "docs" / "evidence" / "citation_archival_audit_2026_08_02_v2.csv",
    ROOT / "docs" / "evidence" / "citation_archival_audit_2026_08_03_v3.csv",
)


def test_every_manuscript_reference_has_a_passed_archival_audit() -> None:
    paper = (ROOT / "paper" / "corrected" / "paper.tex").read_text(
        encoding="utf-8"
    )
    with AUDIT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    bibliography = set(re.findall(r"\\bibitem\{([^}]+)\}", paper))
    audited = {row["citation_key"] for row in rows}
    assert audited == bibliography
    assert len(rows) == len(audited)
    assert all(row["status"] == "PASS" for row in rows)
    assert all(row["primary_url"].startswith("https://") for row in rows)
    assert all(row["source_checked_on"] == "2026-08-06" for row in rows)
    assert all(row["publication_status"] for row in rows)
    assert all(row["selected_form"] for row in rows)
    classes = [row["record_class"] for row in rows]
    assert classes.count("archival_paper") == 8
    assert classes.count("standard") == 1
    assert classes.count("pinned_artifact") == 3
    assert classes.count("preprint") == 4
    preprints = {
        row["citation_key"] for row in rows if row["record_class"] == "preprint"
    }
    assert preprints == {
        "gupta2026",
        "jackscales",
        "mxformer",
        "mxattention",
    }
    for key in preprints:
        row = next(item for item in rows if item["citation_key"] == key)
        assert "no archival venue metadata" in row["publication_status"]
        entry = paper.split(rf"\bibitem{{{key}}}", 1)[1].split(r"\bibitem", 1)[0]
        assert "arXiv preprint" in re.sub(r"\s+", " ", entry)
    qwen = next(row for row in rows if row["citation_key"] == "qwen3nextmodel")
    revision = "9c7f2fbe84465e40164a94cc16cd30b6999b0cc7"
    assert revision in qwen["publication_status"]
    assert revision in qwen["primary_url"]
    assert revision in paper
    quantgdn = next(row for row in rows if row["citation_key"] == "quantgdn")
    assert "ICML 2026" in quantgdn["publication_status"]
    assert "volume 306" in quantgdn["publication_status"]
    assert "openreview.net/pdf" in quantgdn["primary_url"]
    benchmark = next(row for row in rows if row["citation_key"] == "mxfpbenchmark")
    assert benchmark["record_class"] == "archival_paper"
    assert "ACL 2026" in benchmark["publication_status"]
    assert "aclanthology.org/2026.acl-long.1854" in benchmark["primary_url"]
    assert "10.18653/v1/2026.acl-long.1854" in paper
    for key, revision in (
        ("transformersqwen", "8ac2b916b042b1f78b75c9eb941c0f5d2cdd8e10"),
        ("fla021", "a670dff4c2537fc1a82486584dd9569e18fba833"),
    ):
        row = next(item for item in rows if item["citation_key"] == key)
        assert revision in row["publication_status"]
        assert revision in row["primary_url"]
        assert revision in paper
    assert AUDIT_NOTE.is_file()
    assert all(path.is_file() for path in SUPERSEDED_AUDITS)


def test_bibliography_follows_first_citation_order() -> None:
    paper = (ROOT / "paper" / "corrected" / "paper.tex").read_text(
        encoding="utf-8"
    )
    body = paper.split(r"\begin{thebibliography}", 1)[0]
    first_use: list[str] = []
    for match in re.finditer(r"\\cite\{([^}]+)\}", body):
        for key in (item.strip() for item in match.group(1).split(",")):
            if key not in first_use:
                first_use.append(key)
    bibliography = re.findall(r"\\bibitem\{([^}]+)\}", paper)
    assert first_use == bibliography

import csv

from scripts.rs2_paper_assets import CONTROLLED, VARIANTS, _controlled_rows


def test_controlled_tradeoff_provenance_uses_parsed_candidate_row() -> None:
    rows, line_by_key = _controlled_rows()
    candidate = next(name for name, slug in VARIANTS.items() if slug == "rs2")
    line_number = line_by_key[(candidate, 8192)]

    with CONTROLLED.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))

    row = source_rows[line_number - 2]
    assert row["variant"] == candidate
    assert row["token_index"] == "8192"
    assert row["layer_id"] == ""
    assert row in rows

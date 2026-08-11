import csv
import hashlib
import json

from scripts.rs2_paper_assets import (
    CONTROLLED,
    ROOT,
    TIMING_EXPERIMENTS,
    VARIANTS,
    _add_timing_ablation_numbers,
    _controlled_rows,
)


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


def test_timing_ablation_numbers_are_bound_to_archived_summaries() -> None:
    numbers: dict[str, dict[str, object]] = {}
    provenance: dict[str, dict[str, object]] = {}
    _add_timing_ablation_numbers(numbers, provenance, "a" * 40, "test")

    assert len(numbers) == 2 + 2 * len(TIMING_EXPERIMENTS)
    assert set(numbers) == set(provenance)
    assert numbers["rs2_timing_ablation_selected_wns_ns"]["value"] == -1.736
    assert (
        numbers[
            "rs2_timing_ablation_fold_write_setup_failing_endpoints"
        ]["value"]
        == 29168
    )
    for row in numbers.values():
        source = ROOT / str(row["source"])
        assert source.is_file()
        assert int(row["source_line"]) > 0


def test_generated_timing_ablation_table_is_manifest_bound() -> None:
    table = ROOT / "paper/corrected/tables/rs2_timing_ablation.tex"
    manifest_path = ROOT / "paper/corrected/asset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative = table.relative_to(ROOT).as_posix()

    assert manifest["outputs_sha256"][relative] == hashlib.sha256(
        table.read_bytes()
    ).hexdigest().upper()
    text = table.read_text(encoding="utf-8")
    assert "Selected RS2/R3 & -1.736 & 43{,}593" in text
    assert "Fold-write commit & -1.294 & 29{,}168" in text
    assert "Address fanout 16 & -1.453 & 35{,}126" in text

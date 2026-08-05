import json
from pathlib import Path

from scripts.aggregate_e2m0_encoded_held_out import _separated_input_hashes


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "e2m0_encoded"
    / "held_out"
    / "held_out_summary.json"
)


def _configuration() -> dict[str, object]:
    return {
        "tokens": 2,
        "checkpoints": [1, 2],
        "seed": 0xA17E5EED,
        "split": "unit_test",
        "trace_family": "high_retention",
        "num_value_heads": 4,
        "num_qk_heads": 2,
        "key_dim": 8,
        "value_dim": 8,
        "activation_block_size": 32,
        "state_block_size": 32,
    }


def test_input_hashes_treat_initial_state_as_a_paired_condition() -> None:
    random_hashes = _separated_input_hashes(_configuration(), "random")
    zero_hashes = _separated_input_hashes(_configuration(), "zero")

    assert random_hashes["token_stream_sha256"] == zero_hashes["token_stream_sha256"]
    assert random_hashes["initial_state_sha256"] != zero_hashes["initial_state_sha256"]
    assert random_hashes["combined_input_sha256"] != zero_hashes["combined_input_sha256"]


def test_held_out_summary_counts_seed_blocks_not_rows() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["seed_block_count"] == 3
    assert summary["paired_condition_count"] == 6
    assert summary["statistical_unit"].startswith("seed block")

    by_seed: dict[int, list[dict[str, object]]] = {}
    for record in summary["records"]:
        by_seed.setdefault(int(record["seed"]), []).append(record)
    assert len(by_seed) == 3
    for records in by_seed.values():
        assert len(records) == 2
        assert len({record["token_stream_sha256"] for record in records}) == 1
        assert len({record["initial_state_sha256"] for record in records}) == 2

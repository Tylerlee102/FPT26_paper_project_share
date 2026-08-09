from __future__ import annotations

from scripts.long_sequence_stability import TraceConfiguration
from scripts.rs2_encoded_stability import (
    CAPACITY,
    COUNTER_FIELDS,
    VARIANT,
    logical_encoded_state_bytes,
    run_encoded_trace,
    write_csv,
    write_manifest,
)
from scripts.verify_rs2_encoded_stability import verify_manifest


def _config(*, tokens: int, value_heads: int, qk_heads: int, dim: int) -> TraceConfiguration:
    return TraceConfiguration(
        tokens=tokens,
        checkpoints=(1, tokens),
        seed=0xFB72,
        split="development",
        trace_family="high_retention",
        num_value_heads=value_heads,
        num_qk_heads=qk_heads,
        key_dim=dim,
        value_dim=dim,
        activation_block_size=32,
        state_block_size=32,
    )


def test_controlled_full_dimension_logical_bytes() -> None:
    config = _config(tokens=64, value_heads=32, qk_heads=16, dim=128)
    assert logical_encoded_state_bytes(config) == 576_912


def test_trace_records_fold_schedule_and_counter_prefix_sums() -> None:
    config = _config(tokens=6, value_heads=4, qk_heads=2, dim=8)
    result = run_encoded_trace(config, initial_state_mode="zero")
    assert len(result.token_rows) == 12
    assert len(result.checkpoint_rows) == 4
    rows = [row for row in result.token_rows if row["variant"] == VARIANT]
    assert [int(row["live_entries"]) for row in rows] == [1, 2, 0, 1, 2, 0]
    assert [int(row["folded"]) for row in rows] == [0, 0, 1, 0, 0, 1]
    assert [int(row["folds"]) for row in rows] == [0, 0, 1, 1, 1, 2]
    running = {name: 0 for name in COUNTER_FIELDS}
    for row in rows:
        for name in running:
            running[name] += int(row[name])
            assert int(row[f"cumulative_{name}"]) == running[name]
    assert CAPACITY == 3


def test_manifest_verifier_recomputes_every_row(tmp_path) -> None:
    config = _config(tokens=3, value_heads=4, qk_heads=2, dim=8)
    result = run_encoded_trace(config, initial_state_mode="zero")
    token_csv = tmp_path / "tiny_tokens.csv"
    checkpoint_csv = tmp_path / "tiny_checkpoints.csv"
    raw_log = tmp_path / "tiny.log"
    manifest = tmp_path / "tiny_manifest.json"
    write_csv(token_csv, result.token_rows)
    write_csv(checkpoint_csv, result.checkpoint_rows)
    raw_log.write_text("test log\n", encoding="utf-8")
    write_manifest(
        manifest,
        result=result,
        token_csv=token_csv,
        checkpoint_csv=checkpoint_csv,
        raw_log=raw_log,
        command="pytest library call",
    )
    verification = verify_manifest(manifest, recompute=True)
    assert verification["status"] == "PASS"
    assert verification["recomputed"] is True
    assert verification["failures"] == []

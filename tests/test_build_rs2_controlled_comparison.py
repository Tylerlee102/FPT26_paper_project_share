from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.build_rs2_controlled_comparison import build
from scripts.long_sequence_stability import (
    TraceConfiguration,
    run_long_trace,
    write_csv as write_baseline_csv,
    write_manifest as write_baseline_manifest,
)
from scripts.rs2_encoded_stability import (
    VARIANT,
    run_encoded_trace,
    write_csv as write_rs2_csv,
    write_manifest as write_rs2_manifest,
)


def test_builds_trace_identical_controlled_comparison(tmp_path: Path) -> None:
    config = TraceConfiguration(
        tokens=4,
        checkpoints=(2, 4),
        seed=0xFB72,
        split="development",
        trace_family="high_retention",
        num_value_heads=2,
        num_qk_heads=1,
        key_dim=32,
        value_dim=32,
        activation_block_size=32,
        state_block_size=32,
    )
    baseline_result = run_long_trace(config)
    baseline_tokens = tmp_path / "baseline_tokens.csv"
    baseline_checkpoints = tmp_path / "baseline_checkpoints.csv"
    baseline_manifest = tmp_path / "baseline_manifest.json"
    baseline_report = tmp_path / "baseline.md"
    baseline_report.write_text("baseline\n", encoding="utf-8")
    write_baseline_csv(baseline_tokens, baseline_result.token_rows)
    write_baseline_csv(baseline_checkpoints, baseline_result.checkpoint_rows)
    write_baseline_manifest(
        baseline_manifest,
        result=baseline_result,
        token_csv=baseline_tokens,
        checkpoint_csv=baseline_checkpoints,
        report_path=baseline_report,
        execution_command="pytest baseline",
    )

    rs2_result = run_encoded_trace(config, initial_state_mode="random")
    assert rs2_result.gate_pass
    rs2_tokens = tmp_path / "rs2_tokens.csv"
    rs2_checkpoints = tmp_path / "rs2_checkpoints.csv"
    rs2_manifest = tmp_path / "rs2_manifest.json"
    rs2_log = tmp_path / "rs2.log"
    rs2_log.write_text("PASS\n", encoding="utf-8")
    write_rs2_csv(rs2_tokens, rs2_result.token_rows)
    write_rs2_csv(rs2_checkpoints, rs2_result.checkpoint_rows)
    write_rs2_manifest(
        rs2_manifest,
        result=rs2_result,
        token_csv=rs2_tokens,
        checkpoint_csv=rs2_checkpoints,
        raw_log=rs2_log,
        command="pytest rs2",
    )

    output_tokens = tmp_path / "controlled_tokens.csv"
    output_checkpoints = tmp_path / "controlled_checkpoints.csv"
    output_manifest = tmp_path / "controlled_manifest.json"
    output_report = tmp_path / "controlled.md"
    payload = build(
        baseline_tokens,
        baseline_manifest,
        rs2_tokens,
        rs2_manifest,
        output_tokens,
        output_checkpoints,
        output_manifest,
        output_report,
        execution_command="pytest controlled join",
    )

    assert payload["status"] == "PASS"
    assert payload["trace_identity"]["status"] == "PASS"
    assert VARIANT in payload["configuration"]["variants"]
    with output_tokens.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == config.tokens * 6
    candidate = [row for row in rows if row["variant"] == VARIANT]
    assert len(candidate) == config.tokens
    assert all(row["event_metrics_status"] == "PASS" for row in candidate)
    assert json.loads(output_manifest.read_text(encoding="utf-8"))["status"] == "PASS"

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from scripts.long_sequence_stability import TraceConfiguration
from scripts.write_log_stability import (
    logical_state_bytes,
    run_write_log_trace,
    write_csv,
    write_manifest,
    write_report,
)


def _config(tokens: int) -> TraceConfiguration:
    return TraceConfiguration(
        tokens=tokens,
        checkpoints=tuple(value for value in (4, 8) if value <= tokens),
        seed=0xFB72,
        split="development",
        trace_family="nominal",
        num_value_heads=2,
        num_qk_heads=1,
        key_dim=8,
        value_dim=8,
        activation_block_size=16,
        state_block_size=16,
    )


class TestWriteLogStability(unittest.TestCase):
    def test_trace_is_deterministic_prefix_stable_and_no_drop(self) -> None:
        short = run_write_log_trace(_config(4), capacities=(4, 8))
        long_a = run_write_log_trace(_config(8), capacities=(4, 8))
        long_b = run_write_log_trace(_config(8), capacities=(4, 8))

        self.assertEqual(len(long_a.token_rows), 8 * 3)
        self.assertEqual(len(long_a.checkpoint_rows), 2 * 3)
        self.assertEqual(long_a.token_rows, long_b.token_rows)
        self.assertEqual(long_a.input_stream_sha256, long_b.input_stream_sha256)
        self.assertEqual(short.token_rows, long_a.token_rows[: len(short.token_rows)])
        candidates = [row for row in long_a.token_rows if row["variant"] != "fp32"]
        self.assertTrue(all(int(row["dropped_entries"]) == 0 for row in candidates))

    def test_capacity_controls_fold_schedule(self) -> None:
        result = run_write_log_trace(_config(8), capacities=(4, 8))
        final = {
            str(row["variant"]): row
            for row in result.checkpoint_rows
            if int(row["token_index"]) == 8
        }
        r4 = next(row for name, row in final.items() if name.endswith("_r4"))
        r8 = next(row for name, row in final.items() if name.endswith("_r8"))
        self.assertEqual(int(r4["folds"]), 2)
        self.assertEqual(int(r8["folds"]), 1)
        self.assertEqual(int(r4["live_entries"]), 0)
        self.assertEqual(int(r8["live_entries"]), 0)

    def test_logical_storage_increases_with_capacity(self) -> None:
        config = TraceConfiguration(**{**_config(8).__dict__, "value_dim": 32})
        r4 = logical_state_bytes(config, capacity=4, log_precision="mxfp8_e4m3")
        r8 = logical_state_bytes(config, capacity=8, log_precision="mxfp8_e4m3")
        self.assertGreater(r4, 2 * 8 * 8 * 0.5)
        self.assertGreater(r8, r4)
        stacked = logical_state_bytes(
            config,
            capacity=4,
            log_precision="mxfp8_e4m3",
            base_stack_depth=2,
        )
        self.assertGreater(stacked, r4)
        sparse = logical_state_bytes(
            config,
            capacity=4,
            log_precision="mxfp8_e4m3",
            base_stack_depth=2,
            base_residual_block_fraction=0.5,
        )
        self.assertGreater(sparse, r4)
        self.assertLess(sparse, stacked)

    def test_residual_stack_run_is_labeled_and_deterministic(self) -> None:
        left = run_write_log_trace(
            _config(4),
            capacities=(4,),
            activation_stack_depth=2,
            base_stack_depth=2,
        )
        right = run_write_log_trace(
            _config(4),
            capacities=(4,),
            activation_stack_depth=2,
            base_stack_depth=2,
        )
        variants = {str(row["variant"]) for row in left.token_rows}
        self.assertTrue(
            any("mxfp4_rs2_act_rs2_dense_base" in name for name in variants)
        )
        self.assertEqual(left.token_rows, right.token_rows)

    def test_adaptive_run_is_labeled_and_respects_capacity(self) -> None:
        result = run_write_log_trace(
            _config(8),
            capacities=(8,),
            activation_stack_depth=2,
            base_stack_depth=2,
            fold_policy="decay_threshold",
            adaptive_min_entries=2,
            fold_decay_threshold=0.99,
        )
        candidates = [row for row in result.token_rows if row["variant"] != "fp32"]
        self.assertTrue(all("adaptive_decay990" in str(row["variant"]) for row in candidates))
        self.assertTrue(all(0 <= int(row["live_entries"]) < 8 for row in candidates))
        self.assertTrue(all(int(row["dropped_entries"]) == 0 for row in candidates))

    def test_zero_state_and_new_trace_families_are_deterministic(self) -> None:
        hashes = set()
        for family in ("decay_sweep", "adversarial"):
            config = TraceConfiguration(**{**_config(4).__dict__, "trace_family": family})
            left = run_write_log_trace(
                config, capacities=(4,), initial_state_mode="zero"
            )
            right = run_write_log_trace(
                config, capacities=(4,), initial_state_mode="zero"
            )
            self.assertEqual(left.token_rows, right.token_rows)
            self.assertEqual(left.input_stream_sha256, right.input_stream_sha256)
            hashes.add(left.input_stream_sha256)
        self.assertEqual(len(hashes), 2)

    def test_outputs_manifest_and_report_are_written(self) -> None:
        result = run_write_log_trace(_config(4), capacities=(4,))
        tmp = Path.cwd() / "build" / "test_write_log_trace"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            token_csv = tmp / "tokens.csv"
            checkpoint_csv = tmp / "checkpoints.csv"
            manifest = tmp / "manifest.json"
            report = tmp / "report.md"
            write_csv(token_csv, result.token_rows)
            write_csv(checkpoint_csv, result.checkpoint_rows)
            write_manifest(
                manifest,
                result=result,
                token_csv=token_csv,
                checkpoint_csv=checkpoint_csv,
            )
            write_report(
                report,
                result=result,
                token_csv=token_csv,
                checkpoint_csv=checkpoint_csv,
                manifest=manifest,
            )
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "diagnostic_only")
            self.assertEqual(payload["input_stream_sha256"], result.input_stream_sha256)
            self.assertIn("Engineering gate", report.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

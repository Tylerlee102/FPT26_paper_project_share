from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from scripts.e2m0_residual_stability import (
    logical_e2m0_state_bytes,
    run_e2m0_trace,
    write_csv,
    write_manifest,
)
from scripts.long_sequence_stability import TraceConfiguration
from scripts.verify_e2m0_residual_stability import verify


def _config(tokens: int = 8) -> TraceConfiguration:
    return TraceConfiguration(
        tokens=tokens,
        checkpoints=(4, 8),
        seed=0xFB72,
        split="development",
        trace_family="high_retention",
        num_value_heads=2,
        num_qk_heads=1,
        key_dim=8,
        value_dim=32,
        activation_block_size=16,
        state_block_size=16,
    )


class TestE2M0ResidualStability(unittest.TestCase):
    def test_full_dimension_storage_matches_registered_budget(self) -> None:
        config = TraceConfiguration(
            **{
                **_config().__dict__,
                "num_value_heads": 32,
                "num_qk_heads": 16,
                "key_dim": 128,
                "value_dim": 128,
                "activation_block_size": 32,
                "state_block_size": 32,
            }
        )
        self.assertEqual(
            logical_e2m0_state_bytes(config, capacity=7, base_stack_depth=2),
            538_256,
        )
        self.assertEqual(
            logical_e2m0_state_bytes(
                config,
                capacity=7,
                base_stack_depth=2,
                log_mode="mxfp8_e4m3",
            ),
            536_912,
        )
        self.assertLess(538_256, 540_672)

    def test_trace_is_deterministic_and_prefix_complete(self) -> None:
        left = run_e2m0_trace(_config())
        right = run_e2m0_trace(_config())
        self.assertEqual(left.token_rows, right.token_rows)
        self.assertEqual(left.input_stream_sha256, right.input_stream_sha256)
        self.assertEqual(len(left.token_rows), 16)
        candidates = [row for row in left.token_rows if row["variant"] != "fp32"]
        self.assertTrue(all(int(row["dropped_entries"]) == 0 for row in candidates))

    def test_manifest_and_independent_verifier(self) -> None:
        result = run_e2m0_trace(_config())
        tmp = Path.cwd() / "build" / "test_e2m0_residual"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            token_csv = tmp / "tokens.csv"
            checkpoint_csv = tmp / "checkpoints.csv"
            manifest = tmp / "manifest.json"
            write_csv(token_csv, result.token_rows)
            write_csv(checkpoint_csv, result.checkpoint_rows)
            write_manifest(
                manifest,
                result=result,
                token_csv=token_csv,
                checkpoint_csv=checkpoint_csv,
            )
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["base_residual_element_bits"], 3)
            verification = verify(manifest)
            self.assertEqual(verification["status"], "PASS", verification["failures"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

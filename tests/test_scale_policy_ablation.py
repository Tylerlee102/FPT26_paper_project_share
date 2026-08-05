from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts.long_sequence_stability import TraceConfiguration, run_long_trace
from scripts.scale_policy_ablation import (
    POLICIES,
    run_scale_policy_ablation,
    write_csv,
    write_manifest,
    write_report,
)


ROOT = Path(__file__).resolve().parents[1]


def _config(tokens: int = 8) -> TraceConfiguration:
    return TraceConfiguration(
        tokens=tokens,
        checkpoints=(4, 8),
        seed=0xFB72,
        split="development",
        trace_family="nominal",
        num_value_heads=2,
        num_qk_heads=1,
        key_dim=4,
        value_dim=4,
        activation_block_size=16,
        state_block_size=16,
    )


class TestScalePolicyAblation(unittest.TestCase):
    def test_all_frozen_policies_emit_every_token_and_checkpoint(self) -> None:
        result = run_scale_policy_ablation(_config())

        self.assertEqual(len(result.token_rows), 8 * len(POLICIES))
        self.assertEqual(len(result.checkpoint_rows), 2 * len(POLICIES))
        self.assertEqual(
            {row["variant"] for row in result.token_rows},
            {policy.variant for policy in POLICIES},
        )
        self.assertEqual(len(result.input_sha256), 64)
        self.assertEqual(len(result.initial_state_sha256), 64)
        self.assertGreater(result.initial_scale_blocks, 0)

    def test_every_token_policy_matches_main_long_trace_metrics(self) -> None:
        config = _config(4)
        scale_result = run_scale_policy_ablation(config)
        main_result = run_long_trace(config)
        scale_rows = {
            int(row["token_index"]): row
            for row in scale_result.token_rows
            if row["variant"] == "mxfp4_scale_every_token"
        }
        main_rows = {
            int(row["token_index"]): row
            for row in main_result.token_rows
            if row["variant"] == "mxfp4_qdq_act_b16_state_b16"
        }

        self.assertEqual(scale_rows.keys(), main_rows.keys())
        for token_index in scale_rows:
            for metric in (
                "output_cosine_fp32",
                "output_rel_l2",
                "output_max_abs",
                "state_rel_l2",
                "state_max_abs",
            ):
                self.assertEqual(scale_rows[token_index][metric], main_rows[token_index][metric])

    def test_outputs_and_manifest_are_hashed(self) -> None:
        result = run_scale_policy_ablation(_config(4))
        output = ROOT / "build" / "tests" / "scale_policy"
        token_csv = output / "tokens.csv"
        checkpoint_csv = output / "checkpoints.csv"
        report = output / "report.md"
        manifest_path = output / "manifest.json"
        write_csv(token_csv, result.token_rows)
        write_csv(checkpoint_csv, result.checkpoint_rows)
        write_report(report, result)
        write_manifest(manifest_path, result, token_csv, checkpoint_csv, report)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "PASS")
        self.assertEqual(
            manifest["evidence_scope"],
            "synthetic_floating_qdq_scale_policy_diagnostic",
        )
        self.assertEqual(manifest["input_sha256"], result.input_sha256)
        self.assertEqual(manifest["initial_state_sha256"], result.initial_state_sha256)
        self.assertEqual(len(manifest["source_identity"]["dirty_patch"]["sha256"]), 64)
        for path in (token_csv, checkpoint_csv, report):
            relative = path.relative_to(ROOT).as_posix()
            self.assertEqual(
                manifest["outputs"][relative],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()

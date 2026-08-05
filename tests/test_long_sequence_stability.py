from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from scripts.long_sequence_stability import (
    TraceConfiguration,
    run_long_trace,
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


class TestLongSequenceStability(unittest.TestCase):
    def test_trace_has_all_variants_and_checkpoints(self) -> None:
        result = run_long_trace(_config(8))

        self.assertEqual(len(result.token_rows), 8 * 5)
        self.assertEqual(len(result.checkpoint_rows), 2 * 5)
        self.assertEqual(
            {str(row["variant"]) for row in result.token_rows},
            {
                "fp32",
                "bf16_qdq_fp32_accum_state_bf16",
                "mxfp4_qdq_act_b16_state_b16",
                "mxfp4_qdq_act_b16_mxfp8_e4m3_state_b16",
                "flat_int4_qdq",
            },
        )
        self.assertEqual(
            {int(row["token_index"]) for row in result.checkpoint_rows},
            {4, 8},
        )

    def test_trace_is_deterministic_and_prefix_stable(self) -> None:
        short = run_long_trace(_config(4))
        long_a = run_long_trace(_config(8))
        long_b = run_long_trace(_config(8))

        self.assertEqual(long_a.token_rows, long_b.token_rows)
        self.assertEqual(short.token_rows, long_a.token_rows[: len(short.token_rows)])

    def test_fp32_rows_are_exact_and_qdq_events_remain_explicitly_not_run(self) -> None:
        result = run_long_trace(_config(4))
        fp32_rows = [row for row in result.token_rows if row["variant"] == "fp32"]
        qdq_rows = [row for row in result.token_rows if row["variant"] != "fp32"]

        for row in fp32_rows:
            self.assertEqual(float(row["output_cosine_fp32"]), 1.0)
            self.assertEqual(float(row["state_rel_l2"]), 0.0)
            self.assertEqual(row["event_metrics_status"], "PASS")
        for row in qdq_rows:
            self.assertEqual(row["event_metrics_status"], "NOT_RUN")
            self.assertEqual(row["element_saturations"], "")

    def test_outputs_and_manifest_are_written_with_hashes(self) -> None:
        result = run_long_trace(_config(4))
        tmp = Path.cwd() / "build" / "test_long_trace"
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
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(
                payload["evidence_scope"], "synthetic_floating_qdq_diagnostic"
            )
            self.assertEqual(len(payload["outputs"]), 2)
            self.assertEqual(payload["input_sha256"], result.input_sha256)
            self.assertEqual(len(payload["source_identity"]["dirty_patch"]["sha256"]), 64)
            self.assertIn("PASS", report.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_invalid_head_ratio_is_rejected(self) -> None:
        config = TraceConfiguration(
            **{**_config(4).__dict__, "num_value_heads": 3, "num_qk_heads": 2}
        )

        with self.assertRaisesRegex(ValueError, "must be divisible"):
            run_long_trace(config)


if __name__ == "__main__":
    unittest.main()

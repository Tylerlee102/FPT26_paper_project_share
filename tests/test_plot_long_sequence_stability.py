from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from scripts.long_sequence_stability import TraceConfiguration, run_long_trace, write_csv
from scripts.plot_long_sequence_stability import (
    COLORS,
    VARIANT_ORDER,
    _variant_color,
    _variant_dash,
    generate_plots,
)
from scripts.plot_long_sequence_stability import DEFAULT_MANIFEST


def test_variant_colors_do_not_shift_when_fp32_is_omitted() -> None:
    assert _variant_color("bf16_qdq_fp32_accum_state_bf16", 0) == COLORS[1]
    assert _variant_color("mxfp4_qdq_act_b32_state_b32", 1) == COLORS[2]
    assert _variant_color("flat_int4_qdq", 3) == COLORS[4]
    assert _variant_color("native_mxfp4_encoded_act_b32_state_b32", 4) == COLORS[5]


def test_variant_dash_patterns_are_stable_and_grayscale_distinct() -> None:
    patterns = [_variant_dash(variant) for variant in VARIANT_ORDER]
    assert len(set(patterns)) == len(patterns)
    assert _variant_dash("fp32") == ()


def test_current_plot_manifest_includes_verified_native_trace() -> None:
    payload = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["evidence_scope"] == (
        "synthetic_floating_qdq_and_native_encoded_figures"
    )
    assert "native_mxfp4_encoded_act_b32_state_b32" in payload["configuration"][
        "variants"
    ]
    assert payload["encoded_input"] is not None
    assert payload["encoded_upstream_manifest"] is not None


class TestPlotLongSequenceStability(unittest.TestCase):
    def test_generates_two_vector_pdfs_and_manifest(self) -> None:
        config = TraceConfiguration(
            tokens=8,
            checkpoints=(4, 8),
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
        result = run_long_trace(config)
        tmp = Path.cwd() / "build" / "test_long_trace_plots"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            csv_path = tmp / "tokens.csv"
            cosine = tmp / "cosine.pdf"
            state = tmp / "state.pdf"
            manifest = tmp / "manifest.json"
            write_csv(csv_path, result.token_rows)
            generate_plots(csv_path, cosine, state, manifest)

            self.assertTrue(cosine.read_bytes().startswith(b"%PDF"))
            self.assertTrue(state.read_bytes().startswith(b"%PDF"))
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(
                payload["evidence_scope"], "synthetic_floating_qdq_figures"
            )
            self.assertEqual(payload["configuration"]["state_orientation"], "KxV")
            self.assertIn("max(||reference||2", payload["metric_contract"]["state_relative_l2"])
            self.assertEqual(payload["execution"]["exit_code"], 0)
            self.assertEqual(len(payload["source_identity"]["dirty_patch"]["sha256"]), 64)
            self.assertEqual(len(payload["outputs"]), 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

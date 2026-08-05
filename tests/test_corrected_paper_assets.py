import hashlib
import json
from pathlib import Path

import scripts.corrected_paper_assets as paper_assets
from scripts.corrected_paper_assets import generate


def test_corrected_paper_assets_are_evidence_backed_and_release_neutral(
    tmp_path: Path,
) -> None:
    manifest = generate(tmp_path)
    assert manifest["status"] == "PASS"
    assert "paper_pdf_permitted" not in manifest
    assert manifest["source_identity"]["git_revision"] == manifest["source_revision"]
    dirty_patch = manifest["source_identity"]["dirty_patch"]
    assert len(dirty_patch["sha256"]) == 64
    assert dirty_patch["bytes"] >= 0
    if dirty_patch["bytes"] == 0:
        assert dirty_patch["sha256"] == hashlib.sha256(b"").hexdigest().upper()
    numbers = json.loads((tmp_path / "numbers.json").read_text())
    provenance = json.loads((tmp_path / "provenance.json").read_text())
    assert set(numbers) == set(provenance)
    assert numbers["bf16_token_8192_output_cosine"]["value"] > 0.999
    assert numbers["qdq_mxfp4_token_8192_output_cosine"]["value"] < 0.8
    assert numbers["native_encoded_mxfp4_token_8192_output_cosine"]["value"] < 0.5
    assert numbers["native_encoded_mxfp4_token_8192_state_relative_l2"]["value"] > 2.5
    assert (
        numbers["native_encoded_mxfp4_token_8192_output_cosine"]["source"]
        == "reports/benchmark/corrected/native_encoded_long_trace_checkpoints.csv"
    )
    assert numbers["corrected_candidate_hls_cost_advantage"]["value"] == "FAIL"
    assert numbers["corrected_candidate_rtl_64_token"]["value"] == "NOT_ESTABLISHED"
    assert numbers["synthetic_nominal_alpha_minimum"]["value"] == 0.95
    assert numbers["synthetic_high_retention_beta_minimum"]["value"] == 0.85
    assert numbers["mxfp4_logical_bits_per_value"]["value"] == 4.25
    assert numbers["corrected_e2m0_residual_bits"]["value"] == 3
    assert numbers["corrected_residual_stack_terms"]["value"] == 2
    assert numbers["corrected_candidate_hls_tool_version"]["value"] == "2025.2"
    assert numbers["corrected_configured_hls_timing_margin_status"]["value"] == "FAIL"
    assert numbers["corrected_effective_hls_timing_budget_ns"]["value"] == 2.92
    assert numbers["corrected_correction_machinery_lut"]["value"] == 342492
    assert numbers["corrected_state_l2_sensitivity_probe"]["value"] == 0.09
    assert numbers["corrected_heldout_state_l2_probe_status"]["value"] == "FAIL"
    assert numbers["corrected_extended_state_l2_probe_status"]["value"] == "FAIL"
    assert numbers["corrected_postroute_physical_fit"]["value"] == "PASS"
    assert numbers["corrected_postroute_250mhz_status"]["value"] == "FAIL"
    assert numbers["corrected_postroute_250mhz_wns_ns"]["value"] == -1.54
    assert numbers["corrected_postroute_first_closing_frequency_mhz"][
        "value"
    ] > 180.0
    assert numbers["corrected_postroute_uram_used"]["value"] == 624
    assert numbers["corrected_postroute_power_total_w"]["value"] == 6.991
    assert numbers["corrected_postroute_energy_per_token_status"][
        "value"
    ] == "NOT_RUN"
    assert numbers["mxfp8_postroute_physical_fit"]["value"] == "PASS"
    assert numbers["mxfp8_postroute_250mhz_status"]["value"] == "FAIL"
    assert numbers["mxfp8_postroute_250mhz_wns_ns"]["value"] == -1.355
    assert numbers["mxfp8_postroute_first_closing_frequency_mhz"][
        "value"
    ] == 1000.0 / 6.0
    assert numbers["mxfp8_postroute_lut_used"]["value"] == 58_582
    assert numbers["mxfp8_postroute_uram_used"]["value"] == 576
    assert numbers["mxfp8_postroute_power_total_w"]["value"] == 4.952
    assert numbers["corrected_e2m0_control_cosim_status"]["value"] == "PASS"
    assert numbers["corrected_e2m0_control_cosim_commands"]["value"] == 2
    assert numbers["corrected_e2m0_control_cosim_recurrent_transition"][
        "value"
    ] is False
    assert numbers["corrected_e2m0_rtl_64_token_status"]["value"] == "NOT_ESTABLISHED"
    assert numbers["corrected_e2m0_rtl_trace_tokens"]["value"] == 64
    assert numbers["corrected_e2m0_rtl_transactions"]["value"] == 1
    assert numbers["corrected_e2m0_rtl_output_values_compared"]["value"] == 0
    assert numbers["corrected_e2m0_hls_csim_64_token_status"]["value"] == "PASS"
    assert numbers["corrected_e2m0_rtl_direct_load_status"]["value"] == "PASS"
    assert numbers["corrected_e2m0_rtl_direct_load_cycles"]["value"] == 4_797_322
    assert numbers["corrected_e2m0_rtl_completed_recurrent_steps"]["value"] == 0
    assert numbers["qwen_capture_layer_input_elements"]["value"] == 147_456
    assert numbers["qwen_capture_layer_input_abs_max"]["value"] == 51.25
    assert numbers["qwen_capture_recurrence_complete"]["value"] is False
    assert numbers["synthetic_relative_l2_denominator_floor"]["value"] == 1e-12
    assert numbers["bf16_all_layer_logical_state_mib"]["value"] == 36.0
    assert numbers["uniform_mxfp4_all_layer_logical_state_mib"]["value"] == 9.5625
    assert numbers["bf16_ideal_min_uram_for_mantissas"]["value"] == 1024
    assert numbers["u55c_available_uram"]["value"] == 960
    assert numbers["physical_all_layer_state_bank_fit"]["value"] == "NOT_RUN"
    assert numbers["bf16_step_input_logical_bytes"]["value"] == 16512
    assert numbers["uniform_mxfp4_step_input_logical_bytes"]["value"] == 4480
    assert numbers["corrected_candidate_step_input_logical_bytes"]["value"] == 8832
    assert numbers["native_expanded_integer_output_logical_bytes"]["value"] == 24576
    assert numbers["stress_dynamic_range_bf16_full_trace_threshold_status"][
        "value"
    ] == "PASS"
    assert numbers["stress_dynamic_range_qdq_mxfp4_final_output_cosine"][
        "value"
    ] < 0.5
    assert numbers["stress_dynamic_range_mxfp8_state_final_output_cosine"][
        "value"
    ] > numbers["stress_dynamic_range_qdq_mxfp4_final_output_cosine"]["value"]
    assert numbers["stress_cancellation_mxfp8_state_final_output_cosine"][
        "value"
    ] > 0.99
    assert numbers["stress_cancellation_mxfp8_state_final_state_relative_l2"][
        "value"
    ] > 0.10
    assert numbers["stress_cancellation_mxfp8_state_full_trace_threshold_status"][
        "value"
    ] == "FAIL"
    long_table = (tmp_path / "tables" / "long_sequence.tex").read_text(
        encoding="utf-8"
    )
    assert "0.99996" in long_table
    assert "Rel. $L_2$" in long_table
    assert "MXFP4 floating Q/DQ" in long_table
    assert "Native encoded MXFP4" in long_table
    assert "MXFP4 Q/DQ + MXFP8-E4M3 state" in long_table
    hls_table = (tmp_path / "tables" / "controlled_hls.tex").read_text(
        encoding="utf-8"
    )
    assert "BRAM" not in hls_table
    assert "URAM" not in hls_table
    assert "Native encoded MXFP4" in hls_table
    assert "docs/synthetic_trace_protocol.json" in manifest["inputs_sha256"]
    assert (
        "reports/benchmark/corrected/state_capacity_lower_bound.json"
        in manifest["inputs_sha256"]
    )
    assert (
        "reports/benchmark/corrected/stress/long_trace_stress_summary.csv"
        in manifest["inputs_sha256"]
    )
    assert (
        "reports/benchmark/corrected/stress/long_trace_stress_summary_manifest.json"
        in manifest["inputs_sha256"]
    )
    assert (
        "reports/vivado/corrected/e2m0/e2m0_postroute_summary.json"
        in manifest["inputs_sha256"]
    )
    assert (
        "reports/vivado/baselines/mxfp8/mxfp8_vivado_summary.json"
        in manifest["inputs_sha256"]
    )
    assert (
        "reports/cosim/corrected/e2m0_control_smoke/e2m0_control_smoke_summary.json"
        in manifest["inputs_sha256"]
    )
    assert (
        "reports/cosim/corrected/e2m0_trace64/e2m0_trace64_cosim_summary.json"
        in manifest["inputs_sha256"]
    )
    assert (
        "reports/golden/qwen_capture_characterization.json"
        in manifest["inputs_sha256"]
    )
    assert (
        "paper/figures/corrected/tradeoff_evidence.pdf"
        in manifest["verified_figure_sha256"]
    )
    assert "final_paper_pdf_permitted" not in numbers
    for entry in numbers.values():
        assert entry["source_line"] > 0
        assert entry["source"]
        assert entry["git_sha"]
    for name in (
        "long_sequence.tex",
        "controlled_hls.tex",
        "mitigation_hls.tex",
        "resource_ablation.tex",
        "corrected_heldout.tex",
        "corrected_extended.tex",
        "corrected_quality.tex",
        "scale_policy.tex",
        "postroute_evidence.tex",
    ):
        assert (tmp_path / "tables" / name).exists()


def test_corrected_paper_manifest_excludes_unmanaged_output_files(
    tmp_path: Path,
) -> None:
    output = tmp_path / "future_assets"
    output.mkdir()
    unrelated = output / "paper_audit_candidate.pdf"
    unrelated.write_bytes(b"%PDF-unmanaged")

    manifest = generate(output)

    assert all(
        not path.endswith("paper_audit_candidate.pdf")
        for path in manifest["outputs_sha256"]
    )


def test_corrected_paper_assets_report_a_replayed_extended_quality_failure(
    tmp_path: Path, monkeypatch
) -> None:
    extended = tmp_path / "extended_summary.json"
    extended.write_text(
        json.dumps(
            {
                "status": "FAIL",
                "full_deterministic_recompute": "PASS",
                "run_count": 2,
                "recomputed_run_count": 2,
                "minimum_checkpoint_output_cosine": 0.97,
                "maximum_final_state_relative_l2": 0.12,
                "minimum_all_token_output_cosine": 0.96,
                "maximum_all_token_state_relative_l2": 0.13,
                "maximum_all_token_state_abs_error": 0.25,
                "total_element_saturations": 0,
                "total_accumulator_saturations": 0,
                "total_scale_clamps": 0,
                "total_alignment_underflows": 123,
                "total_e2m0_residual_clips": 45,
                "total_folds": 2,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(paper_assets, "EXTENDED", extended)

    output = tmp_path / "failed_quality_assets"
    manifest = paper_assets.generate(output)
    numbers = json.loads((output / "numbers.json").read_text(encoding="utf-8"))

    assert manifest["extended_8192_status"] == "FAIL"
    assert manifest["extended_8192_replay_status"] == "PASS"
    assert numbers["corrected_extended_quality_status"]["value"] == "FAIL"
    assert numbers["corrected_extended_minimum_checkpoint_output_cosine"][
        "value"
    ] == 0.97
    assert numbers["corrected_extended_total_alignment_underflows"]["value"] == 123
    assert numbers["corrected_extended_total_folds"]["value"] == 2
    assert numbers["corrected_extended_run_count"]["value"] == 2
    assert numbers["corrected_extended_recomputed_run_count"]["value"] == 2
    assert numbers["corrected_target_loop_ii"]["value"] == 1
    assert numbers["corrected_failed_loop_final_ii"]["value"] == 2
    table = (output / "tables" / "corrected_extended.tex").read_text(
        encoding="utf-8"
    )
    assert "Update-log folds & 2" in table
    quality = (output / "tables" / "corrected_quality.tex").read_text(
        encoding="utf-8"
    )
    assert "Log folds & -- & 2" in quality

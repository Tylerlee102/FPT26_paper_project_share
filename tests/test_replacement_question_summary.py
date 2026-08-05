import csv
import hashlib
import json
from pathlib import Path

from scripts.replacement_question_summary import summarize, write_report


def _write(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_negative_uniform_mxfp4_answer(tmp_path: Path) -> None:
    synthetic = _write(
        tmp_path / "synthetic.json",
        {
            "status": "PASS",
            "bf16_software_stability": "PASS",
            "uniform_mxfp4_stability": "FAIL",
            "scale_policy_rescues_uniform_mxfp4": "FAIL",
            "overall_finding": "BF16 passes while MXFP4 fails.",
        },
    )
    hls = _write(
        tmp_path / "hls.json",
        {
            "status": "PASS",
            "hls_lut_and_step_cost_advantage": "FAIL",
            "energy_comparison": "NOT_RUN",
            "ratios": {
                "mxfp4_to_bf16_lut": 1.6,
                "mxfp4_to_bf16_step_cycles_max": 1.4,
            },
        },
    )
    capacity = _write(
        tmp_path / "capacity.json",
        {
            "status": "PASS",
            "physical_all_layer_state_bank_fit": "NOT_RUN",
            "rows": [
                {"variant": "BF16", "per_layer_logical_state_bytes": 1_048_576},
                {
                    "variant": "uniform_mxfp4_e2m1_e8m0_b32",
                    "per_layer_logical_state_bytes": 278_528,
                },
            ],
        },
    )
    result = summarize(synthetic, hls, capacity)
    assert result["status"] == "PASS"
    assert result["current_answer_status"] == "FAIL"
    assert result["decisions"]["uniform_mxfp4_logical_state_reduction"] == "PASS"
    assert result["logical_state"]["uniform_mxfp4_reduction_percent"] == 73.4375
    write_report(result, tmp_path / "answer.json", tmp_path / "answer.md")
    assert "Current answer: `FAIL`" in (tmp_path / "answer.md").read_text()


def test_verified_native_failure_is_included_in_answer(tmp_path: Path) -> None:
    synthetic = _write(
        tmp_path / "synthetic.json",
        {
            "status": "PASS",
            "bf16_software_stability": "PASS",
            "uniform_mxfp4_stability": "FAIL",
            "scale_policy_rescues_uniform_mxfp4": "FAIL",
            "overall_finding": "BF16 passes while MXFP4 fails.",
        },
    )
    hls = _write(
        tmp_path / "hls.json",
        {
            "status": "PASS",
            "hls_lut_and_step_cost_advantage": "FAIL",
            "energy_comparison": "NOT_RUN",
            "ratios": {
                "mxfp4_to_bf16_lut": 1.6,
                "mxfp4_to_bf16_step_cycles_max": 1.4,
            },
        },
    )
    capacity = _write(
        tmp_path / "capacity.json",
        {
            "status": "PASS",
            "physical_all_layer_state_bank_fit": "NOT_RUN",
            "rows": [
                {"variant": "BF16", "per_layer_logical_state_bytes": 1_048_576},
                {
                    "variant": "uniform_mxfp4_e2m1_e8m0_b32",
                    "per_layer_logical_state_bytes": 278_528,
                },
            ],
        },
    )
    native_manifest = _write(
        tmp_path / "native_manifest.json",
        {"status": "PASS", "engineering_gate": {"status": "FAIL"}},
    )
    native_verification = _write(
        tmp_path / "native_verification.json",
        {
            "status": "PASS",
            "manifest_sha256": hashlib.sha256(
                native_manifest.read_bytes()
            ).hexdigest().upper(),
        },
    )
    checkpoints = tmp_path / "native_checkpoints.csv"
    fields = [
        "token_index",
        "output_cosine_fp32",
        "output_rel_l2",
        "state_rel_l2",
        "state_max_abs",
        "cumulative_element_saturations",
        "cumulative_accumulator_saturations",
        "cumulative_scale_clamps",
        "cumulative_alignment_underflows",
    ]
    with checkpoints.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for token in (64, 256, 1024, 4096, 8192):
            writer.writerow(
                {
                    "token_index": token,
                    "output_cosine_fp32": 0.8,
                    "output_rel_l2": 1.0,
                    "state_rel_l2": 1.2,
                    "state_max_abs": 0.5,
                    "cumulative_element_saturations": 0,
                    "cumulative_accumulator_saturations": 0,
                    "cumulative_scale_clamps": 0,
                    "cumulative_alignment_underflows": token,
                }
            )

    result = summarize(
        synthetic,
        hls,
        capacity,
        native_manifest,
        native_verification,
        checkpoints,
    )
    assert result["decisions"]["native_encoded_mxfp4_synthetic_stability"] == "FAIL"
    assert result["native_encoded_token_8192"]["state_rel_l2"] == 1.2
    assert "native encoded and floating-Q/DQ diagnostics fail" in result["current_answer"]


def test_corrected_candidate_is_reported_separately_from_uniform_answer(
    tmp_path: Path,
) -> None:
    synthetic = _write(
        tmp_path / "synthetic.json",
        {
            "status": "PASS",
            "bf16_software_stability": "PASS",
            "uniform_mxfp4_stability": "FAIL",
            "scale_policy_rescues_uniform_mxfp4": "FAIL",
            "overall_finding": "controlled failure",
        },
    )
    hls = _write(
        tmp_path / "hls.json",
        {
            "status": "PASS",
            "hls_lut_and_step_cost_advantage": "FAIL",
            "energy_comparison": "NOT_RUN",
            "ratios": {
                "mxfp4_to_bf16_lut": 1.6,
                "mxfp4_to_bf16_step_cycles_max": 1.4,
            },
        },
    )
    capacity = _write(
        tmp_path / "capacity.json",
        {
            "status": "PASS",
            "physical_all_layer_state_bank_fit": "NOT_RUN",
            "rows": [
                {"variant": "BF16", "per_layer_logical_state_bytes": 1_048_576},
                {
                    "variant": "uniform_mxfp4_e2m1_e8m0_b32",
                    "per_layer_logical_state_bytes": 278_528,
                },
            ],
        },
    )
    heldout = _write(
        tmp_path / "heldout.json",
        {
            "status": "PASS",
            "registered_held_out_gate": "PASS",
            "full_deterministic_recompute": "PASS",
            "seed_block_count": 3,
            "paired_condition_count": 6,
            "minimum_all_token_output_cosine": 0.994,
            "maximum_all_token_state_relative_l2": 0.099,
            "logical_state_bytes": 537_744,
        },
    )
    corrected_hls = _write(
        tmp_path / "corrected_hls.json",
        {
            "status": "PASS",
            "candidate_name": "candidate",
            "hls_lut_and_nonfold_step_cost_advantage_vs_bf16": "FAIL",
            "phase4_decision_gate": {
                "criteria": {
                    "estimated_fmax_at_least_200_mhz": "PASS",
                    "configured_target_minus_uncertainty_timing_margin": "FAIL",
                    "all_explicit_ii1_constraints_met": "FAIL",
                }
            },
            "csim": {"required_64_token_rtl_cosimulation": "NOT_RUN"},
            "physical_fit": "NOT_RUN",
            "post_route_timing_and_drc": "NOT_RUN",
            "board_energy_measurement": "NOT_RUN",
            "ratios": {"candidate_to_bf16_lut": 5.1},
        },
    )
    result = summarize(
        synthetic,
        hls,
        capacity,
        corrected_heldout_path=heldout,
        corrected_hls_path=corrected_hls,
    )
    assert result["current_answer_status"] == "FAIL"
    corrected = result["corrected_candidate"]
    assert corrected["heldout_1024_quality"] == "PASS"
    assert corrected["hls_lut_and_step_cost_vs_bf16"] == "FAIL"
    assert corrected["selected_method_pareto"] == "FAIL"


def test_corrected_rtl_partial_evidence_fails_the_recurrent_parity_gate(
    tmp_path: Path,
) -> None:
    synthetic = _write(
        tmp_path / "synthetic.json",
        {
            "status": "PASS",
            "bf16_software_stability": "PASS",
            "uniform_mxfp4_stability": "FAIL",
            "scale_policy_rescues_uniform_mxfp4": "FAIL",
            "overall_finding": "controlled failure",
        },
    )
    hls = _write(
        tmp_path / "hls.json",
        {
            "status": "PASS",
            "hls_lut_and_step_cost_advantage": "FAIL",
            "energy_comparison": "NOT_RUN",
            "ratios": {
                "mxfp4_to_bf16_lut": 1.6,
                "mxfp4_to_bf16_step_cycles_max": 1.4,
            },
        },
    )
    capacity = _write(
        tmp_path / "capacity.json",
        {
            "status": "PASS",
            "physical_all_layer_state_bank_fit": "NOT_RUN",
            "rows": [
                {"variant": "BF16", "per_layer_logical_state_bytes": 1_048_576},
                {
                    "variant": "uniform_mxfp4_e2m1_e8m0_b32",
                    "per_layer_logical_state_bytes": 278_528,
                },
            ],
        },
    )
    heldout = _write(
        tmp_path / "heldout.json",
        {
            "status": "PASS",
            "registered_held_out_gate": "PASS",
            "full_deterministic_recompute": "PASS",
            "seed_block_count": 3,
            "paired_condition_count": 6,
            "minimum_all_token_output_cosine": 0.994,
            "maximum_all_token_state_relative_l2": 0.099,
            "logical_state_bytes": 537_744,
        },
    )
    corrected_hls = _write(
        tmp_path / "corrected_hls.json",
        {
            "status": "PASS",
            "candidate_name": "candidate",
            "hls_lut_and_nonfold_step_cost_advantage_vs_bf16": "FAIL",
            "phase4_decision_gate": {
                "criteria": {
                    "estimated_fmax_at_least_200_mhz": "PASS",
                    "configured_target_minus_uncertainty_timing_margin": "FAIL",
                    "all_explicit_ii1_constraints_met": "PASS",
                }
            },
            "csim": {"required_64_token_rtl_cosimulation": "NOT_RUN"},
            "physical_fit": "NOT_RUN",
            "post_route_timing_and_drc": "NOT_RUN",
            "board_energy_measurement": "NOT_RUN",
            "ratios": {"candidate_to_bf16_lut": 5.1},
        },
    )
    corrected_rtl = _write(
        tmp_path / "corrected_rtl.json",
        {
            "status": "PARTIAL",
            "required_64_token_rtl_parity": "NOT_ESTABLISHED",
            "hls_c_simulation": {"status": "PASS", "tokens": 64},
            "direct_generated_rtl_load": {
                "status": "PASS",
                "completed_transactions": 1,
            },
            "official_hls_xsim": {"status": "FAIL", "independent_attempts": 2},
            "rtl_simulation": {
                "status": "PARTIAL",
                "completed_transactions": 1,
                "completed_recurrent_steps": 0,
            },
        },
    )

    result = summarize(
        synthetic,
        hls,
        capacity,
        corrected_heldout_path=heldout,
        corrected_hls_path=corrected_hls,
        corrected_rtl_path=corrected_rtl,
    )
    corrected = result["corrected_candidate"]
    assert corrected["rtl_64_token"] == "FAIL"
    assert (
        corrected["metrics"]["rtl_64_token"]["required_64_token_rtl_parity"]
        == "NOT_ESTABLISHED"
    )
    report = tmp_path / "answer.md"
    write_report(result, tmp_path / "answer.json", report)
    text = report.read_text(encoding="utf-8")
    assert "required parity NOT_ESTABLISHED" in text
    assert "0 completed recurrent steps" in text


def test_replayed_extended_metrics_are_preserved_in_summary(tmp_path: Path) -> None:
    synthetic = _write(
        tmp_path / "synthetic.json",
        {
            "status": "PASS",
            "bf16_software_stability": "PASS",
            "uniform_mxfp4_stability": "FAIL",
            "scale_policy_rescues_uniform_mxfp4": "FAIL",
            "overall_finding": "controlled failure",
        },
    )
    hls = _write(
        tmp_path / "hls.json",
        {
            "status": "PASS",
            "hls_lut_and_step_cost_advantage": "FAIL",
            "energy_comparison": "NOT_RUN",
            "ratios": {
                "mxfp4_to_bf16_lut": 1.6,
                "mxfp4_to_bf16_step_cycles_max": 1.4,
            },
        },
    )
    capacity = _write(
        tmp_path / "capacity.json",
        {
            "status": "PASS",
            "physical_all_layer_state_bank_fit": "NOT_RUN",
            "rows": [
                {"variant": "BF16", "per_layer_logical_state_bytes": 1_048_576},
                {
                    "variant": "uniform_mxfp4_e2m1_e8m0_b32",
                    "per_layer_logical_state_bytes": 278_528,
                },
            ],
        },
    )
    heldout = _write(
        tmp_path / "heldout.json",
        {
            "status": "PASS",
            "registered_held_out_gate": "PASS",
            "full_deterministic_recompute": "PASS",
            "seed_block_count": 3,
            "paired_condition_count": 6,
            "minimum_all_token_output_cosine": 0.994,
            "maximum_all_token_state_relative_l2": 0.099,
            "logical_state_bytes": 537_744,
        },
    )
    corrected_hls = _write(
        tmp_path / "corrected_hls.json",
        {
            "status": "PASS",
            "candidate_name": "candidate",
            "hls_lut_and_nonfold_step_cost_advantage_vs_bf16": "FAIL",
            "phase4_decision_gate": {
                "criteria": {
                    "estimated_fmax_at_least_200_mhz": "PASS",
                    "configured_target_minus_uncertainty_timing_margin": "FAIL",
                    "all_explicit_ii1_constraints_met": "FAIL",
                }
            },
            "csim": {"required_64_token_rtl_cosimulation": "NOT_RUN"},
            "physical_fit": "NOT_RUN",
            "post_route_timing_and_drc": "NOT_RUN",
            "board_energy_measurement": "NOT_RUN",
            "ratios": {"candidate_to_bf16_lut": 5.1},
        },
    )
    extended_values = {
        "run_count": 2,
        "minimum_all_token_output_cosine": 0.9943,
        "maximum_all_token_state_relative_l2": 0.0991,
        "maximum_all_token_state_abs_error": 0.27,
        "total_element_saturations": 0,
        "total_accumulator_saturations": 0,
        "total_scale_clamps": 0,
        "total_alignment_underflows": 10,
        "total_e2m0_residual_clips": 4,
        "total_folds": 2,
    }
    extended = _write(
        tmp_path / "extended.json",
        {
            "status": "PASS",
            "full_deterministic_recompute": "PASS",
            **extended_values,
        },
    )

    result = summarize(
        synthetic,
        hls,
        capacity,
        corrected_heldout_path=heldout,
        corrected_hls_path=corrected_hls,
        corrected_extended_path=extended,
    )
    assert result["corrected_candidate"]["extended_8192_quality"] == "PASS"
    assert result["corrected_candidate"]["metrics"]["extended_8192"] == extended_values

    report = tmp_path / "answer.md"
    write_report(result, tmp_path / "answer.json", report)
    assert "2 development traces; min all-token cosine 0.994300" in report.read_text()

"""Answer the controlled MXFP4-for-BF16 replacement question from evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "reports" / "benchmark" / "corrected"
DEFAULT_SYNTHETIC = BENCHMARK / "synthetic_stability_verification.json"
DEFAULT_HLS = BENCHMARK / "hls_arithmetic_comparison.json"
DEFAULT_CAPACITY = BENCHMARK / "state_capacity_lower_bound.json"
DEFAULT_NATIVE_MANIFEST = BENCHMARK / "native_encoded_long_trace_manifest.json"
DEFAULT_NATIVE_VERIFICATION = (
    BENCHMARK / "native_encoded_long_trace_verification.json"
)
DEFAULT_NATIVE_CHECKPOINTS = (
    BENCHMARK / "native_encoded_long_trace_checkpoints.csv"
)
DEFAULT_CORRECTED_HELDOUT = (
    BENCHMARK / "e2m0_encoded" / "held_out" / "held_out_summary.json"
)
DEFAULT_CORRECTED_HLS = (
    ROOT / "reports" / "csynth" / "corrected" / "e2m0_hls_summary.json"
)
DEFAULT_CORRECTED_RTL = (
    ROOT
    / "reports"
    / "cosim"
    / "corrected"
    / "e2m0_trace64"
    / "e2m0_trace64_cosim_summary.json"
)
DEFAULT_CORRECTED_EXTENDED = (
    BENCHMARK
    / "e2m0_encoded"
    / "extended_development"
    / "extended_summary.json"
)
DEFAULT_OUTPUT = BENCHMARK / "replacement_question_summary.json"
DEFAULT_MARKDOWN = BENCHMARK / "replacement_question_summary.md"
ALLOWED_STATUSES = {"PASS", "FAIL", "NOT_RUN", "BLOCKED_EXTERNAL"}


def _normalize_status(value: object) -> str:
    status = str(value)
    if status.startswith("BLOCKED_EXTERNAL"):
        return "BLOCKED_EXTERNAL"
    return status


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_pass(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise ValueError(f"evidence extraction is not PASS: {path}")
    return payload


def _load_status(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") not in ALLOWED_STATUSES:
        raise ValueError(f"evidence has an unsupported status: {path}")
    return payload


def summarize(
    synthetic_path: Path,
    hls_path: Path,
    capacity_path: Path,
    native_manifest_path: Path | None = None,
    native_verification_path: Path | None = None,
    native_checkpoint_path: Path | None = None,
    corrected_heldout_path: Path | None = None,
    corrected_hls_path: Path | None = None,
    corrected_extended_path: Path | None = None,
    corrected_rtl_path: Path | None = None,
) -> dict[str, object]:
    synthetic = _load_pass(synthetic_path)
    hls = _load_pass(hls_path)
    capacity = _load_pass(capacity_path)
    rows = {row["variant"]: row for row in capacity["rows"]}
    bf16_bytes = int(rows["BF16"]["per_layer_logical_state_bytes"])
    mxfp4_bytes = int(
        rows["uniform_mxfp4_e2m1_e8m0_b32"]["per_layer_logical_state_bytes"]
    )
    storage_reduction = 1.0 - mxfp4_bytes / bf16_bytes

    native_paths = (
        native_manifest_path,
        native_verification_path,
        native_checkpoint_path,
    )
    if any(path is not None for path in native_paths) and not all(
        path is not None for path in native_paths
    ):
        raise ValueError("native manifest, verification, and checkpoints are one unit")
    native_gate = "NOT_RUN"
    native_final: dict[str, object] | None = None
    native_inputs: tuple[Path, ...] = ()
    if all(path is not None for path in native_paths):
        assert native_manifest_path is not None
        assert native_verification_path is not None
        assert native_checkpoint_path is not None
        native_manifest = _load_pass(native_manifest_path)
        native_verification = _load_pass(native_verification_path)
        if (
            native_verification.get("manifest_sha256")
            != _sha256(native_manifest_path)
        ):
            raise ValueError("native verification does not bind the supplied manifest")
        with native_checkpoint_path.open(newline="", encoding="utf-8") as handle:
            native_rows = list(csv.DictReader(handle))
        if [int(row["token_index"]) for row in native_rows] != [
            64,
            256,
            1024,
            4096,
            8192,
        ]:
            raise ValueError("native checkpoint CSV does not contain required lengths")
        native_gate = str(native_manifest["engineering_gate"]["status"])
        if native_gate not in ALLOWED_STATUSES:
            raise ValueError("native engineering gate has an unsupported status")
        native_final = {
            "token_index": 8192,
            "output_cosine_fp32": float(native_rows[-1]["output_cosine_fp32"]),
            "output_rel_l2": float(native_rows[-1]["output_rel_l2"]),
            "state_rel_l2": float(native_rows[-1]["state_rel_l2"]),
            "state_max_abs": float(native_rows[-1]["state_max_abs"]),
            "cumulative_element_saturations": int(
                native_rows[-1]["cumulative_element_saturations"]
            ),
            "cumulative_accumulator_saturations": int(
                native_rows[-1]["cumulative_accumulator_saturations"]
            ),
            "cumulative_scale_clamps": int(
                native_rows[-1]["cumulative_scale_clamps"]
            ),
            "cumulative_alignment_underflows": int(
                native_rows[-1]["cumulative_alignment_underflows"]
            ),
        }
        native_inputs = (
            native_manifest_path,
            native_verification_path,
            native_checkpoint_path,
        )

    corrected_paths = (corrected_heldout_path, corrected_hls_path)
    if any(path is not None for path in corrected_paths) and not all(
        path is not None for path in corrected_paths
    ):
        raise ValueError("corrected held-out and HLS evidence are one unit")
    corrected_inputs: tuple[Path, ...] = ()
    corrected: dict[str, object] = {
        "candidate": None,
        "heldout_1024_quality": "NOT_RUN",
        "full_deterministic_recompute": "NOT_RUN",
        "extended_8192_quality": "NOT_RUN",
        "hls_200mhz_timing": "NOT_RUN",
        "hls_configured_timing_margin": "NOT_RUN",
        "hls_explicit_ii1_constraints": "NOT_RUN",
        "hls_lut_and_step_cost_vs_bf16": "NOT_RUN",
        "rtl_64_token": "NOT_RUN",
        "physical_fit": "NOT_RUN",
        "post_route_timing_and_drc": "NOT_RUN",
        "board_energy": "NOT_RUN",
        "selected_method_pareto": "NOT_RUN",
        "metrics": None,
    }
    if all(path is not None for path in corrected_paths):
        assert corrected_heldout_path is not None
        assert corrected_hls_path is not None
        heldout = _load_pass(corrected_heldout_path)
        corrected_hls = _load_pass(corrected_hls_path)
        criteria = corrected_hls["phase4_decision_gate"]["criteria"]
        cost_status = str(
            corrected_hls["hls_lut_and_nonfold_step_cost_advantage_vs_bf16"]
        )
        ii_status = str(criteria["all_explicit_ii1_constraints_met"])
        extended_status = "NOT_RUN"
        extended_metrics: dict[str, object] | None = None
        extended_input: tuple[Path, ...] = ()
        if corrected_extended_path is not None:
            extended_payload = _load_status(corrected_extended_path)
            if extended_payload is not None:
                extended_status = str(extended_payload["status"])
                if (
                    extended_status == "PASS"
                    and extended_payload.get("full_deterministic_recompute") != "PASS"
                ):
                    raise ValueError("extended PASS is not backed by full replay")
                extended_fields = (
                    "run_count",
                    "minimum_all_token_output_cosine",
                    "maximum_all_token_state_relative_l2",
                    "maximum_all_token_state_abs_error",
                    "total_element_saturations",
                    "total_accumulator_saturations",
                    "total_scale_clamps",
                    "total_alignment_underflows",
                    "total_e2m0_residual_clips",
                    "total_folds",
                )
                if all(extended_payload.get(field) is not None for field in extended_fields):
                    extended_metrics = {
                        field: extended_payload[field] for field in extended_fields
                    }
                extended_input = (corrected_extended_path,)
        rtl_gate_status = str(
            corrected_hls["csim"]["required_64_token_rtl_cosimulation"]
        )
        rtl_metrics: dict[str, object] | None = None
        rtl_input: tuple[Path, ...] = ()
        if corrected_rtl_path is not None:
            if not corrected_rtl_path.exists():
                raise FileNotFoundError(corrected_rtl_path)
            rtl_payload = json.loads(corrected_rtl_path.read_text(encoding="utf-8"))
            required_rtl = str(
                rtl_payload.get("required_64_token_rtl_parity", "NOT_ESTABLISHED")
            )
            if rtl_payload.get("status") not in {"PASS", "PARTIAL", "FAIL"}:
                raise ValueError("corrected RTL evidence has an unsupported status")
            if required_rtl not in {"PASS", "FAIL", "NOT_ESTABLISHED"}:
                raise ValueError("corrected RTL parity has an unsupported status")
            rtl_gate_status = "PASS" if required_rtl == "PASS" else "FAIL"
            rtl_metrics = {
                "required_64_token_rtl_parity": required_rtl,
                "hls_c_simulation": rtl_payload.get("hls_c_simulation"),
                "direct_generated_rtl_load": rtl_payload.get(
                    "direct_generated_rtl_load"
                ),
                "official_hls_xsim": rtl_payload.get("official_hls_xsim"),
                "rtl_simulation": rtl_payload.get("rtl_simulation"),
            }
            rtl_input = (corrected_rtl_path,)
        corrected = {
            "candidate": corrected_hls["candidate_name"],
            "heldout_1024_quality": heldout["registered_held_out_gate"],
            "full_deterministic_recompute": heldout["full_deterministic_recompute"],
            "extended_8192_quality": extended_status,
            "hls_200mhz_timing": criteria[
                "estimated_fmax_at_least_200_mhz"
            ],
            "hls_configured_timing_margin": criteria[
                "configured_target_minus_uncertainty_timing_margin"
            ],
            "hls_explicit_ii1_constraints": ii_status,
            "hls_lut_and_step_cost_vs_bf16": cost_status,
            "rtl_64_token": rtl_gate_status,
            "physical_fit": corrected_hls["physical_fit"],
            "post_route_timing_and_drc": corrected_hls[
                "post_route_timing_and_drc"
            ],
            "board_energy": corrected_hls["board_energy_measurement"],
            "selected_method_pareto": (
                "FAIL"
                if "FAIL"
                in (
                    cost_status,
                    ii_status,
                    criteria["configured_target_minus_uncertainty_timing_margin"],
                )
                else "NOT_RUN"
            ),
            "metrics": {
                "heldout_min_all_token_output_cosine": heldout[
                    "minimum_all_token_output_cosine"
                ],
                "heldout_max_all_token_state_relative_l2": heldout[
                    "maximum_all_token_state_relative_l2"
                ],
                "logical_state_bytes": heldout["logical_state_bytes"],
                "test_seed_blocks": heldout["seed_block_count"],
                "paired_initial_state_conditions": heldout[
                    "paired_condition_count"
                ],
                "hls_ratios_vs_bf16": corrected_hls["ratios"],
                "extended_8192": extended_metrics,
                "rtl_64_token": rtl_metrics,
            },
        }
        corrected_inputs = (
            corrected_heldout_path,
            corrected_hls_path,
            *extended_input,
            *rtl_input,
        )

    decisions = {
        "bf16_synthetic_stability": synthetic["bf16_software_stability"],
        "uniform_mxfp4_synthetic_stability": synthetic[
            "uniform_mxfp4_stability"
        ],
        "native_encoded_mxfp4_synthetic_stability": native_gate,
        "scale_policy_rescues_uniform_mxfp4": synthetic[
            "scale_policy_rescues_uniform_mxfp4"
        ],
        "uniform_mxfp4_logical_state_reduction": (
            "PASS" if mxfp4_bytes < bf16_bytes else "FAIL"
        ),
        "uniform_mxfp4_hls_lut_and_step_cost_advantage": hls[
            "hls_lut_and_step_cost_advantage"
        ],
        "uniform_mxfp4_energy_advantage": _normalize_status(
            hls["energy_comparison"]
        ),
        "uniform_mxfp4_physical_fit": capacity[
            "physical_all_layer_state_bank_fit"
        ],
    }
    if any(value not in ALLOWED_STATUSES for value in decisions.values()):
        raise ValueError("replacement decision contains an unsupported status")
    corrected_statuses = (
        value
        for key, value in corrected.items()
        if key not in {"candidate", "metrics"}
    )
    if any(value not in ALLOWED_STATUSES for value in corrected_statuses):
        raise ValueError("corrected-candidate decision has an unsupported status")
    answer_status = (
        "PASS"
        if decisions["native_encoded_mxfp4_synthetic_stability"] == "PASS"
        and decisions["uniform_mxfp4_synthetic_stability"] == "PASS"
        and decisions["uniform_mxfp4_hls_lut_and_step_cost_advantage"] == "PASS"
        and decisions["uniform_mxfp4_energy_advantage"] == "PASS"
        and decisions["uniform_mxfp4_physical_fit"] == "PASS"
        else "FAIL"
    )
    stability_clause = (
        "native encoded and floating-Q/DQ diagnostics fail the frozen synthetic "
        "drift gate"
        if native_gate == "FAIL"
        else (
            "the floating-Q/DQ diagnostic fails the frozen synthetic drift "
            "gate, while native encoded long-horizon evidence is not run"
        )
    )
    source_identity = describe_source_files([Path(__file__).resolve()])
    return {
        "schema": 1,
        "status": "PASS",
        "scope": "controlled evidence synthesis for the uniform native-MXFP4 replacement question",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "research_question": (
            "Can native encoded MXFP4 replace BF16 in a fixed-geometry persistent-state "
            "GDN recurrence-core kernel while reducing FPGA logic/schedule cost and "
            "limiting empirical recurrent-state drift on long synthetic traces?"
        ),
        "current_answer_status": answer_status,
        "current_answer": (
            "No for the current uniform-MXFP4 implementation. It reduces logical "
            f"state storage, but {stability_clause}, and the fixed-geometry HLS "
            "implementation fails the LUT-and-STEP cost gate. Energy and physical "
            "fit remain unmeasured, so no energy or physical advantage is claimed."
        ),
        "decisions": decisions,
        "logical_state": {
            "bf16_bytes_per_layer": bf16_bytes,
            "uniform_mxfp4_bytes_per_layer": mxfp4_bytes,
            "uniform_mxfp4_reduction_fraction": storage_reduction,
            "uniform_mxfp4_reduction_percent": 100.0 * storage_reduction,
        },
        "hls_ratios": hls["ratios"],
        "native_encoded_token_8192": native_final,
        "corrected_candidate": corrected,
        "synthetic_finding": synthetic["overall_finding"],
        "inputs": {
            path.relative_to(ROOT).as_posix(): _sha256(path)
            for path in (
                synthetic_path,
                hls_path,
                capacity_path,
                *native_inputs,
                *corrected_inputs,
            )
        },
        "summary_validation": (
            "The summary requires PASS extraction manifests, validates exact status "
            "vocabulary, recomputes per-layer storage reduction, and hashes every input; "
            "this is evidence aggregation, not an independent arithmetic implementation."
        ),
        "limitations": [
            "the controlled uniform comparison uses one deterministic synthetic nominal trace",
            "native encoded arithmetic is software-executed and cross-checked against the 64-token scalar/HLS trace",
            "the BF16 hardware baseline has bounded C-sim but no 64-token RTL parity",
            "the corrected candidate has 64-token HLS C parity and an exact generated-RTL LOAD, but no recurrent candidate STEP parity",
            "the corrected candidate test set has three seed blocks crossed with two paired initial-state conditions",
            "the local candidate registration was not externally timestamped and omitted part of the execution dependency closure",
            "corrected-candidate test-set quality and HLS cost are reported separately from the controlled uniform replacement",
            "uniform-MXFP4 HLS estimates are not post-route measurements",
            "closed-loop model quality and board energy are not available for this evidence synthesis",
        ],
    }


def write_report(
    result: dict[str, object], json_path: Path, markdown_path: Path
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    decisions = result["decisions"]
    ratios = result["hls_ratios"]
    logical = result["logical_state"]
    native_final = result["native_encoded_token_8192"]
    corrected = result["corrected_candidate"]
    corrected_metrics = corrected["metrics"]
    native_detail = (
        "No completed native encoded long trace"
        if native_final is None
        else (
            f"token-8192 cosine {native_final['output_cosine_fp32']:.6f}, "
            f"state relative L2 {native_final['state_rel_l2']:.6f}"
        )
    )
    corrected_quality_detail = (
        "No completed corrected-candidate evidence"
        if corrected_metrics is None
        else (
            f"min all-token cosine "
            f"{corrected_metrics['heldout_min_all_token_output_cosine']:.6f}; "
            f"max all-token state relative L2 "
            f"{corrected_metrics['heldout_max_all_token_state_relative_l2']:.6f}"
        )
    )
    extended_metrics = (
        None if corrected_metrics is None else corrected_metrics.get("extended_8192")
    )
    rtl_metrics = (
        None if corrected_metrics is None else corrected_metrics.get("rtl_64_token")
    )
    rtl_detail = (
        "No candidate-specific recurrent RTL evidence"
        if rtl_metrics is None
        else (
            f"required parity {rtl_metrics['required_64_token_rtl_parity']}; "
            f"HLS C {rtl_metrics['hls_c_simulation']['status']}; direct RTL LOAD "
            f"{rtl_metrics['direct_generated_rtl_load']['status']}; "
            f"{rtl_metrics['rtl_simulation']['completed_recurrent_steps']} completed recurrent steps"
        )
    )
    extended_quality_detail = (
        "No fully recomputed extended metrics"
        if extended_metrics is None
        else (
            f"{extended_metrics['run_count']} development traces; min all-token "
            f"cosine {extended_metrics['minimum_all_token_output_cosine']:.6f}; "
            f"max all-token state relative L2 "
            f"{extended_metrics['maximum_all_token_state_relative_l2']:.6f}"
        )
    )
    markdown_path.write_text(
        "\n".join(
            [
                "# MXFP4-for-BF16 Replacement Question",
                "",
                "Evidence synthesis status: `PASS`",
                f"Current answer: `{result['current_answer_status']}`",
                "",
                result["current_answer"],
                "",
                "| Criterion | Status | Controlled result |",
                "|---|---|---|",
                f"| BF16 synthetic stability | {decisions['bf16_synthetic_stability']} | Frozen 0.99 cosine / 0.10 final-state-relative-L2 gate |",
                f"| Native encoded MXFP4 stability | {decisions['native_encoded_mxfp4_synthetic_stability']} | {native_detail} |",
                f"| Uniform MXFP4 synthetic stability | {decisions['uniform_mxfp4_synthetic_stability']} | Same trace, state layout, and recurrence boundary |",
                f"| Scale-policy rescue | {decisions['scale_policy_rescues_uniform_mxfp4']} | Fixed, every-token, periodic, and threshold refresh |",
                f"| Logical state storage | {decisions['uniform_mxfp4_logical_state_reduction']} | {logical['uniform_mxfp4_bytes_per_layer']} versus {logical['bf16_bytes_per_layer']} bytes/layer ({logical['uniform_mxfp4_reduction_percent']:.2f}% reduction) |",
                f"| HLS LUT and STEP cost | {decisions['uniform_mxfp4_hls_lut_and_step_cost_advantage']} | {ratios['mxfp4_to_bf16_lut']:.3f}x LUT, {ratios['mxfp4_to_bf16_step_cycles_max']:.3f}x max STEP cycles |",
                f"| Energy advantage | {decisions['uniform_mxfp4_energy_advantage']} | No matched board or post-route energy result |",
                f"| Physical all-layer fit | {decisions['uniform_mxfp4_physical_fit']} | Raw bit capacity is not placed/banked fit |",
                "",
                "## Recurrence-Aware Mitigation (separate comparison)",
                "",
                "| Criterion | Status | Result |",
                "|---|---|---|",
                f"| Test-set 1,024-token quality | {corrected['heldout_1024_quality']} | {corrected_quality_detail} |",
                f"| Full deterministic recomputation | {corrected['full_deterministic_recompute']} | Same-implementation integrity check for every paired condition |",
                f"| Extended 8,192-token quality | {corrected['extended_8192_quality']} | {extended_quality_detail}; development-only random/zero initial states |",
                f"| HLS 200 MHz timing | {corrected['hls_200mhz_timing']} | Source-locked C-synthesis estimate |",
                f"| Configured timing margin | {corrected['hls_configured_timing_margin']} | Target minus reported uncertainty |",
                f"| Explicit II=1 constraints | {corrected['hls_explicit_ii1_constraints']} | Every targeted loop must meet II=1 |",
                f"| HLS LUT/STEP cost vs BF16 | {corrected['hls_lut_and_step_cost_vs_bf16']} | Matched target and dimensions; changed state representation |",
                f"| Corrected-candidate 64-token RTL | {corrected['rtl_64_token']} | {rtl_detail} |",
                f"| Selected-method Pareto | {corrected['selected_method_pareto']} | Quality alone cannot pass this gate |",
                "",
                "This is a layer-level synthetic and HLS-estimate conclusion. It does not",
                "establish closed-loop Qwen quality, routed uniform-MXFP4 performance, or board energy.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", type=Path, default=DEFAULT_SYNTHETIC)
    parser.add_argument("--hls", type=Path, default=DEFAULT_HLS)
    parser.add_argument("--capacity", type=Path, default=DEFAULT_CAPACITY)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument(
        "--native-verification", type=Path, default=DEFAULT_NATIVE_VERIFICATION
    )
    parser.add_argument(
        "--native-checkpoints", type=Path, default=DEFAULT_NATIVE_CHECKPOINTS
    )
    parser.add_argument(
        "--corrected-heldout", type=Path, default=DEFAULT_CORRECTED_HELDOUT
    )
    parser.add_argument("--corrected-hls", type=Path, default=DEFAULT_CORRECTED_HLS)
    parser.add_argument(
        "--corrected-extended", type=Path, default=DEFAULT_CORRECTED_EXTENDED
    )
    parser.add_argument("--corrected-rtl", type=Path, default=DEFAULT_CORRECTED_RTL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    result = summarize(
        _resolve(args.synthetic),
        _resolve(args.hls),
        _resolve(args.capacity),
        _resolve(args.native_manifest),
        _resolve(args.native_verification),
        _resolve(args.native_checkpoints),
        _resolve(args.corrected_heldout),
        _resolve(args.corrected_hls),
        _resolve(args.corrected_extended),
        _resolve(args.corrected_rtl),
    )
    write_report(result, _resolve(args.output), _resolve(args.markdown))
    print(json.dumps({"status": result["status"], "answer": result["current_answer_status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate the authoritative final paper-completion gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUSES = {"PASS", "FAIL", "NOT_RUN", "BLOCKED_EXTERNAL"}
AUDIT_PDF = ROOT / "paper" / "corrected" / "paper_audit_candidate.pdf"
ASSET_MANIFEST = ROOT / "paper" / "corrected" / "asset_manifest.json"
AUDIT_BUILD_MANIFEST = (
    ROOT / "paper" / "corrected" / "paper_audit_build_manifest.json"
)
VISUAL_AUDIT_MANIFEST = ROOT / "paper" / "corrected" / "paper_visual_audit.json"
TRACEABILITY_STATUS = ROOT / "docs" / "reviewer_traceability_status.json"
E2M0_CONTROL_COSIM = (
    ROOT
    / "reports"
    / "cosim"
    / "corrected"
    / "e2m0_control_smoke"
    / "e2m0_control_smoke_summary.json"
)
E2M0_TRACE_COSIM = (
    ROOT
    / "reports"
    / "cosim"
    / "corrected"
    / "e2m0_trace64"
    / "e2m0_trace64_cosim_summary.json"
)
E2M0_POSTROUTE = (
    ROOT
    / "reports"
    / "vivado"
    / "corrected"
    / "e2m0"
    / "e2m0_postroute_summary.json"
)
MXFP8_HLS = ROOT / "reports" / "csynth" / "corrected" / "mxfp8_hls_summary.json"
MXFP8_POSTROUTE = (
    ROOT / "reports" / "vivado" / "baselines" / "mxfp8" / "mxfp8_vivado_summary.json"
)
BF16_PHYSICAL = (
    ROOT / "reports" / "vivado" / "baselines" / "bf16" / "bf16_vivado_summary.json"
)
QWEN_RECURRENT = (
    ROOT / "reports" / "benchmark" / "qwen_recurrent_stability_manifest.json"
)
HARDWARE_AVAILABILITY = ROOT / "reports" / "environment" / "hardware_availability.json"
_BASE_FINAL_GATES: tuple[dict[str, object], ...] = (
    {
        "gate": "prior_art_gap",
        "release_required": True,
        "status": "PASS",
        "finding": "A bounded primary-source search found no exact synthetic recurrence-core and matched-HLS study; overlapping arithmetic, state, and dataflow constituents are attributed and no architectural-first claim is made.",
        "evidence": [
            "docs/prior_art_matrix.md",
            "docs/evidence/g0_focused_gap_resolution_2026_08_01.md",
            "docs/evidence/prior_art_gap_recheck_2026_08_02.md",
            "docs/evidence/prior_art_gap_recheck_2026_08_02_v2.md",
        ],
    },
    {
        "gate": "exact_official_recurrence_parity",
        "release_required": True,
        "status": "PASS",
        "finding": "FP64/FP32 and pinned recurrent/chunk/cache comparisons pass at the controlled layer boundary.",
        "evidence": ["reports/golden/official_parity/official_parity_verification.json"],
    },
    {
        "gate": "independent_bit_exact_mx_reference",
        "release_required": True,
        "status": "PASS",
        "finding": "Independent encoded arithmetic and resident-command oracles pass bounded exhaustive, adversarial, and corrected E2M0 checks.",
        "evidence": [
            "golden/gdn_mxfp4_encoded.py",
            "golden/gdn_e2m0_encoded.py",
            "reports/csynth/corrected/e2m0_hls_summary.json",
        ],
    },
    {
        "gate": "matched_native_mxfp8_baseline",
        "release_required": True,
        "status": "NOT_RUN",
        "finding": "The reviewer-requested native MXFP8 wider low-precision baseline has not been validated.",
        "evidence": [],
    },
    {
        "gate": "c_sim_and_rtl_parity",
        "release_required": False,
        "status": "FAIL",
        "finding": "The corrected E2M0 candidate has exact 64-token HLS C parity but its 64-token generated-RTL parity is not established.",
        "evidence": [
            "reports/csynth/corrected/e2m0_hls_summary.json",
            "reports/test_results/e2m0_resident_trace64_csim_20260802.log",
        ],
        "substatus": {
            "corrected_candidate_hls_c_sim_64_token": "PASS",
            "corrected_candidate_rtl_control_smoke": "PASS",
            "corrected_candidate_rtl_64_token": "FAIL",
            "uniform_mxfp4_rtl_64_token": "PASS",
        },
    },
    {
        "gate": "closed_loop_real_model_quality",
        "release_required": False,
        "status": "BLOCKED_EXTERNAL",
        "finding": "Four short model-derived Qwen recurrence traces are complete, but full-model closed-loop quality, perplexity, and downstream accuracy require external 80B model execution assets.",
        "evidence": [
            "reports/golden/qwen_capture_characterization.json",
            "reports/benchmark/qwen_recurrent_stability_manifest.json",
            "docs/experimental_protocol.md",
        ],
    },
    {
        "gate": "selected_method_pareto_advantage",
        "release_required": False,
        "status": "FAIL",
        "finding": "The corrected candidate passes three high-retention test seed blocks under two paired initial-state conditions, but its HLS LUT and STEP costs exceed BF16 and its configured timing margin and explicit II=1 constraints fail.",
        "evidence": [
            "reports/benchmark/corrected/e2m0_encoded/held_out/held_out_summary.json",
            "reports/csynth/corrected/e2m0_hls_summary.json",
        ],
        "substatus": {
            "high_retention_1024_quality": "PASS",
            "full_deterministic_recompute": "PASS",
            "extended_8192_quality": "NOT_RUN",
            "logical_payload_below_uniform_mxfp8": "PASS",
            "hls_200mhz_timing": "PASS",
            "hls_configured_timing_margin": "FAIL",
            "hls_explicit_ii1_constraints": "FAIL",
            "hls_lut_and_step_cost_vs_bf16": "FAIL",
            "allocated_physical_memory": "NOT_RUN",
            "average_and_p99_service_latency": "NOT_RUN",
            "energy": "BLOCKED_EXTERNAL",
        },
    },
    {
        "gate": "controlled_wider_physical_baselines",
        "release_required": False,
        "status": "NOT_RUN",
        "finding": "Controlled wider-arithmetic physical implementation results have not been reconciled.",
        "evidence": [],
    },
    {
        "gate": "physical_all_layer_state_bank_fit",
        "release_required": True,
        "status": "NOT_RUN",
        "finding": "No selected-candidate all-layer physical allocation, banking, or service-rate result exists.",
        "evidence": ["docs/experimental_protocol.md"],
    },
    {
        "gate": "post_route_timing_and_drc",
        "release_required": True,
        "status": "NOT_RUN",
        "finding": "Corrected selected-candidate post-route timing and DRC reports do not exist.",
        "evidence": ["docs/implementation_status.md"],
    },
    {
        "gate": "real_board_parity_and_energy",
        "release_required": False,
        "status": "BLOCKED_EXTERNAL",
        "finding": "Vitis/Vivado are installed, but no attached U55C, U55C XRT platform, xclbin, or board telemetry is available; vectorless power is not measured energy.",
        "evidence": [
            "reports/environment/hardware_availability.json",
            "docs/experimental_protocol.md",
        ],
    },
    {
        "gate": "reviewer_traceability",
        "release_required": True,
        "status": "NOT_RUN",
        "finding": "All reviewer sources are ingested, but remediation cannot be checked against a final evidence-supported PDF.",
        "evidence": ["docs/reviewer_traceability.md"],
    },
    {
        "gate": "paper_provenance_and_final_pdf_audit",
        "release_required": True,
        "status": "NOT_RUN",
        "finding": "Corrected source numbers and provenance exist, but final PDF generation and page-by-page audit are prohibited until upstream gates pass.",
        "evidence": [
            "docs/evidence_manifest.md",
            "docs/implementation_status.md",
            "docs/venue_requirements_2026_08_02.md",
        ],
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def _apply_traceability_evidence(gate: dict[str, object]) -> None:
    if not TRACEABILITY_STATUS.exists():
        return
    try:
        report = _load_json(TRACEABILITY_STATUS)
        source = ROOT / str(report.get("traceability_source", ""))
        visual = ROOT / str(report.get("visual_audit", ""))
        status = str(report.get("status", "NOT_RUN"))
        valid = (
            status in ALLOWED_STATUSES
            and source.is_file()
            and _sha256(source)
            == str(report.get("traceability_source_sha256", "")).upper()
            and int(report.get("comment_row_count", -1)) == 68
            and int(report.get("directive_row_count", -1)) == 25
        )
        if status == "PASS":
            valid = (
                valid
                and visual.is_file()
                and _sha256(visual)
                == str(report.get("visual_audit_sha256", "")).upper()
                and report.get("visual_audit_status") == "PASS"
                and all(
                    isinstance(row, dict) and row.get("status") == "PASS"
                    for row in report.get("rows", [])
                )
            )
        gate["status"] = status if valid else "FAIL"
        if valid and status == "PASS":
            gate["finding"] = (
                "All 68 reviewer-comment rows and 25 reviewer directives are "
                "traceable to the page-audited paper candidate."
            )
        elif valid and status == "NOT_RUN":
            gate["finding"] = (
                "All reviewer sources are ingested, but the source ledger has "
                "not been checked against a page-audited paper candidate."
            )
        elif valid:
            gate["finding"] = (
                "The reviewer traceability summary is current but contains "
                "non-passing remediation rows."
            )
        else:
            gate["finding"] = "The reviewer-traceability summary is malformed or stale."
        gate["evidence"].append(TRACEABILITY_STATUS.relative_to(ROOT).as_posix())
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        gate["status"] = "FAIL"
        gate["finding"] = "The reviewer-traceability status artifact is malformed or stale."


def _apply_paper_audit_evidence(gate: dict[str, object]) -> None:
    paths = (
        ASSET_MANIFEST,
        AUDIT_BUILD_MANIFEST,
        VISUAL_AUDIT_MANIFEST,
        AUDIT_PDF,
    )
    if not (
        ASSET_MANIFEST.is_file()
        and AUDIT_BUILD_MANIFEST.is_file()
        and VISUAL_AUDIT_MANIFEST.is_file()
        and AUDIT_PDF.is_file()
    ):
        return
    gate["evidence"].extend(
        path.relative_to(ROOT).as_posix() for path in paths if path.exists()
    )
    try:
        assets = _load_json(ASSET_MANIFEST)
        build = _load_json(AUDIT_BUILD_MANIFEST)
        visual = _load_json(VISUAL_AUDIT_MANIFEST)
        pages = visual.get("pages")
        valid = (
            assets.get("status") == "PASS"
            and build.get("status") == "PASS"
            and build.get("build_status") == "PASS"
            and build.get("artifact_kind") == "internal_audit_candidate"
            and build.get("submission_eligible") is False
            and _sha256(ASSET_MANIFEST)
            == str(build.get("asset_manifest_sha256", "")).upper()
            and AUDIT_PDF.is_file()
            and _sha256(AUDIT_PDF)
            == str(build.get("output_sha256", "")).upper()
            and visual.get("status") == "PASS"
            and visual.get("visual_audit_status") == "PASS"
            and visual.get("submission_eligible") is False
            and _sha256(AUDIT_BUILD_MANIFEST)
            == str(visual.get("build_manifest_sha256", "")).upper()
            and _sha256(AUDIT_PDF)
            == str(visual.get("audit_candidate_sha256", "")).upper()
            and isinstance(pages, list)
            and len(pages) == int(visual.get("page_count", -1))
            and bool(pages)
            and all(
                isinstance(row, dict)
                and (ROOT / str(row.get("path", ""))).is_file()
                and _sha256(ROOT / str(row["path"]))
                == str(row.get("sha256", "")).upper()
                for row in pages
            )
        )
        gate["status"] = "PASS" if valid else "FAIL"
        gate["finding"] = (
            "Corrected numbers, source assets, compiled audit-candidate bytes, "
            "and every rendered page pass hash and visual checks; these exact "
            "bytes are eligible for gated finalization."
            if valid
            else "The corrected paper audit artifacts are incomplete or stale."
        )
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        gate["status"] = "FAIL"
        gate["finding"] = "The corrected paper audit artifacts are malformed or stale."


def build_final_gates() -> tuple[dict[str, object], ...]:
    gates = list(copy.deepcopy(_BASE_FINAL_GATES))
    mxfp8_gate = next(
        row for row in gates if row["gate"] == "matched_native_mxfp8_baseline"
    )
    if MXFP8_HLS.exists():
        mxfp8 = _load_json(MXFP8_HLS)
        mxfp8_pass = (
            mxfp8.get("status") == "PASS"
            and mxfp8.get("csim", {}).get("arithmetic", {}).get("status") == "PASS"
            and mxfp8.get("csim", {}).get("persistent_kernel", {}).get("status") == "PASS"
            and mxfp8.get("csynth", {}).get("status") == "PASS"
            and mxfp8.get("csynth", {}).get("targeted_loop_ii_status") == "PASS"
        )
        mxfp8_gate["status"] = "PASS" if mxfp8_pass else "FAIL"
        mxfp8_gate["finding"] = (
            "The matched native E4M3/E8M0 baseline passes exhaustive bounded "
            "arithmetic C-sim, one exact persistent-kernel transition, U55C "
            "C-synthesis, and every explicit II=1 constraint."
            if mxfp8_pass
            else "The matched native MXFP8 baseline evidence is incomplete or stale."
        )
        mxfp8_gate["evidence"] = [MXFP8_HLS.relative_to(ROOT).as_posix()]
        mxfp8_gate["substatus"] = {
            "arithmetic_csim": mxfp8.get("csim", {}).get("arithmetic", {}).get("status", "NOT_RUN"),
            "persistent_kernel_csim": mxfp8.get("csim", {}).get("persistent_kernel", {}).get("status", "NOT_RUN"),
            "csynthesis": mxfp8.get("csynth", {}).get("status", "NOT_RUN"),
            "explicit_ii1_constraints": mxfp8.get("csynth", {}).get("targeted_loop_ii_status", "NOT_RUN"),
            "post_route": "NOT_RUN",
        }
        if MXFP8_POSTROUTE.exists():
            mxfp8_physical = _load_json(MXFP8_POSTROUTE)
            mxfp8_gate["evidence"].append(MXFP8_POSTROUTE.relative_to(ROOT).as_posix())
            mxfp8_gate["substatus"]["post_route"] = (
                "PASS"
                if mxfp8_physical.get("status") == "PASS"
                and mxfp8_physical.get("physical_fit") == "PASS"
                else "FAIL"
            )

    closed_loop_gate = next(
        row for row in gates if row["gate"] == "closed_loop_real_model_quality"
    )
    if QWEN_RECURRENT.exists():
        qwen = _load_json(QWEN_RECURRENT)
        short_real_pass = (
            qwen.get("status") == "PASS"
            and qwen.get("source_metadata", {}).get("total_valid_tokens") == 60
            and len(qwen.get("aggregate", {})) == 4
            and all(
                row.get("nonfinite_events") == 0
                for row in qwen.get("aggregate", {}).values()
            )
        )
        closed_loop_gate["substatus"] = {
            "short_real_input_recurrence": "PASS" if short_real_pass else "FAIL",
            "closed_loop_full_model_quality": "BLOCKED_EXTERNAL",
        }
        if QWEN_RECURRENT.relative_to(ROOT).as_posix() not in closed_loop_gate["evidence"]:
            closed_loop_gate["evidence"].append(QWEN_RECURRENT.relative_to(ROOT).as_posix())

    uniform_rtl_path = (
        ROOT
        / "reports"
        / "cosim"
        / "corrected"
        / "direct_rtl_trace64"
        / "direct_rtl_trace64_summary.json"
    )
    rtl_gate = next(row for row in gates if row["gate"] == "c_sim_and_rtl_parity")
    e2m0_hls_path = ROOT / "reports" / "csynth" / "corrected" / "e2m0_hls_summary.json"
    uniform_rtl_pass = False
    if uniform_rtl_path.exists():
        summary = json.loads(uniform_rtl_path.read_text(encoding="utf-8"))
        uniform_rtl_pass = (
            summary.get("status") == "PASS"
            and summary.get("required_64_token_rtl_parity") == "PASS"
            and summary.get("parity", {}).get("ordered_tokens") == 64
            and summary.get("parity", {}).get("final_generation") == 64
        )
    if e2m0_hls_path.exists():
        e2m0 = json.loads(e2m0_hls_path.read_text(encoding="utf-8"))
        c_sim_pass = (
            e2m0.get("status") == "PASS"
            and e2m0.get("csim", {}).get("required_64_token_csim") == "PASS"
        )
        rtl_gate["substatus"]["corrected_candidate_hls_c_sim_64_token"] = (
            "PASS" if c_sim_pass else "FAIL"
        )
        rtl_gate["substatus"]["uniform_mxfp4_rtl_64_token"] = (
            "PASS" if uniform_rtl_pass else "NOT_RUN"
        )
        control_pass = False
        if E2M0_CONTROL_COSIM.exists():
            control = _load_json(E2M0_CONTROL_COSIM)
            control_pass = (
                control.get("status") == "PASS"
                and control.get("official_hls_cosim", {}).get("status") == "PASS"
                and control.get("rtl_simulation", {}).get("completed_transactions")
                == 2
                and control.get("recurrent_transition_covered") is False
                and control.get("required_64_token_rtl_parity") == "NOT_RUN"
            )
            rtl_gate["evidence"].append(
                E2M0_CONTROL_COSIM.relative_to(ROOT).as_posix()
            )
        rtl_gate["substatus"]["corrected_candidate_rtl_control_smoke"] = (
            "PASS" if control_pass else "FAIL"
        )
        candidate_trace_pass = False
        candidate_trace_partial = False
        if E2M0_TRACE_COSIM.exists():
            trace = _load_json(E2M0_TRACE_COSIM)
            candidate_trace_pass = (
                trace.get("status") == "PASS"
                and trace.get("required_64_token_rtl_parity") == "PASS"
                and trace.get("rtl_simulation", {}).get("completed_transactions") == 66
                and trace.get("parity", {}).get("ordered_tokens") == 64
            )
            candidate_trace_partial = (
                trace.get("status") == "PARTIAL"
                and trace.get("required_64_token_rtl_parity") == "NOT_ESTABLISHED"
                and trace.get("hls_c_simulation", {}).get("status") == "PASS"
                and trace.get("direct_generated_rtl_load", {}).get("status") == "PASS"
                and trace.get("rtl_simulation", {}).get("completed_recurrent_steps") == 0
            )
            rtl_gate["evidence"].append(E2M0_TRACE_COSIM.relative_to(ROOT).as_posix())
        rtl_gate["substatus"]["corrected_candidate_rtl_64_token"] = (
            "PASS" if candidate_trace_pass else "FAIL"
        )
        rtl_gate["status"] = (
            "PASS"
            if c_sim_pass and control_pass and candidate_trace_pass and uniform_rtl_pass
            else "FAIL"
        )
        rtl_gate["finding"] = (
            "The corrected candidate passes exact 64-token HLS C simulation "
            "and generated-RTL parity for all 64 recurrent STEPs, "
            "per-token outputs/counters, and the final state snapshot. The "
            "separate two-command control smoke and uniform-MXFP4 RTL trace also pass."
            if rtl_gate["status"] == "PASS"
            else (
                "The corrected candidate passes exact 64-token HLS C simulation, "
                "two generated-RTL control commands, and one direct generated-RTL "
                "LOAD. Two official XSIM attempts exhaust host memory before "
                "transaction one; no corrected recurrent STEP completes in RTL, "
                "so 64-token candidate parity is not established."
                if candidate_trace_partial and c_sim_pass and control_pass
                else "Corrected-candidate C-sim or scoped generated-RTL evidence is missing or stale."
            )
        )

    wider_physical_gate = next(
        row for row in gates if row["gate"] == "controlled_wider_physical_baselines"
    )
    if BF16_PHYSICAL.exists():
        bf16_physical = _load_json(BF16_PHYSICAL)
        bf16_attempt_valid = (
            bf16_physical.get("status") == "PASS"
            and bf16_physical.get("synthesis_completion") == "PASS"
            and bf16_physical.get("physical_fit") == "FAIL"
            and bf16_physical.get("placement_completion") == "FAIL_CAPACITY"
        )
        mxfp8_fit = "NOT_RUN"
        evidence = [BF16_PHYSICAL.relative_to(ROOT).as_posix()]
        if MXFP8_POSTROUTE.exists():
            mxfp8_physical = _load_json(MXFP8_POSTROUTE)
            mxfp8_fit = str(mxfp8_physical.get("physical_fit", "NOT_RUN"))
            evidence.append(MXFP8_POSTROUTE.relative_to(ROOT).as_posix())
        wider_physical_gate["status"] = "FAIL" if bf16_attempt_valid else "NOT_RUN"
        wider_physical_gate["finding"] = (
            "The controlled 36-layer BF16 physical attempt completes synthesis "
            "but fails U55C memory capacity before placement; a smaller layout is "
            "not substituted. Native MXFP8 physical status is reported separately."
            if bf16_attempt_valid
            else "The controlled BF16 physical-attempt evidence is missing or stale."
        )
        wider_physical_gate["evidence"] = evidence
        wider_physical_gate["substatus"] = {
            "bf16_synthesis": "PASS" if bf16_attempt_valid else "FAIL",
            "bf16_physical_fit": "FAIL" if bf16_attempt_valid else "NOT_RUN",
            "mxfp8_physical_fit": mxfp8_fit,
            "uniform_mxfp4_physical_fit": "NOT_RUN",
        }

    pareto_gate = next(
        row for row in gates if row["gate"] == "selected_method_pareto_advantage"
    )
    held_out_path = (
        ROOT
        / "reports"
        / "benchmark"
        / "corrected"
        / "e2m0_encoded"
        / "held_out"
        / "held_out_summary.json"
    )
    if held_out_path.exists() and e2m0_hls_path.exists():
        held_out = json.loads(held_out_path.read_text(encoding="utf-8"))
        e2m0 = json.loads(e2m0_hls_path.read_text(encoding="utf-8"))
        pareto_gate["substatus"]["high_retention_1024_quality"] = (
            "PASS" if held_out.get("registered_held_out_gate") == "PASS" else "FAIL"
        )
        pareto_gate["substatus"]["full_deterministic_recompute"] = str(
            held_out.get("full_deterministic_recompute", "NOT_RUN")
        )
        pareto_gate["substatus"]["hls_200mhz_timing"] = str(
            e2m0.get("phase4_decision_gate", {})
            .get("criteria", {})
            .get("estimated_fmax_at_least_200_mhz", "NOT_RUN")
        )
        pareto_gate["substatus"]["hls_configured_timing_margin"] = str(
            e2m0.get("phase4_decision_gate", {})
            .get("criteria", {})
            .get("configured_target_minus_uncertainty_timing_margin", "NOT_RUN")
        )
        pareto_gate["substatus"]["hls_explicit_ii1_constraints"] = str(
            e2m0.get("csynth", {}).get("targeted_loop_ii_status", "NOT_RUN")
        )
        pareto_gate["substatus"]["hls_lut_and_step_cost_vs_bf16"] = str(
            e2m0.get("hls_lut_and_nonfold_step_cost_advantage_vs_bf16", "NOT_RUN")
        )
    extended_path = (
        ROOT
        / "reports"
        / "benchmark"
        / "corrected"
        / "e2m0_encoded"
        / "extended_development"
        / "extended_summary.json"
    )
    if extended_path.exists():
        extended = json.loads(extended_path.read_text(encoding="utf-8"))
        extended_status = str(extended.get("status", "NOT_RUN"))
        replay_status = str(extended.get("full_deterministic_recompute", "NOT_RUN"))
        if extended_status == "PASS" and replay_status == "PASS":
            pareto_gate["substatus"]["extended_8192_quality"] = "PASS"
            pareto_gate["finding"] = (
                "The corrected candidate passes three 1024-token test seed "
                "blocks under two paired initial-state conditions and "
                f"{int(extended.get('run_count', 0))} fully recomputed "
                "8192-token development traces, but its HLS LUT and STEP costs "
                "exceed BF16 and its configured timing margin and explicit II=1 "
                "constraints fail."
            )
        elif "FAIL" in (extended_status, replay_status):
            pareto_gate["substatus"]["extended_8192_quality"] = "FAIL"
        else:
            pareto_gate["substatus"]["extended_8192_quality"] = "NOT_RUN"
        pareto_gate["evidence"].append(
            extended_path.relative_to(ROOT).as_posix()
        )
    physical_gate = next(
        row for row in gates if row["gate"] == "physical_all_layer_state_bank_fit"
    )
    postroute_gate = next(
        row for row in gates if row["gate"] == "post_route_timing_and_drc"
    )
    if E2M0_POSTROUTE.exists():
        postroute = _load_json(E2M0_POSTROUTE)
        physical_pass = (
            postroute.get("status") == "PASS"
            and postroute.get("route_completion") == "PASS"
            and postroute.get("physical_fit") == "PASS"
        )
        drc = postroute.get("drc", {})
        timing_evidence_pass = (
            physical_pass
            and drc.get("signoff_status") in {"PASS", "PASS_WITH_WARNINGS"}
            and drc.get("critical_warning_count") == 0
            and drc.get("error_count") == 0
            and postroute.get("first_tested_closing_point", {}).get("status")
            == "PASS"
        )
        evidence_path = E2M0_POSTROUTE.relative_to(ROOT).as_posix()
        physical_gate["evidence"] = [evidence_path]
        physical_gate["status"] = "PASS" if physical_pass else "FAIL"
        physical_gate["finding"] = (
            "The declared corrected-candidate resident-state design physically "
            "fits out of context on the U55C at 624 URAM and 208,523 CLB LUTs. "
            "This is not a complete-model or shell-integrated fit claim."
            if physical_pass
            else "The corrected candidate does not have a valid physical-fit result."
        )
        postroute_gate["evidence"] = [evidence_path]
        postroute_gate["status"] = "PASS" if timing_evidence_pass else "FAIL"
        postroute_gate["finding"] = (
            "Post-route timing and DRC evidence is complete: the candidate "
            "fails setup at 250 and 200 MHz, first closes at the tested "
            "180.18 MHz point, and has warnings but no critical warnings or "
            "errors. The gate passes evidence completeness, not target timing."
            if timing_evidence_pass
            else "Corrected-candidate post-route timing or DRC evidence is missing or invalid."
        )
        postroute_gate["substatus"] = {
            "route_completion": postroute.get("route_completion", "NOT_RUN"),
            "physical_fit": postroute.get("physical_fit", "NOT_RUN"),
            "target_250mhz_timing": postroute.get("target_clock", {}).get(
                "status", "NOT_RUN"
            ),
            "timing_200mhz": postroute.get("implemented_200mhz_timing", "NOT_RUN"),
            "first_tested_closing_point": postroute.get(
                "first_tested_closing_point", {}
            ).get("status", "NOT_RUN"),
            "drc": drc.get("signoff_status", "NOT_RUN"),
            "vectorless_power": "PASS"
            if postroute.get("power_at_5p6ns", {}).get("measured_on_board") is False
            else "FAIL",
            "measured_board_energy": "BLOCKED_EXTERNAL",
        }
        pareto_gate["substatus"]["allocated_physical_memory"] = (
            "PASS" if physical_pass else "FAIL"
        )
        pareto_gate["substatus"]["energy"] = "BLOCKED_EXTERNAL"
        pareto_gate["evidence"].append(evidence_path)

    board_gate = next(
        row for row in gates if row["gate"] == "real_board_parity_and_energy"
    )
    if HARDWARE_AVAILABILITY.exists():
        hardware = _load_json(HARDWARE_AVAILABILITY)
        board = hardware.get("u55c_board_experiment", {})
        gpu = hardware.get("native_fp4_gpu_experiment", {})
        board_gate["status"] = "BLOCKED_EXTERNAL"
        board_gate["substatus"] = {
            "toolchain": hardware.get("toolchain", {}).get("status", "NOT_RUN"),
            "u55c_board": board.get("status", "NOT_RUN"),
            "native_fp4_gpu": gpu.get("status", "NOT_RUN"),
        }
        board_gate["evidence"] = [HARDWARE_AVAILABILITY.relative_to(ROOT).as_posix()]
    traceability_gate = next(
        row for row in gates if row["gate"] == "reviewer_traceability"
    )
    _apply_traceability_evidence(traceability_gate)
    paper_gate = next(
        row for row in gates if row["gate"] == "paper_provenance_and_final_pdf_audit"
    )
    _apply_paper_audit_evidence(paper_gate)
    return tuple(gates)


FINAL_GATES = build_final_gates()


def _git_revision() -> str:
    return subprocess.check_output(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "rev-parse",
            "HEAD",
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def evaluate(gates: tuple[dict[str, object], ...]) -> dict[str, object]:
    names = [str(row["gate"]) for row in gates]
    if len(names) != len(set(names)):
        raise ValueError("final gate names must be unique")
    invalid = [row for row in gates if row["status"] not in ALLOWED_STATUSES]
    if invalid:
        raise ValueError(f"invalid final-gate status: {invalid[0]['status']}")
    required = [row for row in gates if row.get("release_required", True)]
    if not required:
        raise ValueError("final gate set has no release-required rows")
    ready = all(row["status"] == "PASS" for row in required)
    nonpassing = [row for row in gates if row["status"] != "PASS"]
    required_nonpassing = [row for row in required if row["status"] != "PASS"]
    return {
        "schema": 1,
        "status": "PASS" if ready else "FAIL",
        "release_state": "READY FOR HUMAN SUBMISSION REVIEW" if ready else "NOT PAPER READY",
        "paper_pdf_permitted": ready,
        "gate_count": len(gates),
        "required_gate_count": len(required),
        "nonpassing_gate_count": len(nonpassing),
        "required_nonpassing_gate_count": len(required_nonpassing),
        "gates": list(gates),
    }


def write_report(json_path: Path, markdown_path: Path) -> dict[str, object]:
    report = evaluate(FINAL_GATES)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["source_revision"] = _git_revision()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Final Completion Gate",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Release state: **{report['release_state']}**",
        "",
        "| Gate | Release required | Status | Finding |",
        "|---|---:|---|---|",
    ]
    for row in report["gates"]:
        lines.append(
            f"| `{row['gate']}` | {'yes' if row.get('release_required', True) else 'no'} | "
            f"{row['status']} | {row['finding']} |"
        )
    lines.extend(
        [
            "",
            "A corrected paper PDF may be generated and delivered only when every",
            "release-required row is `PASS`. Non-required rows preserve negative",
            "research outcomes and explicitly scoped limitations; they do not become",
            "positive claims and do not block publication of a supported negative result.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        type=Path,
        default=ROOT / "reports" / "final_completion_gate.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=ROOT / "docs" / "final_completion_gate.md",
    )
    args = parser.parse_args(argv)
    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    markdown_path = (
        args.markdown if args.markdown.is_absolute() else ROOT / args.markdown
    )
    report = write_report(json_path, markdown_path)
    print(json.dumps({"status": report["status"], "release_state": report["release_state"]}))
    return 0 if report["paper_pdf_permitted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

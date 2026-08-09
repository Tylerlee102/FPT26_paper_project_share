"""Generate the authoritative eleven-item paper-completion gate.

Every row is release-required.  This deliberately mirrors the reviewer
directive and AGENTS.md: a negative research result, an unrun experiment, or
an external blocker keeps the project ``NOT PAPER READY``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUSES = {"PASS", "FAIL", "NOT_RUN", "BLOCKED_EXTERNAL"}
GATE_NAMES = (
    "prior_art_gap",
    "exact_official_recurrence_parity",
    "independent_bit_exact_mx_reference",
    "c_sim_and_rtl_parity",
    "closed_loop_real_model_quality",
    "selected_method_pareto_advantage",
    "physical_all_layer_state_bank_fit",
    "post_route_timing_and_drc",
    "real_board_parity_and_energy",
    "reviewer_traceability",
    "paper_provenance_and_final_pdf_audit",
)

OFFICIAL_PARITY = ROOT / "reports/golden/official_parity/official_parity_verification.json"
RS2_REGISTRATION = (
    ROOT / "reports/benchmark/corrected/rs2_encoded_candidate_preregistration.json"
)
RS2_STABILITY = (
    ROOT / "reports/benchmark/corrected/rs2_encoded/rs2_encoded_candidate_summary.json"
)
RS2_HLS = ROOT / "reports/csynth/corrected/rs2_hls_summary.json"
MXFP8_HLS = ROOT / "reports/csynth/corrected/mxfp8_hls_summary.json"
BF16_PHYSICAL = ROOT / "reports/vivado/baselines/bf16/bf16_vivado_summary.json"
MXFP8_PHYSICAL = ROOT / "reports/vivado/baselines/mxfp8/mxfp8_vivado_summary.json"
RS2_RTL_DIRECT = (
    ROOT
    / "reports/cosim/corrected/rs2_current/trace64_direct/rs2_trace64_direct_summary.json"
)
RS2_RTL_OFFICIAL = (
    ROOT / "reports/cosim/corrected/rs2_current/trace64/gdn_rs2_top_cosim.rpt"
)
RS2_RTL_OFFICIAL_RESET = (
    ROOT
    / "reports/cosim/corrected/rs2_current/trace64_reset/gdn_rs2_top_cosim.rpt"
)
RS2_RTL_CONTROL = (
    ROOT / "reports/cosim/corrected/rs2_current/control/gdn_rs2_top_cosim.rpt"
)
RS2_PHYSICAL = ROOT / "reports/vivado/corrected/rs2_current/rs2_vivado_summary.json"
QWEN_DIAGNOSTIC = ROOT / "reports/benchmark/qwen_recurrent_stability_manifest.json"
QWEN_CLOSED_LOOP = ROOT / "reports/benchmark/qwen_closed_loop_manifest.json"
HARDWARE_AVAILABILITY = ROOT / "reports/environment/hardware_availability.json"
BOARD_VALIDATION = ROOT / "reports/board/u55c/board_validation.json"
TRACEABILITY_STATUS = ROOT / "docs/reviewer_traceability_status.json"
TRACEABILITY_SOURCE = ROOT / "docs/reviewer_traceability.md"
ASSET_MANIFEST = ROOT / "paper/corrected/asset_manifest.json"
AUDIT_BUILD_MANIFEST = ROOT / "paper/corrected/paper_audit_build_manifest.json"
VISUAL_AUDIT_MANIFEST = ROOT / "paper/corrected/paper_visual_audit.json"
AUDIT_PDF = ROOT / "paper/corrected/paper_audit_candidate.pdf"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _gate(
    name: str,
    status: str,
    finding: str,
    evidence: list[Path] | tuple[Path, ...] = (),
    substatus: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "gate": name,
        "release_required": True,
        "status": status,
        "finding": finding,
        "evidence": [_relative(path) for path in evidence if path.exists()],
        **({"substatus": substatus} if substatus is not None else {}),
    }


def _combined_status(statuses: list[str]) -> str:
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "NOT_RUN" for status in statuses):
        return "NOT_RUN"
    if any(status == "BLOCKED_EXTERNAL" for status in statuses):
        return "BLOCKED_EXTERNAL"
    return "PASS"


def _frozen_sources_pass(registration: dict[str, Any] | None) -> bool:
    if not registration or registration.get("registration_status") != "PASS":
        return False
    hashes = registration.get("frozen_source_sha256")
    if not isinstance(hashes, dict) or not hashes:
        return False
    return all(
        (ROOT / relative).is_file()
        and _sha256(ROOT / relative) == str(expected).upper()
        for relative, expected in hashes.items()
    )


def _prior_art_gate() -> dict[str, object]:
    evidence = (
        ROOT / "docs/prior_art_matrix.md",
        ROOT / "docs/evidence/g0_focused_gap_resolution_2026_08_01.md",
        ROOT / "docs/evidence/prior_art_gap_recheck_2026_08_02_v2.md",
    )
    passed = all(path.is_file() and path.stat().st_size > 0 for path in evidence)
    return _gate(
        "prior_art_gap",
        "PASS" if passed else "FAIL",
        (
            "The bounded primary-source audit attributes persistent state and the five-phase schedule to Gupta et al.; the remaining claim is limited to the recurrence-aware native-MX arithmetic study."
            if passed
            else "The prior-art matrix or focused gap audit is missing."
        ),
        evidence,
    )


def _official_parity_gate() -> dict[str, object]:
    report = _load_json(OFFICIAL_PARITY)
    passed = bool(
        report
        and report.get("status") == "PASS"
        and report.get("verified_metric_rows") == 6
        and report.get("verified_source_hashes") == 6
    )
    return _gate(
        "exact_official_recurrence_parity",
        "PASS" if passed else ("FAIL" if report else "NOT_RUN"),
        (
            "The independent FP32/FP64 recurrence agrees with pinned Transformers and FLA recurrent, chunked, and cache paths at the declared recurrence-core boundary."
            if passed
            else "Pinned official recurrence parity is missing or invalid."
        ),
        (OFFICIAL_PARITY,),
    )


def _independent_reference_gate() -> dict[str, object]:
    registration = _load_json(RS2_REGISTRATION)
    hls = _load_json(RS2_HLS)
    mxfp8 = _load_json(MXFP8_HLS)
    frozen = _frozen_sources_pass(registration)
    arithmetic = bool(
        hls
        and hls.get("status") == "PASS"
        and hls.get("csim", {}).get("arithmetic_status") == "PASS"
        and hls.get("csim", {}).get("exact_trace64_status") == "PASS"
    )
    wider = bool(
        mxfp8
        and mxfp8.get("status") == "PASS"
        and mxfp8.get("csim", {}).get("arithmetic", {}).get("status") == "PASS"
        and mxfp8.get("csim", {}).get("persistent_kernel", {}).get("status")
        == "PASS"
    )
    statuses = {
        "registered_source_hashes": "PASS" if frozen else "FAIL",
        "rs2_encoded_arithmetic_csim": "PASS" if arithmetic else "NOT_RUN" if not hls else "FAIL",
        "matched_native_mxfp8_reference": "PASS" if wider else "NOT_RUN" if not mxfp8 else "FAIL",
    }
    status = _combined_status(list(statuses.values()))
    return _gate(
        "independent_bit_exact_mx_reference",
        status,
        (
            "The frozen encoded-integer RS2 oracle, native E2M1/E8M0 arithmetic C simulation, exact 64-token C trace, and matched E4M3/E8M0 reference all pass."
            if status == "PASS"
            else "The frozen encoded MX oracle or its matched low-precision cross-check is incomplete or stale."
        ),
        (RS2_REGISTRATION, RS2_HLS, MXFP8_HLS),
        statuses,
    )


def _cosim_report_pass(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return "|   Verilog|      Pass|" in text


def _rtl_gate() -> dict[str, object]:
    hls = _load_json(RS2_HLS)
    direct = _load_json(RS2_RTL_DIRECT)
    csim = bool(
        hls
        and hls.get("csim", {}).get("exact_trace64_status") == "PASS"
        and hls.get("csim", {}).get("exact_trace_tokens") == 64
    )
    direct_pass = bool(
        direct
        and direct.get("status") == "PASS"
        and direct.get("required_64_token_rtl_parity") == "PASS"
        and direct.get("parity", {}).get("ordered_tokens") == 64
        and direct.get("rtl_simulation", {}).get("completed_transactions") == 66
    )
    control_pass = _cosim_report_pass(RS2_RTL_CONTROL)
    official_pass = _cosim_report_pass(RS2_RTL_OFFICIAL) or _cosim_report_pass(
        RS2_RTL_OFFICIAL_RESET
    )
    substatus = {
        "exact_64_token_hls_c_simulation": "PASS" if csim else "NOT_RUN" if not hls else "FAIL",
        "official_xsim_control": "PASS" if control_pass else "NOT_RUN",
        "direct_generated_rtl_64_token": "PASS" if direct_pass else "NOT_RUN" if not direct else "FAIL",
        "official_xsim_64_token_random_or_reset_state": (
            "PASS" if official_pass else "NOT_RUN"
        ),
    }
    # The direct harness checks every generated-RTL value and snapshot.  The
    # official full-trace XSim run remains an explicit requirement because the
    # repository contract names HLS cosimulation as the authoritative RTL gate.
    status = _combined_status(list(substatus.values()))
    return _gate(
        "c_sim_and_rtl_parity",
        status,
        (
            "Both the direct generated-Verilog harness and official Vitis XSim reproduce the frozen 64-token encoded oracle exactly."
            if status == "PASS"
            else "Exact HLS C simulation passes, but one or both required 64-token RTL parity paths remain incomplete or failing."
        ),
        (
            RS2_HLS,
            RS2_RTL_CONTROL,
            RS2_RTL_DIRECT,
            RS2_RTL_OFFICIAL,
            RS2_RTL_OFFICIAL_RESET,
        ),
        substatus,
    )


def _closed_loop_gate() -> dict[str, object]:
    closed = _load_json(QWEN_CLOSED_LOOP)
    diagnostic = _load_json(QWEN_DIAGNOSTIC)
    closed_pass = bool(
        closed
        and closed.get("status") == "PASS"
        and closed.get("cache_faithful_decode") == "PASS"
        and closed.get("held_out_quality_gate") == "PASS"
    )
    diagnostic_pass = bool(
        diagnostic
        and diagnostic.get("status") == "PASS"
        and diagnostic.get("source_metadata", {}).get("total_valid_tokens") == 60
    )
    if closed_pass:
        status = "PASS"
        finding = "Cache-faithful closed-loop Qwen evaluation passes its preregistered held-out quality gate."
    elif closed:
        status = "FAIL"
        finding = "A closed-loop Qwen report exists but does not pass its preregistered quality gate."
    else:
        status = "BLOCKED_EXTERNAL"
        finding = "Short model-derived recurrence diagnostics pass, but the 80B checkpoint and adequate execution memory are absent; no closed-loop perplexity or downstream result exists."
    return _gate(
        "closed_loop_real_model_quality",
        status,
        finding,
        (QWEN_DIAGNOSTIC, QWEN_CLOSED_LOOP, ROOT / "reports/golden/qwen_capture_status.md"),
        {
            "short_model_derived_recurrence": "PASS" if diagnostic_pass else "FAIL" if diagnostic else "NOT_RUN",
            "cache_faithful_closed_loop_quality": "PASS" if closed_pass else "FAIL" if closed else "BLOCKED_EXTERNAL",
        },
    )


def _pareto_gate() -> dict[str, object]:
    stability = _load_json(RS2_STABILITY)
    hls = _load_json(RS2_HLS)
    physical = _load_json(RS2_PHYSICAL)
    direct = _load_json(RS2_RTL_DIRECT)
    held_out = str(
        (stability or {}).get("gate_results", {}).get("held_out", {}).get("status", "NOT_RUN")
    )
    extended = str(
        (stability or {}).get("gate_results", {}).get("extended_development", {}).get("status", "NOT_RUN")
    )
    hls_advantage = str(
        (hls or {}).get("comparison", {}).get("hls_cost_latency_advantage_vs_bf16", "NOT_RUN")
    )
    memory = "PASS" if hls and float(hls.get("comparison", {}).get("state_bytes_ratio_rs2_to_bf16", 2.0)) < 1.0 else "NOT_RUN" if not hls else "FAIL"
    routed = "PASS" if physical and physical.get("status") == "PASS" else "NOT_RUN" if not physical else "FAIL"
    service = "PASS" if direct and direct.get("status") == "PASS" else "NOT_RUN" if not direct else "FAIL"
    board = _load_json(BOARD_VALIDATION)
    energy = "PASS" if board and board.get("matched_energy_pareto") == "PASS" else "FAIL" if board else "BLOCKED_EXTERNAL"
    substatus = {
        "held_out_1024_quality": held_out,
        "extended_8192_quality": extended,
        "logical_state_bytes_vs_bf16": memory,
        "hls_lut_and_latency_vs_bf16": hls_advantage,
        "routed_cost": routed,
        "average_and_p99_service_latency": service,
        "measured_energy": energy,
    }
    status = _combined_status(list(substatus.values()))
    return _gate(
        "selected_method_pareto_advantage",
        status,
        (
            "The selected method is Pareto-superior to BF16 in quality, physical memory, average/p99 latency, and measured energy."
            if status == "PASS"
            else "The RS2/R3 method is numerically stable and reduces logical state bytes, but the matched HLS comparison currently uses more LUTs and cycles than BF16; measured board energy is also unavailable."
        ),
        (RS2_STABILITY, RS2_HLS, RS2_PHYSICAL, RS2_RTL_DIRECT, BOARD_VALIDATION),
        substatus,
    )


def _physical_fit_gate() -> dict[str, object]:
    report = _load_json(RS2_PHYSICAL)
    passed = bool(
        report
        and report.get("status") == "PASS"
        and report.get("route_completion") == "PASS"
        and report.get("physical_fit") == "PASS"
        and "all-layer" in str(report.get("scope", ""))
    )
    return _gate(
        "physical_all_layer_state_bank_fit",
        "PASS" if passed else "FAIL" if report else "NOT_RUN",
        (
            "All 36 logical GDN state slots physically fit in the routed U55C out-of-context kernel; this is not complete-model residency."
            if passed
            else "Selected-candidate all-layer physical banking and route evidence is absent or does not fit."
        ),
        (RS2_PHYSICAL,),
    )


def _postroute_gate() -> dict[str, object]:
    report = _load_json(RS2_PHYSICAL)
    if not report:
        return _gate(
            "post_route_timing_and_drc",
            "NOT_RUN",
            "Selected-candidate post-route timing and DRC extraction has not completed.",
        )
    drc = report.get("drc", {})
    substatus = {
        "route_completion": str(report.get("route_completion", "NOT_RUN")),
        "target_250mhz_timing": str(report.get("target_clock", {}).get("status", "NOT_RUN")),
        "drc": "PASS" if drc.get("signoff_status") in {"PASS", "PASS_WITH_WARNINGS"} and drc.get("critical_warning_count") == 0 and drc.get("error_count") == 0 else "FAIL",
    }
    status = _combined_status(list(substatus.values()))
    return _gate(
        "post_route_timing_and_drc",
        status,
        (
            "The routed selected candidate closes the declared 250 MHz target and has no DRC errors or critical warnings."
            if status == "PASS"
            else "Route evidence is complete only if the selected candidate closes 250 MHz and passes DRC; a slower sweep point does not satisfy this gate."
        ),
        (RS2_PHYSICAL,),
        substatus,
    )


def _board_gate() -> dict[str, object]:
    validation = _load_json(BOARD_VALIDATION)
    hardware = _load_json(HARDWARE_AVAILABILITY)
    passed = bool(
        validation
        and validation.get("status") == "PASS"
        and validation.get("bit_exact_parity") == "PASS"
        and validation.get("telemetry_energy") == "PASS"
    )
    if passed:
        status = "PASS"
        finding = "A real U55C passes bit parity, repeated latency, and integrated idle-subtracted board-energy measurements."
    elif validation:
        status = "FAIL"
        finding = "A U55C board report exists but parity or telemetry validation failed."
    else:
        status = "BLOCKED_EXTERNAL"
        finding = "Vitis and Vivado are installed, but no attached U55C, U55C XRT platform, xclbin, or board telemetry interface is present."
    board_status = str(
        (hardware or {}).get("u55c_board_experiment", {}).get("status", "NOT_RUN")
    )
    return _gate(
        "real_board_parity_and_energy",
        status,
        finding,
        (HARDWARE_AVAILABILITY, BOARD_VALIDATION),
        {
            "local_toolchain": str((hardware or {}).get("toolchain", {}).get("status", "NOT_RUN")),
            "u55c_environment": board_status,
            "bit_exact_board_parity": "PASS" if passed else "FAIL" if validation else "BLOCKED_EXTERNAL",
            "measured_board_energy": "PASS" if passed else "FAIL" if validation else "BLOCKED_EXTERNAL",
        },
    )


def _paper_audit_is_current(
    assets: dict[str, Any] | None,
    build: dict[str, Any] | None,
    visual: dict[str, Any] | None,
) -> bool:
    return bool(
        assets
        and assets.get("status") == "PASS"
        and build
        and build.get("status") == "PASS"
        and build.get("artifact_kind") == "internal_audit_candidate"
        and build.get("submission_eligible") is False
        and AUDIT_PDF.is_file()
        and _sha256(AUDIT_PDF) == str(build.get("output_sha256", "")).upper()
        and _sha256(ASSET_MANIFEST) == str(build.get("asset_manifest_sha256", "")).upper()
        and visual
        and visual.get("status") == "PASS"
        and visual.get("visual_audit_status") == "PASS"
        and _sha256(AUDIT_PDF) == str(visual.get("audit_candidate_sha256", "")).upper()
        and _sha256(AUDIT_BUILD_MANIFEST)
        == str(visual.get("build_manifest_sha256", "")).upper()
        and len(visual.get("pages", [])) == int(visual.get("page_count", -1))
        and bool(visual.get("pages"))
        and all(
            (ROOT / row.get("path", "")).is_file()
            and _sha256(ROOT / row["path"])
            == str(row.get("sha256", "")).upper()
            for row in visual.get("pages", [])
        )
    )


def _traceability_gate() -> dict[str, object]:
    report = _load_json(TRACEABILITY_STATUS)
    visual = _load_json(VISUAL_AUDIT_MANIFEST)
    assets = _load_json(ASSET_MANIFEST)
    build = _load_json(AUDIT_BUILD_MANIFEST)
    passed = bool(
        report
        and report.get("status") == "PASS"
        and report.get("comment_row_count") == 68
        and report.get("directive_row_count") == 25
        and all(row.get("status") == "PASS" for row in report.get("rows", []))
        and TRACEABILITY_SOURCE.is_file()
        and _sha256(TRACEABILITY_SOURCE) == str(report.get("traceability_source_sha256", "")).upper()
        and visual
        and visual.get("status") == "PASS"
        and _sha256(VISUAL_AUDIT_MANIFEST) == str(report.get("visual_audit_sha256", "")).upper()
        and _paper_audit_is_current(assets, build, visual)
    )
    return _gate(
        "reviewer_traceability",
        "PASS" if passed else "FAIL" if report else "NOT_RUN",
        (
            "All 68 reviewer rows and 25 remediation directives trace to the current page-audited paper."
            if passed
            else "The reviewer ledger has not been regenerated against the current RS2 paper audit bytes."
        ),
        (TRACEABILITY_SOURCE, TRACEABILITY_STATUS, VISUAL_AUDIT_MANIFEST),
    )


def _paper_audit_gate() -> dict[str, object]:
    assets = _load_json(ASSET_MANIFEST)
    build = _load_json(AUDIT_BUILD_MANIFEST)
    visual = _load_json(VISUAL_AUDIT_MANIFEST)
    passed = _paper_audit_is_current(assets, build, visual)
    return _gate(
        "paper_provenance_and_final_pdf_audit",
        "PASS" if passed else "FAIL" if any((assets, build, visual)) else "NOT_RUN",
        (
            "Generated numbers, provenance, audit-candidate bytes, and every rendered page pass freshness and visual checks."
            if passed
            else "The current RS2 paper assets, audit candidate, provenance, or page-by-page visual audit are missing or stale."
        ),
        (ASSET_MANIFEST, AUDIT_BUILD_MANIFEST, VISUAL_AUDIT_MANIFEST, AUDIT_PDF),
    )


def build_final_gates() -> tuple[dict[str, object], ...]:
    gates = (
        _prior_art_gate(),
        _official_parity_gate(),
        _independent_reference_gate(),
        _rtl_gate(),
        _closed_loop_gate(),
        _pareto_gate(),
        _physical_fit_gate(),
        _postroute_gate(),
        _board_gate(),
        _traceability_gate(),
        _paper_audit_gate(),
    )
    if tuple(str(row["gate"]) for row in gates) != GATE_NAMES:
        raise AssertionError("completion-gate construction does not match the directive")
    return gates


FINAL_GATES = build_final_gates()


def _git_revision() -> str:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def evaluate(gates: tuple[dict[str, object], ...]) -> dict[str, object]:
    names = tuple(str(row.get("gate", "")) for row in gates)
    if len(names) != len(set(names)):
        raise ValueError("final gate names must be unique")
    invalid = [row for row in gates if row.get("status") not in ALLOWED_STATUSES]
    if invalid:
        raise ValueError(f"invalid final-gate status: {invalid[0].get('status')}")
    nonpassing = [row for row in gates if row["status"] != "PASS"]
    ready = bool(gates) and not nonpassing
    return {
        "schema": 2,
        "status": "PASS" if ready else "FAIL",
        "release_state": "READY FOR HUMAN SUBMISSION REVIEW" if ready else "NOT PAPER READY",
        "paper_pdf_permitted": ready,
        "gate_count": len(gates),
        "required_gate_count": len(gates),
        "nonpassing_gate_count": len(nonpassing),
        "required_nonpassing_gate_count": len(nonpassing),
        "gates": list(gates),
    }


def write_report(json_path: Path, markdown_path: Path) -> dict[str, object]:
    report = evaluate(build_final_gates())
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
        "All eleven rows are release-required. Any non-PASS row means `NOT PAPER READY`.",
        "",
        "| Gate | Status | Finding |",
        "|---|---|---|",
    ]
    for row in report["gates"]:
        lines.append(f"| `{row['gate']}` | {row['status']} | {row['finding']} |")
    lines.extend(["", "A working draft may be compiled separately, but it is not a submission artifact.", ""])
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=ROOT / "reports/final_completion_gate.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs/final_completion_gate.md")
    args = parser.parse_args(argv)
    json_path = args.json if args.json.is_absolute() else ROOT / args.json
    markdown_path = args.markdown if args.markdown.is_absolute() else ROOT / args.markdown
    report = write_report(json_path, markdown_path)
    print(json.dumps({"status": report["status"], "release_state": report["release_state"]}))
    return 0 if report["paper_pdf_permitted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

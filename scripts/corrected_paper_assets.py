"""Generate paper-facing assets only from corrected, verified evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "reports" / "benchmark" / "corrected"
DEFAULT_OUTPUT = ROOT / "paper" / "corrected"
PAPER_SOURCE = DEFAULT_OUTPUT / "paper.tex"
LONG_CHECKPOINTS = BENCHMARK / "long_trace_checkpoints.csv"
NATIVE_CHECKPOINTS = BENCHMARK / "native_encoded_long_trace_checkpoints.csv"
SYNTHETIC = BENCHMARK / "synthetic_stability_verification.json"
UNIFORM_HLS = BENCHMARK / "hls_arithmetic_comparison.json"
E2M0_HLS = ROOT / "reports" / "csynth" / "corrected" / "e2m0_hls_summary.json"
HELD_OUT = BENCHMARK / "e2m0_encoded" / "held_out" / "held_out_summary.json"
SCALE_POLICY = BENCHMARK / "scale_policy_checkpoints.csv"
PREREGISTRATION = BENCHMARK / "e2m0_encoded_preregistration.json"
LONG_PLOT_MANIFEST = (
    ROOT / "paper" / "figures" / "corrected" / "long_trace_plot_manifest.json"
)
DATAPATH_MANIFEST = (
    ROOT
    / "paper"
    / "figures"
    / "corrected"
    / "corrected_candidate_datapath_manifest.json"
)
LONG_PANEL_MANIFEST = (
    ROOT
    / "paper"
    / "figures"
    / "corrected"
    / "long_sequence_stability_panel_manifest.json"
)
TRADEOFF_MANIFEST = (
    ROOT
    / "paper"
    / "figures"
    / "corrected"
    / "tradeoff_evidence_manifest.json"
)
STATE_CAPACITY = BENCHMARK / "state_capacity_lower_bound.json"
STRESS_SUMMARY = BENCHMARK / "stress" / "long_trace_stress_summary.csv"
STRESS_MANIFEST = (
    BENCHMARK / "stress" / "long_trace_stress_summary_manifest.json"
)
NUMERICAL_CONTRACT = ROOT / "docs" / "numerical_contract.md"
TRACE_PROTOCOL = ROOT / "docs" / "synthetic_trace_protocol.json"
EXTENDED = (
    BENCHMARK
    / "e2m0_encoded"
    / "extended_development"
    / "extended_summary.json"
)
BF16_CSYNTH_REPORT = (
    ROOT
    / "reports"
    / "csynth"
    / "corrected"
    / "bf16_current"
    / "report"
    / "gdn_bf16_top_impl_csynth.rpt"
)
NATIVE_CSYNTH_REPORT = (
    ROOT
    / "reports"
    / "csynth"
    / "corrected_attempt9_transport_pipeline_cleanup"
    / "report"
    / "gdn_top_impl_csynth.rpt"
)
CORRECTED_CSYNTH_REPORT = (
    ROOT
    / "reports"
    / "csynth"
    / "corrected"
    / "e2m0_r7_retime"
    / "report"
    / "gdn_e2m0_top_impl_csynth.rpt"
)
VIVADO_POSTROUTE = (
    ROOT
    / "reports"
    / "vivado"
    / "corrected"
    / "e2m0"
    / "e2m0_postroute_summary.json"
)
BF16_VIVADO = (
    ROOT / "reports" / "vivado" / "baselines" / "bf16" / "bf16_vivado_summary.json"
)
MXFP8_VIVADO = (
    ROOT / "reports" / "vivado" / "baselines" / "mxfp8" / "mxfp8_vivado_summary.json"
)
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
QWEN_CHARACTERIZATION = (
    ROOT / "reports" / "golden" / "qwen_capture_characterization.json"
)
QWEN_RECURRENT = (
    ROOT / "reports" / "benchmark" / "qwen_recurrent_stability_manifest.json"
)
REQUIRED_LENGTHS = (64, 256, 1024, 4096, 8192)
STATE_REL_L2_SENSITIVITY_PROBE = 0.09
QDQ_DISPLAY_VARIANTS = (
    "bf16_qdq_fp32_accum_state_bf16",
    "mxfp4_qdq_act_b32_state_b32",
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32",
    "flat_int4_qdq",
)
STRESS_VARIANTS = ("fp32", *QDQ_DISPLAY_VARIANTS)
DISPLAY_VARIANTS = (
    "bf16_qdq_fp32_accum_state_bf16",
    "mxfp4_qdq_act_b32_state_b32",
    "native_mxfp4_encoded_act_b32_state_b32",
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32",
    "flat_int4_qdq",
)
DISPLAY_NAMES = {
    "bf16_qdq_fp32_accum_state_bf16": "BF16 state/operands",
    "mxfp4_qdq_act_b32_state_b32": "MXFP4 floating Q/DQ",
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32": "MXFP4 Q/DQ + MXFP8-E4M3 state",
    "flat_int4_qdq": "Flat INT4",
    "native_mxfp4_encoded_act_b32_state_b32": "Native encoded MXFP4",
}
QWEN_RECURRENT_NAMES = {
    "bf16_qdq_fp32_accum_state_bf16": "BF16 state/operands",
    "mxfp4_qdq_state_mxfp4_b32": "MXFP4 state/operands",
    "mxfp4_qdq_state_mxfp8_b32": "MXFP4 operands + MXFP8 state",
    "flat_int4_qdq": "Flat INT4",
    "mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5": (
        "Native MXFP4 RS2/R3"
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _git_revision() -> str:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _line(path: Path, marker: str) -> int:
    for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if marker in text:
            return number
    raise ValueError(f"marker {marker!r} is absent from {path}")


def _load_json(path: Path, *, require_pass: bool = True) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if require_pass and payload.get("status") != "PASS":
        raise ValueError(f"corrected evidence extraction is not PASS: {path}")
    return payload


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _escape(value: object) -> str:
    return str(value).replace("_", r"\_").replace("%", r"\%")


def _number(
    numbers: dict[str, dict[str, object]],
    provenance: dict[str, dict[str, object]],
    *,
    key: str,
    value: object,
    units: str,
    source: Path,
    marker: str,
    revision: str,
    timestamp: str,
) -> None:
    relative = _display_path(source)
    row = {
        "value": value,
        "units": units,
        "source": relative,
        "source_line": _line(source, marker),
        "extractor": "scripts.corrected_paper_assets",
        "git_sha": revision,
        "timestamp": timestamp,
    }
    numbers[key] = row
    provenance[key] = dict(row)


def _resource_lut(path: Path, module: str) -> tuple[int, int]:
    """Return the LUT count and one-based line from an HLS hierarchy row."""
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 9 or cells[2] != module:
            continue
        try:
            resources = [int(cell.replace(",", "")) for cell in cells[3:8]]
        except ValueError:
            continue
        return resources[3], line_number
    raise ValueError(f"resource row for {module!r} is absent from {path}")


def _number_at_line(
    numbers: dict[str, dict[str, object]],
    provenance: dict[str, dict[str, object]],
    *,
    key: str,
    value: object,
    units: str,
    source: Path,
    source_line: int,
    revision: str,
    timestamp: str,
) -> None:
    relative = _display_path(source)
    row = {
        "value": value,
        "units": units,
        "source": relative,
        "source_line": source_line,
        "extractor": "scripts.corrected_paper_assets",
        "git_sha": revision,
        "timestamp": timestamp,
    }
    numbers[key] = row
    provenance[key] = dict(row)


def _format(value: object, digits: int = 6) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _tex_integer(value: object) -> str:
    return f"{int(value):,}".replace(",", r"{,}")


def generate(output: Path) -> dict[str, object]:
    required = (
        LONG_CHECKPOINTS,
        NATIVE_CHECKPOINTS,
        SYNTHETIC,
        UNIFORM_HLS,
        E2M0_HLS,
        HELD_OUT,
        SCALE_POLICY,
        PREREGISTRATION,
        LONG_PLOT_MANIFEST,
        DATAPATH_MANIFEST,
        LONG_PANEL_MANIFEST,
        TRADEOFF_MANIFEST,
        STATE_CAPACITY,
        STRESS_SUMMARY,
        STRESS_MANIFEST,
        NUMERICAL_CONTRACT,
        TRACE_PROTOCOL,
        PAPER_SOURCE,
        BF16_CSYNTH_REPORT,
        NATIVE_CSYNTH_REPORT,
        CORRECTED_CSYNTH_REPORT,
        VIVADO_POSTROUTE,
        BF16_VIVADO,
        MXFP8_VIVADO,
        E2M0_CONTROL_COSIM,
        E2M0_TRACE_COSIM,
        QWEN_CHARACTERIZATION,
        QWEN_RECURRENT,
    )
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    _load_json(SYNTHETIC)
    uniform_hls = _load_json(UNIFORM_HLS)
    e2m0_hls = _load_json(E2M0_HLS)
    postroute = _load_json(VIVADO_POSTROUTE)
    bf16_vivado = _load_json(BF16_VIVADO)
    mxfp8_vivado = _load_json(MXFP8_VIVADO)
    control_cosim = _load_json(E2M0_CONTROL_COSIM)
    trace_cosim = _load_json(E2M0_TRACE_COSIM, require_pass=False)
    qwen_characterization = _load_json(QWEN_CHARACTERIZATION)
    qwen_recurrent = _load_json(QWEN_RECURRENT)
    held_out = _load_json(HELD_OUT)
    preregistration = _load_json(PREREGISTRATION, require_pass=False)
    plot_manifest = _load_json(LONG_PLOT_MANIFEST)
    datapath_manifest = _load_json(DATAPATH_MANIFEST)
    long_panel_manifest = _load_json(LONG_PANEL_MANIFEST)
    tradeoff_manifest = _load_json(TRADEOFF_MANIFEST)
    state_capacity = _load_json(STATE_CAPACITY)
    stress_manifest = _load_json(STRESS_MANIFEST)
    trace_protocol = _load_json(TRACE_PROTOCOL)
    long_rows = _read_csv(LONG_CHECKPOINTS)
    native_rows = _read_csv(NATIVE_CHECKPOINTS)
    scale_rows = _read_csv(SCALE_POLICY)
    stress_rows = _read_csv(STRESS_SUMMARY)
    expected_pairs = {
        (length, variant) for length in REQUIRED_LENGTHS for variant in DISPLAY_VARIANTS
    }
    selected = {
        (int(row["token_index"]), row["variant"]): row
        for row in long_rows
        if row["variant"] in QDQ_DISPLAY_VARIANTS
    }
    selected.update(
        {
            (int(row["token_index"]), row["variant"]): row
            for row in native_rows
            if row["variant"] == "native_mxfp4_encoded_act_b32_state_b32"
        }
    )
    if set(selected) != expected_pairs:
        raise ValueError("long-trace CSV does not contain the controlled comparison grid")
    if held_out.get("full_deterministic_recompute") != "PASS":
        raise ValueError("corrected held-out evidence is not fully recomputed")
    if preregistration.get("registration_status") != "PASS":
        raise ValueError("corrected-candidate preregistration is not PASS")
    for relative, expected in plot_manifest["outputs"].items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != str(expected).upper():
            raise ValueError(f"corrected plot hash mismatch: {relative}")
    for relative, expected in datapath_manifest["outputs"].items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != str(expected).upper():
            raise ValueError(f"corrected datapath hash mismatch: {relative}")
    if not datapath_manifest.get("source_identity", {}).get("dirty_patch", {}).get(
        "sha256"
    ):
        raise ValueError("corrected datapath source identity is absent")
    if long_panel_manifest.get("upstream_manifest_sha256", "").upper() != _sha256(
        LONG_PLOT_MANIFEST
    ):
        raise ValueError("corrected long-panel upstream manifest is stale")
    for relative, expected in long_panel_manifest["outputs"].items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != str(expected).upper():
            raise ValueError(f"corrected long-panel hash mismatch: {relative}")
    for relative, expected in tradeoff_manifest["outputs"].items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != str(expected).upper():
            raise ValueError(f"corrected trade-off figure hash mismatch: {relative}")
    if stress_manifest.get("evidence_scope") != (
        "supplemental_synthetic_floating_qdq_stress"
    ):
        raise ValueError("long-trace stress evidence has the wrong scope")
    if int(stress_manifest.get("row_count", -1)) != 2 * len(STRESS_VARIANTS):
        raise ValueError("long-trace stress summary has the wrong row count")
    for relative, expected in stress_manifest["outputs"].items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != str(expected).upper():
            raise ValueError(f"long-trace stress hash mismatch: {relative}")
    expected_stress_pairs = {
        (family, variant)
        for family in ("dynamic_range", "cancellation")
        for variant in STRESS_VARIANTS
    }
    observed_stress_pairs = {
        (row["trace_family"], row["variant"]) for row in stress_rows
    }
    if observed_stress_pairs != expected_stress_pairs:
        raise ValueError("long-trace stress CSV does not contain the controlled grid")
    if postroute.get("physical_fit") != "PASS":
        raise ValueError("corrected candidate does not have a physical-fit PASS")
    if (
        bf16_vivado.get("physical_fit") != "PASS"
        or bf16_vivado.get("placement_completion") != "PASS"
        or bf16_vivado.get("route_completion") != "PASS"
        or bf16_vivado.get("first_tested_closing_point", {}).get("status") != "PASS"
    ):
        raise ValueError("matched BF16 post-route evidence must preserve its physical-fit PASS")
    if mxfp8_vivado.get("physical_fit") != "PASS":
        raise ValueError("matched native-MXFP8 implementation must physically fit")
    if control_cosim.get("recurrent_transition_covered") is not False:
        raise ValueError("control-smoke scope no longer matches its registered boundary")
    if (
        trace_cosim.get("status") != "PARTIAL"
        or trace_cosim.get("required_64_token_rtl_parity") != "NOT_ESTABLISHED"
        or trace_cosim.get("hls_c_simulation", {}).get("status") != "PASS"
        or trace_cosim.get("direct_generated_rtl_load", {}).get("status") != "PASS"
        or trace_cosim.get("rtl_simulation", {}).get("completed_recurrent_steps") != 0
    ):
        raise ValueError("corrected-candidate RTL completion boundary is stale")
    if qwen_characterization.get("recurrence_coverage", {}).get("complete") is not False:
        raise ValueError("Qwen characterization must not claim recurrent coverage")
    if set(qwen_recurrent.get("aggregate", {})) != set(QWEN_RECURRENT_NAMES):
        raise ValueError("Qwen recurrence evidence does not contain the controlled variants")
    if qwen_recurrent.get("arithmetic_boundary") != (
        "exact_rs2_plus_floating_qdq_recurrence_diagnostic"
    ):
        raise ValueError("Qwen recurrence evidence has the wrong arithmetic boundary")

    timestamp = datetime.now(timezone.utc).isoformat()
    source_identity = describe_source_files(
        [
            Path(__file__),
            ROOT / "paper" / "corrected" / "paper.tex",
            NUMERICAL_CONTRACT,
        ]
    )
    revision = str(source_identity["git_revision"])
    if revision != _git_revision():
        raise ValueError("source-identity revision changed during asset generation")
    numbers: dict[str, dict[str, object]] = {}
    provenance: dict[str, dict[str, object]] = {}

    capacity_rows = {row["variant"]: row for row in state_capacity["rows"]}
    capacity_variants = {
        "bf16": "BF16",
        "uniform_mxfp4": "uniform_mxfp4_e2m1_e8m0_b32",
        "mxfp8": "mxfp8_e4m3_e8m0_b32",
        "flat_int4": "flat_int4",
    }
    if set(capacity_rows) != set(capacity_variants.values()):
        raise ValueError("state-capacity report does not contain the controlled variants")
    if int(state_capacity["configuration"]["num_layers"]) != int(
        uniform_hls["controlled_configuration"]["num_layers"]
    ):
        raise ValueError("state-capacity and HLS layer counts differ")
    if (
        state_capacity["physical_all_layer_state_bank_fit"]
        != "SEE_PHYSICAL_FIT_BY_VARIANT"
    ):
        raise ValueError("all-layer physical fit must be resolved per controlled variant")

    for prefix, variant in capacity_variants.items():
        row = capacity_rows[variant]
        marker = f'"variant": "{variant}"'
        for suffix, value, units in (
            ("all_layer_logical_state_bytes", row["logical_state_bytes"], "bytes"),
            (
                "all_layer_logical_state_mib",
                float(row["logical_state_bytes"]) / (1024.0 * 1024.0),
                "MiB",
            ),
            (
                "ideal_min_uram_for_mantissas",
                row["ideal_min_uram_for_mantissas"],
                "URAM288",
            ),
            (
                "ideal_min_bram18k_for_scales",
                row["ideal_min_bram18k_for_scales"],
                "BRAM18K",
            ),
            (
                "raw_bit_capacity_necessary_condition",
                row["raw_bit_capacity_necessary_condition"],
                "status",
            ),
        ):
            _number(
                numbers,
                provenance,
                key=f"{prefix}_{suffix}",
                value=value,
                units=units,
                source=STATE_CAPACITY,
                marker=marker,
                revision=revision,
                timestamp=timestamp,
            )
    _number(
        numbers,
        provenance,
        key="u55c_available_uram",
        value=state_capacity["available_device_resources"]["URAM"],
        units="URAM288",
        source=STATE_CAPACITY,
        marker='"URAM": 960',
        revision=revision,
        timestamp=timestamp,
    )

    for key, value, units, marker in (
        (
            "bf16_physical_fit_status",
            bf16_vivado["physical_fit"],
            "status",
            '"physical_fit":',
        ),
        (
            "bf16_placement_completion_status",
            bf16_vivado["placement_completion"],
            "status",
            '"placement_completion":',
        ),
        (
            "bf16_route_completion_status",
            bf16_vivado["route_completion"],
            "status",
            '"route_completion":',
        ),
        (
            "bf16_target_250mhz_status",
            bf16_vivado["target_clock"]["status"],
            "status",
            '"target_clock":',
        ),
        (
            "bf16_target_250mhz_wns_ns",
            bf16_vivado["target_clock"]["timing"]["wns_ns"],
            "ns",
            f'"wns_ns": {bf16_vivado["target_clock"]["timing"]["wns_ns"]}',
        ),
        (
            "bf16_first_tested_closing_period_ns",
            bf16_vivado["first_tested_closing_point"]["period_ns"],
            "ns",
            f'"period_ns": {bf16_vivado["first_tested_closing_point"]["period_ns"]}',
        ),
        (
            "bf16_first_tested_closing_frequency_mhz",
            bf16_vivado["first_tested_closing_point"]["frequency_mhz"],
            "MHz",
            f'"frequency_mhz": {bf16_vivado["first_tested_closing_point"]["frequency_mhz"]}',
        ),
        (
            "bf16_routed_clb_lut",
            bf16_vivado["utilization"]["clb_luts"]["used"],
            "CLB_LUT",
            '"clb_luts":',
        ),
        (
            "bf16_routed_ff",
            bf16_vivado["utilization"]["clb_registers"]["used"],
            "FF",
            '"clb_registers":',
        ),
        (
            "bf16_routed_bram_tiles",
            bf16_vivado["utilization"]["block_ram_tiles"]["used"],
            "BRAM_tile",
            '"block_ram_tiles":',
        ),
        (
            "bf16_routed_uram",
            bf16_vivado["utilization"]["uram"]["used"],
            "URAM288",
            '"uram":',
        ),
        (
            "bf16_routed_dsp",
            bf16_vivado["utilization"]["dsps"]["used"],
            "DSP",
            '"dsps":',
        ),
        (
            "bf16_vectorless_power_first_closing_w",
            bf16_vivado["vectorless_power"]["total_on_chip_w"],
            "W",
            f'"total_on_chip_w": {bf16_vivado["vectorless_power"]["total_on_chip_w"]}',
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=BF16_VIVADO,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )
    _number(
        numbers,
        provenance,
        key="physical_all_layer_state_bank_fit",
        value=state_capacity["physical_all_layer_state_bank_fit"],
        units="status",
        source=STATE_CAPACITY,
        marker='"physical_all_layer_state_bank_fit":',
        revision=revision,
        timestamp=timestamp,
    )

    stress_prefixes = {
        "fp32": "fp32",
        "bf16_qdq_fp32_accum_state_bf16": "bf16",
        "mxfp4_qdq_act_b32_state_b32": "qdq_mxfp4",
        "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32": "mxfp8_state",
        "flat_int4_qdq": "flat_int4",
    }
    for row in stress_rows:
        family = row["trace_family"]
        variant = row["variant"]
        marker = f"{family},{variant},"
        prefix = f"stress_{family}_{stress_prefixes[variant]}"
        for suffix, value, units in (
            ("final_output_cosine", float(row["final_output_cosine_fp32"]), "cosine"),
            ("final_state_relative_l2", float(row["final_state_rel_l2"]), "relative_l2"),
            ("final_state_max_abs", float(row["final_state_max_abs"]), "absolute"),
            ("worst_output_cosine", float(row["worst_output_cosine_fp32"]), "cosine"),
            ("worst_state_relative_l2", float(row["worst_state_rel_l2"]), "relative_l2"),
            ("full_trace_threshold_status", row["full_trace_threshold_status"], "status"),
        ):
            _number(
                numbers,
                provenance,
                key=f"{prefix}_{suffix}",
                value=value,
                units=units,
                source=STRESS_SUMMARY,
                marker=marker,
                revision=revision,
                timestamp=timestamp,
            )

    for variant in DISPLAY_VARIANTS:
        prefix = {
            "bf16_qdq_fp32_accum_state_bf16": "bf16",
            "mxfp4_qdq_act_b32_state_b32": "qdq_mxfp4",
            "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32": "mxfp8_state",
            "flat_int4_qdq": "flat_int4",
            "native_mxfp4_encoded_act_b32_state_b32": "native_encoded_mxfp4",
        }[variant]
        source = (
            NATIVE_CHECKPOINTS
            if variant == "native_mxfp4_encoded_act_b32_state_b32"
            else LONG_CHECKPOINTS
        )
        for length in REQUIRED_LENGTHS:
            row = selected[(length, variant)]
            csv_marker = f",{variant},0,{length},"
            _number(
                numbers,
                provenance,
                key=f"{prefix}_token_{length}_output_cosine",
                value=float(row["output_cosine_fp32"]),
                units="cosine_similarity",
                source=source,
                marker=csv_marker,
                revision=revision,
                timestamp=timestamp,
            )
            _number(
                numbers,
                provenance,
                key=f"{prefix}_token_{length}_state_relative_l2",
                value=float(row["state_rel_l2"]),
                units="relative_l2",
                source=source,
                marker=csv_marker,
                revision=revision,
                timestamp=timestamp,
            )

    native_final = selected[(8192, "native_mxfp4_encoded_act_b32_state_b32")]
    _number(
        numbers,
        provenance,
        key="native_encoded_mxfp4_token_8192_alignment_underflows",
        value=int(native_final["cumulative_alignment_underflows"]),
        units="events",
        source=NATIVE_CHECKPOINTS,
        marker=",native_mxfp4_encoded_act_b32_state_b32,0,8192,",
        revision=revision,
        timestamp=timestamp,
    )

    uniform_rows = {row["variant"]: row for row in uniform_hls["rows"]}
    e2m0_rows = {row["variant"]: row for row in e2m0_hls["comparison_rows"]}
    candidate_name = str(e2m0_hls["candidate_name"])
    hls_specs = (
        ("bf16", uniform_rows["BF16"], UNIFORM_HLS, '"variant": "BF16"'),
        (
            "uniform_mxfp4",
            uniform_rows["uniform_mxfp4"],
            UNIFORM_HLS,
            '"variant": "uniform_mxfp4"',
        ),
        (
            "native_mxfp8",
            uniform_rows["native_mxfp8"],
            UNIFORM_HLS,
            '"variant": "native_mxfp8"',
        ),
        (
            "corrected_candidate",
            e2m0_rows[candidate_name],
            E2M0_HLS,
            f'"variant": "{candidate_name}"',
        ),
    )
    for prefix, row, source, marker in hls_specs:
        mapping = {
            "hls_estimated_clock_ns": ("estimated_clock_ns", "ns"),
            "hls_lut": ("lut", "LUT"),
            "hls_ff": ("ff", "FF"),
            "hls_bram18k": ("bram_18k", "BRAM18K"),
            "hls_reported_uram": (
                "uram" if prefix != "corrected_candidate" else "uram_reported",
                "URAM",
            ),
            "hls_dsp": ("dsp", "DSP"),
            "hls_step_cycles_max": (
                "step_cycles_max"
                if prefix != "corrected_candidate"
                else "nonfold_step_cycles_max",
                "cycles",
            ),
        }
        for suffix, (field, units) in mapping.items():
            _number(
                numbers,
                provenance,
                key=f"{prefix}_{suffix}",
                value=row[field],
                units=units,
                source=source,
                marker=marker,
                revision=revision,
                timestamp=timestamp,
            )

        for field, units in (
            ("logical_state_bytes_per_layer", "bytes_per_layer"),
            ("nonfold_step_cycles_max", "cycles"),
            ("amortized_cycles_max", "cycles_per_token"),
        ):
            if field in row:
                _number(
                    numbers,
                    provenance,
                    key=f"{prefix}_{field}",
                    value=row[field],
                    units=units,
                    source=E2M0_HLS,
                    marker=marker,
                    revision=revision,
                    timestamp=timestamp,
                )

    for key, field in (
        ("uniform_mxfp4_to_bf16_lut_ratio", "mxfp4_to_bf16_lut"),
        (
            "uniform_mxfp4_to_bf16_step_cycles_max_ratio",
            "mxfp4_to_bf16_step_cycles_max",
        ),
        ("native_mxfp8_to_bf16_lut_ratio", "mxfp8_to_bf16_lut"),
        (
            "native_mxfp8_to_bf16_step_cycles_max_ratio",
            "mxfp8_to_bf16_step_cycles_max",
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=uniform_hls["ratios"][field],
            units="ratio",
            source=UNIFORM_HLS,
            marker=f'"{field}":',
            revision=revision,
            timestamp=timestamp,
        )

    for key, field in (
        ("corrected_candidate_to_bf16_lut_ratio", "candidate_to_bf16_lut"),
        (
            "corrected_candidate_to_bf16_nonfold_step_ratio",
            "candidate_to_bf16_nonfold_step_cycles_max",
        ),
        (
            "corrected_candidate_to_bf16_amortized_step_ratio",
            "candidate_to_bf16_amortized_cycles_max",
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=e2m0_hls["ratios"][field],
            units="ratio",
            source=E2M0_HLS,
            marker=f'"{field}":',
            revision=revision,
            timestamp=timestamp,
        )

    failed_targeted_loops = e2m0_hls["csynth"]["failed_targeted_loops"]
    target_iis = {int(loop["target_ii"]) for loop in failed_targeted_loops}
    final_iis = {int(loop["final_ii"]) for loop in failed_targeted_loops}
    if not failed_targeted_loops or target_iis != {1} or final_iis != {2}:
        raise ValueError(
            "failed targeted loops do not share the reported II=1 to II=2 result"
        )

    hls_scalar_fields = (
        (
            "corrected_arithmetic_csim_cases",
            e2m0_hls["csim"]["arithmetic_267_case_status"],
            "cases",
            '"arithmetic_267_case_status":',
            267,
        ),
        (
            "corrected_stateful_csim_tokens",
            e2m0_hls["csim"]["exact_random_state_trace_tokens"],
            "tokens",
            '"exact_random_state_trace_tokens":',
            e2m0_hls["csim"]["exact_random_state_trace_tokens"],
        ),
        (
            "corrected_failed_ii_one_loop_count",
            failed_targeted_loops,
            "loops",
            '"failed_targeted_loops":',
            len(failed_targeted_loops),
        ),
        (
            "corrected_target_loop_ii",
            failed_targeted_loops,
            "cycles_per_iteration",
            '"target_ii":',
            next(iter(target_iis)),
        ),
        (
            "corrected_failed_loop_final_ii",
            failed_targeted_loops,
            "cycles_per_iteration",
            '"final_ii":',
            next(iter(final_iis)),
        ),
        (
            "corrected_fold_period_tokens",
            e2m0_hls["csynth"]["fold_period_tokens"],
            "tokens",
            '"fold_period_tokens":',
            e2m0_hls["csynth"]["fold_period_tokens"],
        ),
        (
            "corrected_reported_one_slr_lut_percent",
            e2m0_hls["csynth"]["slr_utilization_percent_reported"]["LUT"],
            "percent",
            '"slr_utilization_percent_reported":',
            e2m0_hls["csynth"]["slr_utilization_percent_reported"]["LUT"],
        ),
        (
            "corrected_fold_burst_cycles_max",
            e2m0_hls["csynth"]["fold_latency_cycles"]["maximum"],
            "cycles_per_fold_command",
            '"fold_latency_cycles":',
            e2m0_hls["csynth"]["fold_latency_cycles"]["maximum"],
        ),
        (
            "corrected_top_command_cycles_max",
            e2m0_hls["csynth"]["metrics"]["latency_cycles_max"],
            "cycles_per_command",
            '"latency_cycles_max":',
            e2m0_hls["csynth"]["metrics"]["latency_cycles_max"],
        ),
    )
    for key, _raw, units, marker, value in hls_scalar_fields:
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=E2M0_HLS,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    timing_metrics = e2m0_hls["csynth"]["metrics"]
    effective_timing_budget_ns = float(timing_metrics["target_clock_ns"]) - float(
        timing_metrics["clock_uncertainty_ns"]
    )
    timing_shortfall_ns = float(timing_metrics["estimated_clock_ns"]) - effective_timing_budget_ns
    for key, value, units, marker in (
        (
            "corrected_effective_hls_timing_budget_ns",
            effective_timing_budget_ns,
            "ns",
            '"clock_uncertainty_ns":',
        ),
        (
            "corrected_configured_hls_timing_shortfall_ns",
            timing_shortfall_ns,
            "ns",
            '"estimated_clock_ns":',
        ),
        (
            "corrected_configured_hls_timing_margin_status",
            "PASS" if timing_shortfall_ns <= 0.0 else "FAIL",
            "status",
            '"estimated_clock_ns":',
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=E2M0_HLS,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    hierarchy_specs = (
        (
            "bf16_state_update_lut",
            BF16_CSYNTH_REPORT,
            "p_anonymous_namespace_phase4_update_state_tile",
            int(uniform_rows["BF16"]["lut"]),
        ),
        (
            "native_encoded_state_update_lut",
            NATIVE_CSYNTH_REPORT,
            "phase4_update_state_tile",
            int(uniform_rows["uniform_mxfp4"]["lut"]),
        ),
        (
            "corrected_fold_log_lut",
            CORRECTED_CSYNTH_REPORT,
            "p_anonymous_namespace_fold_log",
            int(e2m0_rows[candidate_name]["lut"]),
        ),
        (
            "corrected_update_quantizer_lut",
            CORRECTED_CSYNTH_REPORT,
            "p_anonymous_namespace_quantize_update_block",
            int(e2m0_rows[candidate_name]["lut"]),
        ),
    )
    hierarchy_values: dict[str, int] = {}
    hierarchy_lines: dict[str, int] = {}
    hierarchy_sources: dict[str, Path] = {}
    hierarchy_top_luts: dict[str, int] = {}
    for key, source, module, top_lut in hierarchy_specs:
        value, source_line = _resource_lut(source, module)
        hierarchy_values[key] = value
        hierarchy_lines[key] = source_line
        hierarchy_sources[key] = source
        hierarchy_top_luts[key] = top_lut
        _number_at_line(
            numbers,
            provenance,
            key=key,
            value=value,
            units="LUT",
            source=source,
            source_line=source_line,
            revision=revision,
            timestamp=timestamp,
        )
        _number_at_line(
            numbers,
            provenance,
            key=f"{key}_percent_of_top",
            value=100.0 * value / top_lut,
            units="percent",
            source=source,
            source_line=source_line,
            revision=revision,
            timestamp=timestamp,
        )

    correction_machinery_lut = (
        hierarchy_values["corrected_fold_log_lut"]
        + hierarchy_values["corrected_update_quantizer_lut"]
    )
    _number_at_line(
        numbers,
        provenance,
        key="corrected_correction_machinery_lut",
        value=correction_machinery_lut,
        units="LUT",
        source=CORRECTED_CSYNTH_REPORT,
        source_line=hierarchy_lines["corrected_fold_log_lut"],
        revision=revision,
        timestamp=timestamp,
    )
    _number_at_line(
        numbers,
        provenance,
        key="corrected_correction_machinery_lut_percent_of_top",
        value=100.0 * correction_machinery_lut / int(e2m0_rows[candidate_name]["lut"]),
        units="percent",
        source=CORRECTED_CSYNTH_REPORT,
        source_line=hierarchy_lines["corrected_fold_log_lut"],
        revision=revision,
        timestamp=timestamp,
    )

    held_out_fields = {
        "corrected_heldout_min_checkpoint_output_cosine": (
            "minimum_registered_checkpoint_output_cosine",
            "cosine_similarity",
        ),
        "corrected_heldout_min_all_token_output_cosine": (
            "minimum_all_token_output_cosine",
            "cosine_similarity",
        ),
        "corrected_heldout_max_final_state_relative_l2": (
            "maximum_final_state_relative_l2",
            "relative_l2",
        ),
        "corrected_heldout_max_all_token_state_relative_l2": (
            "maximum_all_token_state_relative_l2",
            "relative_l2",
        ),
        "corrected_heldout_max_state_abs_error": (
            "maximum_all_token_state_abs_error",
            "absolute_error",
        ),
        "corrected_logical_state_bytes": ("logical_state_bytes", "bytes_per_layer"),
        "corrected_total_element_saturations": (
            "total_element_saturations",
            "events",
        ),
        "corrected_total_accumulator_saturations": (
            "total_accumulator_saturations",
            "events",
        ),
        "corrected_total_scale_clamps": ("total_scale_clamps", "events"),
        "corrected_heldout_run_count": ("run_count", "traces"),
        "corrected_heldout_seed_block_count": ("seed_block_count", "seed_blocks"),
        "corrected_heldout_paired_condition_count": (
            "paired_condition_count",
            "paired_conditions",
        ),
        "corrected_uniform_mxfp8_state_bytes": (
            "uniform_mxfp8_state_bytes",
            "bytes_per_layer",
        ),
        "corrected_bytes_below_uniform_mxfp8": (
            "bytes_below_uniform_mxfp8",
            "bytes_per_layer",
        ),
        "corrected_percent_below_uniform_mxfp8": (
            "percent_below_uniform_mxfp8",
            "percent",
        ),
    }
    for key, (field, units) in held_out_fields.items():
        _number(
            numbers,
            provenance,
            key=key,
            value=held_out[field],
            units=units,
            source=HELD_OUT,
            marker=f'"{field}":',
            revision=revision,
            timestamp=timestamp,
        )

    total_hard_events = sum(
        int(held_out[field])
        for field in (
            "total_element_saturations",
            "total_accumulator_saturations",
            "total_scale_clamps",
        )
    )
    _number(
        numbers,
        provenance,
        key="corrected_total_preregistered_hard_events",
        value=total_hard_events,
        units="events",
        source=HELD_OUT,
        marker='"total_element_saturations":',
        revision=revision,
        timestamp=timestamp,
    )

    final_scale_rows = [row for row in scale_rows if int(row["token_index"]) == 8192]
    for row in final_scale_rows:
        prefix = row["variant"].removeprefix("mxfp4_scale_")
        marker = f",{row['variant']},{row['policy']},"
        for field, units in (
            ("output_cosine_fp32", "cosine_similarity"),
            ("state_rel_l2", "relative_l2"),
            ("state_element_saturations_cumulative", "events"),
            ("state_scale_changes_cumulative", "events"),
        ):
            _number(
                numbers,
                provenance,
                key=f"scale_policy_{prefix}_token_8192_{field}",
                value=float(row[field])
                if field in ("output_cosine_fp32", "state_rel_l2")
                else int(row[field]),
                units=units,
                source=SCALE_POLICY,
                marker=marker,
                revision=revision,
                timestamp=timestamp,
            )

    _number(
        numbers,
        provenance,
        key="uniform_mxfp4_hls_cost_advantage",
        value=uniform_hls["hls_lut_and_step_cost_advantage"],
        units="status",
        source=UNIFORM_HLS,
        marker='"hls_lut_and_step_cost_advantage":',
        revision=revision,
        timestamp=timestamp,
    )
    _number(
        numbers,
        provenance,
        key="corrected_candidate_hls_cost_advantage",
        value=e2m0_hls["hls_lut_and_nonfold_step_cost_advantage_vs_bf16"],
        units="status",
        source=E2M0_HLS,
        marker='"hls_lut_and_nonfold_step_cost_advantage_vs_bf16":',
        revision=revision,
        timestamp=timestamp,
    )
    _number(
        numbers,
        provenance,
        key="corrected_candidate_hls_tool_version",
        value=e2m0_hls["csynth"]["metrics"]["tool_version"],
        units="version",
        source=E2M0_HLS,
        marker='"tool_version":',
        revision=revision,
        timestamp=timestamp,
    )
    _number(
        numbers,
        provenance,
        key="corrected_candidate_rtl_64_token",
        value=trace_cosim["required_64_token_rtl_parity"],
        units="status",
        source=E2M0_TRACE_COSIM,
        marker='"required_64_token_rtl_parity":',
        revision=revision,
        timestamp=timestamp,
    )
    protocol_fields = (
        (
            "controlled_num_layers",
            uniform_hls["controlled_configuration"]["num_layers"],
            "layers",
            UNIFORM_HLS,
            '"num_layers":',
        ),
        (
            "controlled_num_qk_heads",
            uniform_hls["controlled_configuration"]["num_qk_heads"],
            "heads",
            UNIFORM_HLS,
            '"num_qk_heads":',
        ),
        (
            "controlled_num_value_heads",
            uniform_hls["controlled_configuration"]["num_value_heads"],
            "heads",
            UNIFORM_HLS,
            '"num_value_heads":',
        ),
        (
            "controlled_key_dim",
            uniform_hls["controlled_configuration"]["key_dim"],
            "elements",
            UNIFORM_HLS,
            '"key_dim":',
        ),
        (
            "controlled_value_dim",
            uniform_hls["controlled_configuration"]["value_dim"],
            "elements",
            UNIFORM_HLS,
            '"value_dim":',
        ),
        (
            "controlled_p_k",
            uniform_hls["controlled_configuration"]["p_k"],
            "lanes",
            UNIFORM_HLS,
            '"p_k":',
        ),
        (
            "controlled_p_v",
            uniform_hls["controlled_configuration"]["p_v"],
            "lanes",
            UNIFORM_HLS,
            '"p_v":',
        ),
        (
            "controlled_block_size",
            uniform_hls["controlled_configuration"]["block_size"],
            "elements",
            UNIFORM_HLS,
            '"block_size":',
        ),
        (
            "controlled_target_clock_ns",
            uniform_rows["BF16"]["target_clock_ns"],
            "ns",
            UNIFORM_HLS,
            '"target_clock_ns":',
        ),
        (
            "controlled_seed",
            preregistration["development_gate"]["seed"],
            "integer_seed",
            PREREGISTRATION,
            '"seed":',
        ),
        (
            "controlled_checkpoint_output_cosine_minimum",
            preregistration["quality_gate"]["checkpoint_output_cosine_minimum"],
            "cosine_similarity",
            PREREGISTRATION,
            '"checkpoint_output_cosine_minimum":',
        ),
        (
            "controlled_final_state_relative_l2_maximum",
            preregistration["quality_gate"]["final_state_relative_l2_maximum"],
            "relative_l2",
            PREREGISTRATION,
            '"final_state_relative_l2_maximum":',
        ),
        (
            "corrected_log_capacity",
            preregistration["controlled_configuration"]["capacity"],
            "entries",
            PREREGISTRATION,
            '"capacity":',
        ),
        (
            "corrected_accumulator_bits",
            preregistration["controlled_configuration"]["accumulator_bits"],
            "bits",
            PREREGISTRATION,
            '"accumulator_bits":',
        ),
        (
            "corrected_alignment_guard_bits",
            preregistration["controlled_configuration"]["alignment_guard_bits"],
            "bits",
            PREREGISTRATION,
            '"alignment_guard_bits":',
        ),
        (
            "corrected_heldout_registered_tokens",
            preregistration["held_out_gate"]["tokens"],
            "tokens",
            PREREGISTRATION,
            '"held_out_gate":',
        ),
        (
            "corrected_extended_registered_tokens",
            preregistration["extended_development_gate"]["tokens"],
            "tokens",
            PREREGISTRATION,
            '"extended_development_gate":',
        ),
        (
            "corrected_heldout_registered_run_count",
            preregistration["held_out_gate"]["run_count"],
            "traces",
            PREREGISTRATION,
            '"run_count":',
        ),
        (
            "controlled_scale_policy_count",
            len(final_scale_rows),
            "policies",
            SCALE_POLICY,
            ",8192,",
        ),
    )
    for key, value, units, source, marker in protocol_fields:
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=source,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    trace_fields = (
        (
            "synthetic_random_initial_state_standard_deviation",
            trace_protocol["random_initial_state"]["standard_deviation"],
            "standard_deviation",
            '"random_initial_state":',
        ),
        (
            "synthetic_value_standard_deviation",
            trace_protocol["token_inputs"]["value"]["standard_deviation"],
            "standard_deviation",
            '"value": {',
        ),
        (
            "synthetic_nominal_alpha_minimum",
            trace_protocol["trace_families"]["nominal"]["alpha_uniform"][0],
            "unitless",
            '"alpha_uniform": [0.95, 1.0]',
        ),
        (
            "synthetic_nominal_alpha_maximum",
            trace_protocol["trace_families"]["nominal"]["alpha_uniform"][1],
            "unitless",
            '"alpha_uniform": [0.95, 1.0]',
        ),
        (
            "synthetic_nominal_beta_minimum",
            trace_protocol["trace_families"]["nominal"]["beta_uniform"][0],
            "unitless",
            '"beta_uniform": [0.0, 1.0]',
        ),
        (
            "synthetic_nominal_beta_maximum",
            trace_protocol["trace_families"]["nominal"]["beta_uniform"][1],
            "unitless",
            '"beta_uniform": [0.0, 1.0]',
        ),
        (
            "synthetic_high_retention_alpha_minimum",
            trace_protocol["trace_families"]["high_retention"]["alpha_uniform"][0],
            "unitless",
            '"alpha_uniform": [0.995, 1.0]',
        ),
        (
            "synthetic_high_retention_alpha_maximum",
            trace_protocol["trace_families"]["high_retention"]["alpha_uniform"][1],
            "unitless",
            '"alpha_uniform": [0.995, 1.0]',
        ),
        (
            "synthetic_high_retention_beta_minimum",
            trace_protocol["trace_families"]["high_retention"]["beta_uniform"][0],
            "unitless",
            '"beta_uniform": [0.85, 1.0]',
        ),
        (
            "synthetic_high_retention_beta_maximum",
            trace_protocol["trace_families"]["high_retention"]["beta_uniform"][1],
            "unitless",
            '"beta_uniform": [0.85, 1.0]',
        ),
    )
    for key, value, units, marker in trace_fields:
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=TRACE_PROTOCOL,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )
    _number(
        numbers,
        provenance,
        key="synthetic_relative_l2_denominator_floor",
        value=trace_protocol["metrics"]["relative_l2_denominator_floor"],
        units="absolute_floor",
        source=TRACE_PROTOCOL,
        marker='"relative_l2_denominator_floor":',
        revision=revision,
        timestamp=timestamp,
    )

    controlled = uniform_hls["controlled_configuration"]
    qk_elements = int(controlled["num_qk_heads"]) * int(controlled["key_dim"])
    value_elements = int(controlled["num_value_heads"]) * int(
        controlled["value_dim"]
    )
    qk_scale_bytes = int(controlled["num_qk_heads"]) * (
        int(controlled["key_dim"]) // int(controlled["block_size"])
    )
    value_scale_bytes = int(controlled["num_value_heads"]) * (
        int(controlled["value_dim"]) // int(controlled["block_size"])
    )
    gate_bytes = 2 * int(controlled["num_value_heads"]) * 2
    uniform_mxfp4_token_bytes = (
        (2 * qk_elements + value_elements) * 4 // 8
        + 2 * qk_scale_bytes
        + value_scale_bytes
        + gate_bytes
    )
    residual_stack_terms = 2
    corrected_token_bytes = (
        residual_stack_terms
        * (
            (2 * qk_elements + value_elements) * 4 // 8
            + 2 * qk_scale_bytes
            + value_scale_bytes
        )
        + gate_bytes
    )
    bf16_token_bytes = (2 * qk_elements + value_elements + 2 * int(
        controlled["num_value_heads"]
    )) * 2
    bf16_output_bytes = value_elements * 2
    expanded_integer_output_bytes = value_elements * (32 + 16) // 8
    for key, value in (
        ("bf16_step_input_logical_bytes", bf16_token_bytes),
        ("uniform_mxfp4_step_input_logical_bytes", uniform_mxfp4_token_bytes),
        ("corrected_candidate_step_input_logical_bytes", corrected_token_bytes),
        ("bf16_output_logical_bytes", bf16_output_bytes),
        ("native_expanded_integer_output_logical_bytes", expanded_integer_output_bytes),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units="logical_bytes_per_command",
            source=UNIFORM_HLS,
            marker='"controlled_configuration":',
            revision=revision,
            timestamp=timestamp,
        )

    datapath_values_match = all(
        key in numbers and numbers[key]["value"] == expected
        for key, expected in datapath_manifest["used_number_values"].items()
    )
    if not datapath_values_match:
        # The final RS2 asset overlay owns this shared figure after it supersedes
        # the historical E2M0 candidate. Accept that state only when the checked
        # manifest is still value-bound to the canonical final numbers.
        canonical_numbers = json.loads(
            (DEFAULT_OUTPUT / "numbers.json").read_text(encoding="utf-8")
        )
        if any(
            key not in canonical_numbers
            or canonical_numbers[key]["value"] != expected
            for key, expected in datapath_manifest["used_number_values"].items()
        ):
            raise ValueError("corrected datapath manifest is not value-bound")

    checkpoints = list(preregistration["extended_development_gate"]["checkpoints"])
    _number(
        numbers,
        provenance,
        key="controlled_required_checkpoints",
        value=checkpoints,
        units="token_indices",
        source=PREREGISTRATION,
        marker='"checkpoints":',
        revision=revision,
        timestamp=timestamp,
    )

    format_fields = (
        (
            "mxfp4_logical_bits_per_value",
            4.25,
            "bits_per_value",
            "4.25 bits/value",
        ),
        ("mxfp4_e2m1_sign_bits", 1, "bits", "E2M1 uses one sign bit"),
        ("mxfp4_e2m1_exponent_bits", 2, "bits", "E2M1 uses one sign bit"),
        ("mxfp4_e2m1_mantissa_bits", 1, "bits", "E2M1 uses one sign bit"),
        (
            "mxfp4_e2m1_positive_magnitudes",
            [0, 0.5, 1, 1.5, 2, 3, 4, 6],
            "finite_magnitudes",
            "code magnitude:",
        ),
        ("mxfp4_e8m0_valid_code_minimum", 0, "scale_code", "in `0..254`"),
        ("mxfp4_e8m0_valid_code_maximum", 254, "scale_code", "in `0..254`"),
        ("mxfp4_e8m0_invalid_code", 255, "scale_code", "Byte `255`"),
        ("mxfp4_e8m0_exponent_bias", 127, "exponent_bias", "2^(e - 127)"),
        ("mxfp4_e8m0_zero_block_scale_code", 127, "scale_code", "scale byte `127`"),
        ("corrected_e2m0_residual_bits", 3, "bits", "signed three-bit"),
        ("corrected_residual_stack_terms", 2, "terms", "two-term"),
    )
    for key, value, units, marker in format_fields:
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=NUMERICAL_CONTRACT,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    extended = None
    extended_status = "NOT_RUN"
    extended_replay_status = "NOT_RUN"
    if EXTENDED.exists():
        extended_payload = _load_json(EXTENDED, require_pass=False)
        extended_status = str(extended_payload.get("status", "NOT_RUN"))
        extended_replay_status = str(
            extended_payload.get("full_deterministic_recompute", "NOT_RUN")
        )
        if extended_status not in {"PASS", "FAIL", "NOT_RUN"}:
            raise ValueError("corrected 8192-token extended status is invalid")
        if extended_replay_status == "PASS" and all(
            extended_payload.get(field) is not None
            for field in (
                "run_count",
                "recomputed_run_count",
                "minimum_checkpoint_output_cosine",
                "maximum_final_state_relative_l2",
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
        ):
            extended = extended_payload
        for field, units in (
            ("run_count", "traces"),
            ("recomputed_run_count", "traces"),
            ("minimum_checkpoint_output_cosine", "cosine_similarity"),
            ("maximum_final_state_relative_l2", "relative_l2"),
            ("minimum_all_token_output_cosine", "cosine_similarity"),
            ("maximum_all_token_state_relative_l2", "relative_l2"),
            ("maximum_all_token_state_abs_error", "absolute_error"),
            ("total_element_saturations", "events"),
            ("total_accumulator_saturations", "events"),
            ("total_scale_clamps", "events"),
            ("total_alignment_underflows", "events"),
            ("total_e2m0_residual_clips", "events"),
            ("total_folds", "folds"),
        ):
            if extended is None:
                continue
            _number(
                numbers,
                provenance,
                key=f"corrected_extended_{field}",
                value=extended[field],
                units=units,
                source=EXTENDED,
                marker=f'"{field}":',
                revision=revision,
                timestamp=timestamp,
            )
        _number(
            numbers,
            provenance,
            key="corrected_extended_quality_status",
            value=extended_status,
            units="status",
            source=EXTENDED,
            marker='"status":',
            revision=revision,
            timestamp=timestamp,
        )
        _number(
            numbers,
            provenance,
            key="corrected_extended_replay_status",
            value=extended_replay_status,
            units="status",
            source=EXTENDED,
            marker='"full_deterministic_recompute":',
            revision=revision,
            timestamp=timestamp,
        )

    if extended is not None:
        registered_state_limit = float(
            preregistration["quality_gate"]["final_state_relative_l2_maximum"]
        )
        extended_state_max = float(extended["maximum_all_token_state_relative_l2"])
        _number(
            numbers,
            provenance,
            key="corrected_extended_state_l2_gate_margin",
            value=registered_state_limit - extended_state_max,
            units="relative_l2",
            source=EXTENDED,
            marker='"maximum_all_token_state_relative_l2":',
            revision=revision,
            timestamp=timestamp,
        )
        _number(
            numbers,
            provenance,
            key="corrected_state_l2_sensitivity_probe",
            value=STATE_REL_L2_SENSITIVITY_PROBE,
            units="relative_l2",
            source=Path(__file__),
            marker="STATE_REL_L2_SENSITIVITY_PROBE =",
            revision=revision,
            timestamp=timestamp,
        )
        for key, value, source, marker in (
            (
                "corrected_heldout_state_l2_probe_status",
                float(held_out["maximum_all_token_state_relative_l2"]),
                HELD_OUT,
                '"maximum_all_token_state_relative_l2":',
            ),
            (
                "corrected_extended_state_l2_probe_status",
                extended_state_max,
                EXTENDED,
                '"maximum_all_token_state_relative_l2":',
            ),
        ):
            _number(
                numbers,
                provenance,
                key=key,
                value="PASS" if value <= STATE_REL_L2_SENSITIVITY_PROBE else "FAIL",
                units="status",
                source=source,
                marker=marker,
                revision=revision,
                timestamp=timestamp,
            )

    postroute_target = postroute["target_clock"]
    postroute_first = postroute["first_tested_closing_point"]
    postroute_secondary = next(
        row for row in postroute["timing_sweep"] if row["period_ns"] == 5.0
    )
    postroute_critical = postroute["critical_path_at_4ns"]
    postroute_utilization = postroute["utilization"]
    postroute_drc = postroute["drc"]
    postroute_power = postroute["power_at_5p6ns"]
    for key, value, units, marker in (
        (
            "corrected_postroute_physical_fit",
            postroute["physical_fit"],
            "status",
            '"physical_fit":',
        ),
        (
            "corrected_postroute_250mhz_status",
            postroute_target["status"],
            "status",
            '"target_clock":',
        ),
        (
            "corrected_postroute_target_frequency_mhz",
            postroute_target["frequency_mhz"],
            "MHz",
            '"target_clock":',
        ),
        (
            "corrected_postroute_250mhz_wns_ns",
            postroute_target["timing"]["wns_ns"],
            "ns",
            '"target_clock":',
        ),
        (
            "corrected_postroute_200mhz_status",
            postroute["implemented_200mhz_timing"],
            "status",
            '"implemented_200mhz_timing":',
        ),
        (
            "corrected_postroute_secondary_frequency_mhz",
            postroute_secondary["frequency_mhz"],
            "MHz",
            '"period_ns": 5.0',
        ),
        (
            "corrected_postroute_first_closing_period_ns",
            postroute_first["period_ns"],
            "ns",
            '"first_tested_closing_point":',
        ),
        (
            "corrected_postroute_first_closing_frequency_mhz",
            postroute_first["frequency_mhz"],
            "MHz",
            '"first_tested_closing_point":',
        ),
        (
            "corrected_postroute_first_closing_wns_ns",
            postroute_first["wns_ns"],
            "ns",
            '"first_tested_closing_point":',
        ),
        (
            "corrected_postroute_first_closing_whs_ns",
            postroute_first["whs_ns"],
            "ns",
            '"first_tested_closing_point":',
        ),
        (
            "corrected_postroute_critical_path_ns",
            postroute_critical["data_path_delay_ns"],
            "ns",
            '"critical_path_at_4ns":',
        ),
        (
            "corrected_postroute_critical_route_percent",
            postroute_critical["route_delay_percent"],
            "percent",
            '"critical_path_at_4ns":',
        ),
        (
            "corrected_postroute_critical_logic_levels",
            postroute_critical["logic_levels"],
            "levels",
            '"critical_path_at_4ns":',
        ),
        (
            "corrected_postroute_drc_status",
            postroute_drc["signoff_status"],
            "status",
            '"drc":',
        ),
        (
            "corrected_postroute_drc_warning_count",
            postroute_drc["warning_count"],
            "warnings",
            '"drc":',
        ),
        (
            "corrected_postroute_drc_critical_warning_count",
            postroute_drc["critical_warning_count"],
            "warnings",
            '"drc":',
        ),
        (
            "corrected_postroute_drc_error_count",
            postroute_drc["error_count"],
            "errors",
            '"drc":',
        ),
        (
            "corrected_postroute_power_total_w",
            postroute_power["total_on_chip_w"],
            "W",
            '"power_at_5p6ns":',
        ),
        (
            "corrected_postroute_power_period_ns",
            postroute_power["period_ns"],
            "ns",
            '"power_at_5p6ns":',
        ),
        (
            "corrected_postroute_power_dynamic_w",
            postroute_power["dynamic_w"],
            "W",
            '"power_at_5p6ns":',
        ),
        (
            "corrected_postroute_power_static_w",
            postroute_power["static_w"],
            "W",
            '"power_at_5p6ns":',
        ),
        (
            "corrected_postroute_power_confidence",
            postroute_power["confidence"],
            "confidence",
            '"power_at_5p6ns":',
        ),
        (
            "corrected_postroute_energy_per_token_status",
            postroute_power["energy_per_token"],
            "status",
            '"power_at_5p6ns":',
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=VIVADO_POSTROUTE,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )
    for resource, label in (
        ("clb_luts", "lut"),
        ("clb_registers", "ff"),
        ("block_ram_tiles", "bram_tiles"),
        ("uram", "uram"),
        ("dsps", "dsp"),
    ):
        row = postroute_utilization[resource]
        for suffix, value, units in (
            ("used", row["used"], "resources"),
            ("utilization_percent", row["utilization_percent"], "percent"),
        ):
            _number(
                numbers,
                provenance,
                key=f"corrected_postroute_{label}_{suffix}",
                value=value,
                units=units,
                source=VIVADO_POSTROUTE,
                marker=f'"{resource}":',
                revision=revision,
                timestamp=timestamp,
            )

    mxfp8_target = mxfp8_vivado["target_clock"]
    mxfp8_first = mxfp8_vivado["first_tested_closing_point"]
    mxfp8_utilization = mxfp8_vivado["utilization"]
    mxfp8_drc = mxfp8_vivado["drc"]
    mxfp8_power = mxfp8_vivado["vectorless_power"]
    for key, value, units, marker in (
        (
            "mxfp8_postroute_physical_fit",
            mxfp8_vivado["physical_fit"],
            "status",
            '"physical_fit":',
        ),
        (
            "mxfp8_postroute_250mhz_status",
            mxfp8_target["status"],
            "status",
            '"target_clock":',
        ),
        (
            "mxfp8_postroute_250mhz_wns_ns",
            mxfp8_target["timing"]["wns_ns"],
            "ns",
            '"target_clock":',
        ),
        (
            "mxfp8_postroute_first_closing_period_ns",
            mxfp8_first["period_ns"],
            "ns",
            '"first_tested_closing_point":',
        ),
        (
            "mxfp8_postroute_first_closing_frequency_mhz",
            mxfp8_first["frequency_mhz"],
            "MHz",
            '"first_tested_closing_point":',
        ),
        (
            "mxfp8_postroute_first_closing_wns_ns",
            mxfp8_first["wns_ns"],
            "ns",
            '"first_tested_closing_point":',
        ),
        (
            "mxfp8_postroute_first_closing_whs_ns",
            mxfp8_first["whs_ns"],
            "ns",
            '"first_tested_closing_point":',
        ),
        (
            "mxfp8_postroute_drc_status",
            mxfp8_drc["signoff_status"],
            "status",
            '"drc":',
        ),
        (
            "mxfp8_postroute_power_total_w",
            mxfp8_power["total_on_chip_w"],
            "W",
            '"vectorless_power":',
        ),
        (
            "mxfp8_postroute_power_dynamic_w",
            mxfp8_power["dynamic_w"],
            "W",
            '"vectorless_power":',
        ),
        (
            "mxfp8_postroute_power_static_w",
            mxfp8_power["static_w"],
            "W",
            '"vectorless_power":',
        ),
        (
            "mxfp8_postroute_power_period_ns",
            mxfp8_power["period_ns"],
            "ns",
            '"vectorless_power":',
        ),
        (
            "mxfp8_postroute_power_confidence",
            mxfp8_power["confidence"],
            "confidence",
            '"vectorless_power":',
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=MXFP8_VIVADO,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )
    for resource, label in (
        ("clb_luts", "lut"),
        ("clb_registers", "ff"),
        ("block_ram_tiles", "bram_tiles"),
        ("uram", "uram"),
        ("dsps", "dsp"),
    ):
        row = mxfp8_utilization[resource]
        for suffix, value, units in (
            ("used", row["used"], "resources"),
            ("utilization_percent", row["utilization_percent"], "percent"),
        ):
            _number(
                numbers,
                provenance,
                key=f"mxfp8_postroute_{label}_{suffix}",
                value=value,
                units=units,
                source=MXFP8_VIVADO,
                marker=f'"{resource}":',
                revision=revision,
                timestamp=timestamp,
            )

    for key, value, units, marker in (
        (
            "corrected_e2m0_control_cosim_status",
            control_cosim["status"],
            "status",
            '"status":',
        ),
        (
            "corrected_e2m0_control_cosim_commands",
            control_cosim["rtl_simulation"]["completed_transactions"],
            "commands",
            '"rtl_simulation":',
        ),
        (
            "corrected_e2m0_control_cosim_latency_cycles",
            control_cosim["official_hls_cosim"]["latency_avg_cycles"],
            "cycles",
            '"official_hls_cosim":',
        ),
        (
            "corrected_e2m0_control_cosim_interval_cycles",
            control_cosim["official_hls_cosim"]["interval_avg_cycles"],
            "cycles",
            '"official_hls_cosim":',
        ),
        (
            "corrected_e2m0_control_cosim_total_cycles",
            control_cosim["official_hls_cosim"]["total_execution_cycles"],
            "cycles",
            '"official_hls_cosim":',
        ),
        (
            "corrected_e2m0_control_cosim_recurrent_transition",
            control_cosim["recurrent_transition_covered"],
            "boolean",
            '"recurrent_transition_covered":',
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=E2M0_CONTROL_COSIM,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    for key, value, units, marker in (
        (
            "corrected_e2m0_rtl_64_token_status",
            trace_cosim["required_64_token_rtl_parity"],
            "status",
            '"required_64_token_rtl_parity":',
        ),
        (
            "corrected_e2m0_rtl_trace_tokens",
            trace_cosim["trace"]["tokens"],
            "tokens",
            '"tokens":',
        ),
        (
            "corrected_e2m0_rtl_transactions",
            trace_cosim["rtl_simulation"]["completed_transactions"],
            "transactions",
            '"completed_transactions":',
        ),
        (
            "corrected_e2m0_rtl_output_values_compared",
            trace_cosim["parity"]["output_values_compared"],
            "values",
            '"output_values_compared":',
        ),
        (
            "corrected_e2m0_hls_csim_64_token_status",
            trace_cosim["hls_c_simulation"]["status"],
            "status",
            '"hls_c_simulation":',
        ),
        (
            "corrected_e2m0_rtl_direct_load_status",
            trace_cosim["direct_generated_rtl_load"]["status"],
            "status",
            '"direct_generated_rtl_load":',
        ),
        (
            "corrected_e2m0_rtl_direct_load_cycles",
            trace_cosim["direct_generated_rtl_load"]["cycles"],
            "cycles",
            '"cycles":',
        ),
        (
            "corrected_e2m0_rtl_completed_recurrent_steps",
            trace_cosim["rtl_simulation"]["completed_recurrent_steps"],
            "steps",
            '"completed_recurrent_steps":',
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=E2M0_TRACE_COSIM,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    qwen_capture = qwen_characterization["capture"]
    qwen_input = qwen_characterization["floating_tensors"]["layer_input"]
    qwen_recurrence = qwen_characterization["recurrence_coverage"]
    for key, value, units, marker in (
        (
            "qwen_capture_sha256",
            qwen_capture["sha256"],
            "sha256",
            '"capture":',
        ),
        (
            "qwen_capture_model_id",
            qwen_capture["metadata"]["model_id"],
            "identifier",
            '"metadata":',
        ),
        (
            "qwen_capture_layer_index",
            qwen_capture["metadata"]["layer_index"],
            "layer_index",
            '"metadata":',
        ),
        (
            "qwen_capture_layer_input_elements",
            qwen_input["elements"],
            "elements",
            '"layer_input":',
        ),
        (
            "qwen_capture_layer_input_abs_p99",
            qwen_input["abs_p99"],
            "absolute_value",
            '"layer_input":',
        ),
        (
            "qwen_capture_layer_input_abs_p999",
            qwen_input["abs_p999"],
            "absolute_value",
            '"layer_input":',
        ),
        (
            "qwen_capture_layer_input_abs_max",
            qwen_input["abs_max"],
            "absolute_value",
            '"layer_input":',
        ),
        (
            "qwen_capture_layer_input_max_to_p99_ratio",
            float(qwen_input["abs_max"]) / float(qwen_input["abs_p99"]),
            "ratio",
            '"layer_input":',
        ),
        (
            "qwen_capture_recurrence_complete",
            qwen_recurrence["complete"],
            "boolean",
            '"recurrence_coverage":',
        ),
        (
            "qwen_capture_closed_loop_quality_supported",
            qwen_recurrence["closed_loop_quality_supported"],
            "boolean",
            '"recurrence_coverage":',
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=QWEN_CHARACTERIZATION,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    recurrent_metadata = qwen_recurrent["source_metadata"]
    valid_lengths = [int(value) for value in recurrent_metadata["valid_tokens_per_prompt"]]
    for key, value, units, marker in (
        (
            "qwen_recurrent_input_sha256",
            qwen_recurrent["input_sha256"],
            "sha256",
            '"input_sha256":',
        ),
        (
            "qwen_recurrent_layer_index",
            recurrent_metadata["layer_index"],
            "layer_index",
            '"layer_index":',
        ),
        (
            "qwen_recurrent_prompt_count",
            len(valid_lengths),
            "prompts",
            '"valid_tokens_per_prompt":',
        ),
        (
            "qwen_recurrent_total_valid_tokens",
            recurrent_metadata["total_valid_tokens"],
            "tokens",
            '"total_valid_tokens":',
        ),
        (
            "qwen_recurrent_min_valid_tokens",
            min(valid_lengths),
            "tokens_per_prompt",
            '"valid_tokens_per_prompt":',
        ),
        (
            "qwen_recurrent_max_valid_tokens",
            max(valid_lengths),
            "tokens_per_prompt",
            '"valid_tokens_per_prompt":',
        ),
    ):
        _number(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=QWEN_RECURRENT,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    recurrent_fields = (
        ("mean_final_output_cosine_fp32", "mean_final_output_cosine", "cosine_similarity"),
        ("worst_output_cosine_fp32", "worst_output_cosine", "cosine_similarity"),
        ("mean_final_state_rel_l2", "mean_final_state_relative_l2", "relative_l2"),
        ("worst_state_rel_l2", "worst_state_relative_l2", "relative_l2"),
        ("max_state_abs_error", "maximum_state_absolute_error", "absolute_error"),
        ("nonfinite_events", "nonfinite_events", "events"),
    )
    for variant, aggregate in qwen_recurrent["aggregate"].items():
        prefix = {
            "bf16_qdq_fp32_accum_state_bf16": "bf16",
            "mxfp4_qdq_state_mxfp4_b32": "mxfp4",
            "mxfp4_qdq_state_mxfp8_b32": "mxfp8_state",
            "flat_int4_qdq": "flat_int4",
            "mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5": (
                "rs2"
            ),
        }[variant]
        marker = f'"{variant}": {{'
        for source_field, suffix, units in recurrent_fields:
            _number(
                numbers,
                provenance,
                key=f"qwen_recurrent_{prefix}_{suffix}",
                value=aggregate[source_field],
                units=units,
                source=QWEN_RECURRENT,
                marker=marker,
                revision=revision,
                timestamp=timestamp,
            )
    rs2_qwen_variant = (
        "mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5"
    )
    _number(
        numbers,
        provenance,
        key="qwen_recurrent_rs2_accumulator_saturations",
        value=qwen_recurrent["aggregate"][rs2_qwen_variant][
            "cumulative_accumulator_saturations"
        ],
        units="events",
        source=QWEN_RECURRENT,
        marker=f'"{rs2_qwen_variant}": {{',
        revision=revision,
        timestamp=timestamp,
    )
    output.mkdir(parents=True, exist_ok=True)
    tables = output / "tables"
    snippets = output / "snippets"
    tables.mkdir(parents=True, exist_ok=True)
    snippets.mkdir(parents=True, exist_ok=True)
    stale_gate_table = tables / "readiness_gates.tex"
    if stale_gate_table.exists():
        stale_gate_table.unlink()
    (output / "numbers.json").write_text(
        json.dumps(numbers, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    checkpoint_header = " & ".join(
        rf"\multicolumn{{2}}{{c}}{{{_tex_integer(length)}}}"
        for length in REQUIRED_LENGTHS
    )
    long_lines = [
        r"\begin{tabular}{lrrrrrrrrrr}",
        r"\toprule",
        f"& {checkpoint_header} " + r"\\",
        r"Variant & Cos. & Rel. $L_2$ & Cos. & Rel. $L_2$ & Cos. & Rel. $L_2$ & Cos. & Rel. $L_2$ & Cos. & Rel. $L_2$ \\",
        r"\midrule",
    ]
    for variant in DISPLAY_VARIANTS:
        cells = []
        for length in REQUIRED_LENGTHS:
            row = selected[(length, variant)]
            cells.extend(
                [
                    f"{float(row['output_cosine_fp32']):.5f}",
                    f"{float(row['state_rel_l2']):.5f}",
                ]
            )
        long_lines.append(f"{_escape(DISPLAY_NAMES[variant])} & " + " & ".join(cells) + r" \\")
    long_lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (tables / "long_sequence.tex").write_text("\n".join(long_lines), encoding="utf-8")

    hls_lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Arithmetic & Path (ns) & STEP max & LUT & FF & DSP \\",
        r"\midrule",
    ]
    hls_display = {
        "BF16": "BF16",
        "uniform_mxfp4": "Native encoded MXFP4",
        "native_mxfp8": "Native MXFP8",
    }
    for row in uniform_hls["rows"]:
        hls_lines.append(
            f"{hls_display[row['variant']]} & {float(row['estimated_clock_ns']):.3f} & "
            f"{_tex_integer(row['step_cycles_max'])} & {_tex_integer(row['lut'])} & "
            f"{_tex_integer(row['ff'])} & {_tex_integer(row['dsp'])} " + r"\\"
        )
    hls_lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (tables / "controlled_hls.tex").write_text("\n".join(hls_lines), encoding="utf-8")

    qwen_lines = [
        r"\begin{tabular}{lrrrrr@{\hspace{1em}}r}",
        r"\toprule",
        r"Arithmetic & Mean final cos. & Worst cos. & Mean state $L_2$ & Worst state $L_2$ & Max abs. & Nonfinite \\",
        r"\midrule",
    ]
    for variant, display in QWEN_RECURRENT_NAMES.items():
        row = qwen_recurrent["aggregate"][variant]
        qwen_lines.append(
            f"{_escape(display)} & {float(row['mean_final_output_cosine_fp32']):.5f} & "
            f"{float(row['worst_output_cosine_fp32']):.5f} & "
            f"{float(row['mean_final_state_rel_l2']):.5f} & "
            f"{float(row['worst_state_rel_l2']):.5f} & "
            f"{float(row['max_state_abs_error']):.5f} & "
            f"{_tex_integer(row['nonfinite_events'])} " + r"\\"
        )
    qwen_lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (tables / "qwen_recurrent_stability.tex").write_text(
        "\n".join(qwen_lines), encoding="utf-8"
    )

    candidate_row = e2m0_rows[candidate_name]
    mitigation_lines = [
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Metric & BF16 & Encoded MXFP4 & Corrected candidate \\",
        r"\midrule",
        f"Logical bytes/layer & {_tex_integer(e2m0_rows['BF16']['logical_state_bytes_per_layer'])} & "
        f"{_tex_integer(e2m0_rows['uniform_mxfp4']['logical_state_bytes_per_layer'])} & "
        f"{_tex_integer(candidate_row['logical_state_bytes_per_layer'])} " + r"\\",
        f"LUT & {_tex_integer(e2m0_rows['BF16']['lut'])} & "
        f"{_tex_integer(e2m0_rows['uniform_mxfp4']['lut'])} & "
        f"{_tex_integer(candidate_row['lut'])} " + r"\\",
        f"Non-fold STEP max & {_tex_integer(e2m0_rows['BF16']['nonfold_step_cycles_max'])} & "
        f"{_tex_integer(e2m0_rows['uniform_mxfp4']['nonfold_step_cycles_max'])} & "
        f"{_tex_integer(candidate_row['nonfold_step_cycles_max'])} " + r"\\",
        f"Amortized per-layer HLS cycles/STEP & {_tex_integer(round(float(e2m0_rows['BF16']['amortized_cycles_max'])))} & "
        f"{_tex_integer(round(float(e2m0_rows['uniform_mxfp4']['amortized_cycles_max'])))} & "
        f"{_tex_integer(round(float(candidate_row['amortized_cycles_max'])))} " + r"\\",
        f"Fold-command burst max & -- & -- & "
        f"{_tex_integer(e2m0_hls['csynth']['fold_latency_cycles']['maximum'])} " + r"\\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]
    (tables / "mitigation_hls.tex").write_text(
        "\n".join(mitigation_lines), encoding="utf-8"
    )

    resource_lines = [
        r"\begin{tabular}{lrr}",
        r"\toprule",
        r"Generated hierarchy block & LUT & Share of top (\%) \\",
        r"\midrule",
        (
            "BF16 state-update block & "
            f"{_tex_integer(hierarchy_values['bf16_state_update_lut'])} & "
            f"{numbers['bf16_state_update_lut_percent_of_top']['value']:.1f} "
            + r"\\"
        ),
        (
            "Encoded-MXFP4 state-update block & "
            f"{_tex_integer(hierarchy_values['native_encoded_state_update_lut'])} & "
            f"{numbers['native_encoded_state_update_lut_percent_of_top']['value']:.1f} "
            + r"\\"
        ),
        (
            "Correction fold engine & "
            f"{_tex_integer(hierarchy_values['corrected_fold_log_lut'])} & "
            f"{numbers['corrected_fold_log_lut_percent_of_top']['value']:.1f} "
            + r"\\"
        ),
        (
            "Correction update quantizer & "
            f"{_tex_integer(hierarchy_values['corrected_update_quantizer_lut'])} & "
            f"{numbers['corrected_update_quantizer_lut_percent_of_top']['value']:.1f} "
            + r"\\"
        ),
        r"\midrule",
        (
            "Correction subtotal & "
            f"{_tex_integer(correction_machinery_lut)} & "
            f"{numbers['corrected_correction_machinery_lut_percent_of_top']['value']:.1f} "
            + r"\\"
        ),
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]
    (tables / "resource_ablation.tex").write_text(
        "\n".join(resource_lines), encoding="utf-8"
    )

    held_lines = [
        r"\begin{tabular}{lr}",
        r"\toprule",
        r"Test-set statistic (\CorrectedHeldoutSeedBlocks{} seed blocks, "
        r"\CorrectedHeldoutPairedConditions{} paired conditions) & Worst value \\",
        r"\midrule",
        f"Minimum checkpoint output cosine & {float(held_out['minimum_registered_checkpoint_output_cosine']):.6f} " + r"\\",
        f"Minimum all-token output cosine & {float(held_out['minimum_all_token_output_cosine']):.6f} " + r"\\",
        f"Maximum final state relative $L_2$ & {float(held_out['maximum_final_state_relative_l2']):.6f} " + r"\\",
        f"Maximum all-token state relative $L_2$ & {float(held_out['maximum_all_token_state_relative_l2']):.6f} " + r"\\",
        f"Maximum state absolute error & {float(held_out['maximum_all_token_state_abs_error']):.6f} " + r"\\",
        f"Three hard-event counters & {_tex_integer(total_hard_events)} " + r"\\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]
    (tables / "corrected_heldout.tex").write_text("\n".join(held_lines), encoding="utf-8")

    final_scale_rows = [row for row in scale_rows if int(row["token_index"]) == 8192]
    scale_display = {
        "mxfp4_scale_fixed": "Fixed",
        "mxfp4_scale_every_token": "Every token",
        "mxfp4_scale_periodic_4": "Periodic, $N=4$",
        "mxfp4_scale_periodic_8": "Periodic, $N=8$",
        "mxfp4_scale_periodic_16": "Periodic, $N=16$",
        "mxfp4_scale_threshold_0p75_5p5": "Threshold triggered",
    }
    scale_order = {name: index for index, name in enumerate(scale_display)}
    final_scale_rows.sort(key=lambda row: scale_order[row["variant"]])
    scale_lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Scale policy & Output cosine & State rel. $L_2$ & Clips & Scale changes \\",
        r"\midrule",
    ]
    for row in final_scale_rows:
        scale_lines.append(
            f"{scale_display[row['variant']]} & {float(row['output_cosine_fp32']):.6f} & "
            f"{float(row['state_rel_l2']):.6f} & "
            f"{_tex_integer(row['state_element_saturations_cumulative'])} & "
            f"{_tex_integer(row['state_scale_changes_cumulative'])} " + r"\\"
        )
    scale_lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    (tables / "scale_policy.tex").write_text("\n".join(scale_lines), encoding="utf-8")

    postroute_lines = [
        r"\begin{tabular}{lrl}",
        r"\toprule",
        r"Evidence item & Result & Status \\",
        r"\midrule",
        r"\multicolumn{3}{l}{\textit{Corrected MXFP4 candidate}} \\",
        f"Out-of-context physical fit & yes & {_escape(postroute['physical_fit'])} "
        + r"\\",
        (
            f"250-MHz setup WNS & {float(postroute_target['timing']['wns_ns']):.3f} ns & "
            f"{_escape(postroute_target['status'])} " + r"\\"
        ),
        (
            "First tested closing point & "
            f"{float(postroute_first['frequency_mhz']):.2f} MHz & PASS " + r"\\"
        ),
        (
            "CLB LUT / FF & "
            f"{_tex_integer(postroute_utilization['clb_luts']['used'])} / "
            f"{_tex_integer(postroute_utilization['clb_registers']['used'])} & FIT "
            + r"\\"
        ),
        (
            "BRAM tile / URAM / DSP & "
            f"{_tex_integer(postroute_utilization['block_ram_tiles']['used'])} / "
            f"{_tex_integer(postroute_utilization['uram']['used'])} / "
            f"{_tex_integer(postroute_utilization['dsps']['used'])} & FIT " + r"\\"
        ),
        (
            f"DRC warnings / critical / errors & {postroute_drc['warning_count']} / "
            f"{postroute_drc['critical_warning_count']} / {postroute_drc['error_count']} & "
            f"{_escape(postroute_drc['signoff_status'])} " + r"\\"
        ),
        (
            "Vectorless power at 5.6 ns & "
            f"{float(postroute_power['total_on_chip_w']):.3f} W & "
            f"{_escape(postroute_power['confidence'])} estimate " + r"\\"
        ),
        (
            "Generated-RTL control smoke & "
            f"{control_cosim['rtl_simulation']['completed_transactions']} / "
            f"{control_cosim['rtl_simulation']['total_transactions']} commands & PASS "
            + r"\\"
        ),
        (
            "Candidate 64-token HLS C parity & "
            f"{trace_cosim['trace']['tokens']} tokens & "
            f"{_escape(trace_cosim['hls_c_simulation']['status'])} " + r"\\"
        ),
        (
            "Candidate generated-RTL direct LOAD & "
            f"{trace_cosim['direct_generated_rtl_load']['completed_transactions']} command & "
            f"{_escape(trace_cosim['direct_generated_rtl_load']['status'])} " + r"\\"
        ),
        (
            "Candidate recurrent 64-token RTL parity & "
            f"{trace_cosim['rtl_simulation']['completed_recurrent_steps']} / "
            f"{trace_cosim['trace']['tokens']} STEP commands & "
            f"{_escape(trace_cosim['required_64_token_rtl_parity'])} " + r"\\"
        ),
        r"\midrule",
        r"\multicolumn{3}{l}{\textit{Native MXFP8 baseline}} \\",
        (
            "Out-of-context physical fit & yes & "
            f"{_escape(mxfp8_vivado['physical_fit'])} " + r"\\"
        ),
        (
            f"250-MHz setup WNS & {float(mxfp8_target['timing']['wns_ns']):.3f} ns & "
            f"{_escape(mxfp8_target['status'])} " + r"\\"
        ),
        (
            "First tested closing point & "
            f"{float(mxfp8_first['frequency_mhz']):.2f} MHz & PASS " + r"\\"
        ),
        (
            "CLB LUT / FF & "
            f"{_tex_integer(mxfp8_utilization['clb_luts']['used'])} / "
            f"{_tex_integer(mxfp8_utilization['clb_registers']['used'])} & FIT "
            + r"\\"
        ),
        (
            "BRAM tile / URAM / DSP & "
            f"{_tex_integer(mxfp8_utilization['block_ram_tiles']['used'])} / "
            f"{_tex_integer(mxfp8_utilization['uram']['used'])} / "
            f"{_tex_integer(mxfp8_utilization['dsps']['used'])} & FIT " + r"\\"
        ),
        (
            f"Vectorless power at {float(mxfp8_power['period_ns']):.2f} ns & "
            f"{float(mxfp8_power['total_on_chip_w']):.3f} W & "
            f"{_escape(mxfp8_power['confidence'])} estimate " + r"\\"
        ),
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]
    (tables / "postroute_evidence.tex").write_text(
        "\n".join(postroute_lines), encoding="utf-8"
    )

    extended_table = tables / "corrected_extended.tex"
    quality_table = tables / "corrected_quality.tex"
    if extended is None:
        extended_table.unlink(missing_ok=True)
        quality_table.unlink(missing_ok=True)
    else:
        hard_events = (
            int(extended["total_element_saturations"])
            + int(extended["total_accumulator_saturations"])
            + int(extended["total_scale_clamps"])
        )
        extended_lines = [
            r"\begin{tabular}{lr}",
            r"\toprule",
            r"Metric (deterministically recomputed runs) & Worst/total \\",
            r"\midrule",
            (
                "Minimum checkpoint output cosine & "
                f"{float(extended['minimum_checkpoint_output_cosine']):.6f} "
                + r"\\"
            ),
            (
                "Minimum all-token output cosine & "
                f"{float(extended['minimum_all_token_output_cosine']):.6f} "
                + r"\\"
            ),
            (
                r"Maximum final state relative $L_2$ & "
                f"{float(extended['maximum_final_state_relative_l2']):.6f} "
                + r"\\"
            ),
            (
                r"Maximum all-token state relative $L_2$ & "
                f"{float(extended['maximum_all_token_state_relative_l2']):.6f} "
                + r"\\"
            ),
            (
                "Maximum state absolute error & "
                f"{float(extended['maximum_all_token_state_abs_error']):.6f} "
                + r"\\"
            ),
            f"Three hard-event counters & {_tex_integer(hard_events)} "
            + r"\\",
            (
                "Alignment underflows & "
                f"{_tex_integer(extended['total_alignment_underflows'])} "
                + r"\\"
            ),
            (
                "Deliberate E2M0 residual clips & "
                f"{_tex_integer(extended['total_e2m0_residual_clips'])} "
                + r"\\"
            ),
            f"Update-log folds & {_tex_integer(extended['total_folds'])} " + r"\\",
            r"\bottomrule",
            r"\end{tabular}",
            "",
        ]
        extended_table.write_text("\n".join(extended_lines), encoding="utf-8")

        quality_lines = [
            r"\begin{tabular}{lrr}",
            r"\toprule",
            (
                r"Metric & Test (\CorrectedHeldoutTraceTokens{}) & "
                r"Development (\CorrectedLongTraceTokens{}) \\"
            ),
            r"\midrule",
            (
                "Min. checkpoint cosine & "
                f"{float(held_out['minimum_registered_checkpoint_output_cosine']):.6f} & "
                f"{float(extended['minimum_checkpoint_output_cosine']):.6f} "
                + r"\\"
            ),
            (
                "Min. all-token cosine & "
                f"{float(held_out['minimum_all_token_output_cosine']):.6f} & "
                f"{float(extended['minimum_all_token_output_cosine']):.6f} "
                + r"\\"
            ),
            (
                r"Max. final state rel. $L_2$ & "
                f"{float(held_out['maximum_final_state_relative_l2']):.6f} & "
                f"{float(extended['maximum_final_state_relative_l2']):.6f} "
                + r"\\"
            ),
            (
                r"Max. all-token state rel. $L_2$ & "
                f"{float(held_out['maximum_all_token_state_relative_l2']):.6f} & "
                f"{float(extended['maximum_all_token_state_relative_l2']):.6f} "
                + r"\\"
            ),
            (
                "Max. state abs. error & "
                f"{float(held_out['maximum_all_token_state_abs_error']):.6f} & "
                f"{float(extended['maximum_all_token_state_abs_error']):.6f} "
                + r"\\"
            ),
            (
                "Hard-event total (three counters) & "
                f"{_tex_integer(total_hard_events)} & {_tex_integer(hard_events)} "
                + r"\\"
            ),
            r"\midrule",
            (
                "Alignment underflows & -- & "
                f"{_tex_integer(extended['total_alignment_underflows'])} "
                + r"\\"
            ),
            (
                "E2M0 residual clips & -- & "
                f"{_tex_integer(extended['total_e2m0_residual_clips'])} "
                + r"\\"
            ),
            (
                "Log folds & -- & "
                f"{_tex_integer(extended['total_folds'])} "
                + r"\\"
            ),
            r"\bottomrule",
            r"\end{tabular}",
            "",
        ]
        quality_table.write_text("\n".join(quality_lines), encoding="utf-8")

    def macro_number(key: str, digits: int | None = None) -> str:
        value = numbers[key]["value"]
        return _format(value, digits) if digits is not None else str(value)

    def macro_integer(key: str) -> str:
        return _tex_integer(numbers[key]["value"])

    def macro_scientific(key: str) -> str:
        mantissa, exponent = f"{float(numbers[key]['value']):.0e}".split("e")
        return rf"{mantissa}\times 10^{{{int(exponent)}}}"

    macros = {
        "CorrectedLongTraceTokens": macro_integer(
            "corrected_extended_registered_tokens"
        ),
        "CorrectedHeldoutTraceTokens": macro_integer(
            "corrected_heldout_registered_tokens"
        ),
        "CorrectedHeldoutRunCount": macro_integer("corrected_heldout_run_count"),
        "CorrectedHeldoutSeedBlocks": macro_integer(
            "corrected_heldout_seed_block_count"
        ),
        "CorrectedHeldoutPairedConditions": macro_integer(
            "corrected_heldout_paired_condition_count"
        ),
        "CorrectedSeedHex": f"0x{int(numbers['controlled_seed']['value']):04X}",
        "CorrectedMxfpFourLogicalBitsPerValue": macro_number(
            "mxfp4_logical_bits_per_value", 2
        ),
        "CorrectedSyntheticInitialStateStdDev": macro_number(
            "synthetic_random_initial_state_standard_deviation", 2
        ),
        "CorrectedSyntheticValueStdDev": macro_number(
            "synthetic_value_standard_deviation", 2
        ),
        "CorrectedRelativeLTwoDenominatorFloor": macro_scientific(
            "synthetic_relative_l2_denominator_floor"
        ),
        "CorrectedNominalAlphaMinimum": macro_number(
            "synthetic_nominal_alpha_minimum", 3
        ),
        "CorrectedNominalAlphaMaximum": macro_number(
            "synthetic_nominal_alpha_maximum", 3
        ),
        "CorrectedNominalBetaMinimum": macro_number(
            "synthetic_nominal_beta_minimum", 3
        ),
        "CorrectedNominalBetaMaximum": macro_number(
            "synthetic_nominal_beta_maximum", 3
        ),
        "CorrectedHighRetentionAlphaMinimum": macro_number(
            "synthetic_high_retention_alpha_minimum", 3
        ),
        "CorrectedHighRetentionAlphaMaximum": macro_number(
            "synthetic_high_retention_alpha_maximum", 3
        ),
        "CorrectedHighRetentionBetaMinimum": macro_number(
            "synthetic_high_retention_beta_minimum", 3
        ),
        "CorrectedHighRetentionBetaMaximum": macro_number(
            "synthetic_high_retention_beta_maximum", 3
        ),
        "CorrectedQdqMxfpFourCosineEightK": macro_number(
            "qdq_mxfp4_token_8192_output_cosine", 6
        ),
        "CorrectedQdqMxfpFourStateRelLTwoEightK": macro_number(
            "qdq_mxfp4_token_8192_state_relative_l2", 6
        ),
        "CorrectedNativeEncodedCosineEightK": macro_number(
            "native_encoded_mxfp4_token_8192_output_cosine", 6
        ),
        "CorrectedNativeEncodedStateRelLTwoEightK": macro_number(
            "native_encoded_mxfp4_token_8192_state_relative_l2", 6
        ),
        "CorrectedNativeEncodedAlignmentUnderflowsEightK": macro_integer(
            "native_encoded_mxfp4_token_8192_alignment_underflows"
        ),
        "CorrectedBfSixteenCosineEightK": macro_number(
            "bf16_token_8192_output_cosine", 6
        ),
        "CorrectedBfSixteenStateRelLTwoEightK": macro_number(
            "bf16_token_8192_state_relative_l2", 6
        ),
        "CorrectedDynamicRangeBfSixteenCosineEightK": macro_number(
            "stress_dynamic_range_bf16_final_output_cosine", 6
        ),
        "CorrectedDynamicRangeBfSixteenStateRelLTwoEightK": macro_number(
            "stress_dynamic_range_bf16_final_state_relative_l2", 6
        ),
        "CorrectedDynamicRangeQdqMxfpFourCosineEightK": macro_number(
            "stress_dynamic_range_qdq_mxfp4_final_output_cosine", 6
        ),
        "CorrectedDynamicRangeQdqMxfpFourStateRelLTwoEightK": macro_number(
            "stress_dynamic_range_qdq_mxfp4_final_state_relative_l2", 6
        ),
        "CorrectedDynamicRangeMxfpEightStateCosineEightK": macro_number(
            "stress_dynamic_range_mxfp8_state_final_output_cosine", 6
        ),
        "CorrectedDynamicRangeMxfpEightStateRelLTwoEightK": macro_number(
            "stress_dynamic_range_mxfp8_state_final_state_relative_l2", 6
        ),
        "CorrectedCancellationBfSixteenCosineEightK": macro_number(
            "stress_cancellation_bf16_final_output_cosine", 6
        ),
        "CorrectedCancellationBfSixteenStateRelLTwoEightK": macro_number(
            "stress_cancellation_bf16_final_state_relative_l2", 6
        ),
        "CorrectedCancellationQdqMxfpFourCosineEightK": macro_number(
            "stress_cancellation_qdq_mxfp4_final_output_cosine", 6
        ),
        "CorrectedCancellationQdqMxfpFourStateRelLTwoEightK": macro_number(
            "stress_cancellation_qdq_mxfp4_final_state_relative_l2", 6
        ),
        "CorrectedCancellationMxfpEightStateCosineEightK": macro_number(
            "stress_cancellation_mxfp8_state_final_output_cosine", 6
        ),
        "CorrectedCancellationMxfpEightStateRelLTwoEightK": macro_number(
            "stress_cancellation_mxfp8_state_final_state_relative_l2", 6
        ),
        "CorrectedUniformToBfSixteenLutRatio": macro_number(
            "uniform_mxfp4_to_bf16_lut_ratio", 3
        ),
        "CorrectedUniformToBfSixteenStepRatio": macro_number(
            "uniform_mxfp4_to_bf16_step_cycles_max_ratio", 3
        ),
        "CorrectedHeldoutMinCheckpointCosine": macro_number(
            "corrected_heldout_min_checkpoint_output_cosine", 6
        ),
        "CorrectedHeldoutMinAllTokenCosine": macro_number(
            "corrected_heldout_min_all_token_output_cosine", 6
        ),
        "CorrectedHeldoutMaxFinalStateRelLTwo": macro_number(
            "corrected_heldout_max_final_state_relative_l2", 6
        ),
        "CorrectedHeldoutMaxAllTokenStateRelLTwo": macro_number(
            "corrected_heldout_max_all_token_state_relative_l2", 6
        ),
        "CorrectedTotalHardEvents": macro_integer(
            "corrected_total_preregistered_hard_events"
        ),
        "CorrectedLogicalStateBytes": macro_integer("corrected_logical_state_bytes"),
        "CorrectedMxfpEightStateBytes": macro_integer(
            "corrected_uniform_mxfp8_state_bytes"
        ),
        "CorrectedBytesBelowMxfpEight": macro_integer(
            "corrected_bytes_below_uniform_mxfp8"
        ),
        "CorrectedPercentBelowMxfpEight": macro_number(
            "corrected_percent_below_uniform_mxfp8", 3
        ),
        "CorrectedBfSixteenAllLayerStateMiB": macro_number(
            "bf16_all_layer_logical_state_mib", 2
        ),
        "CorrectedUniformMxfpFourAllLayerStateMiB": macro_number(
            "uniform_mxfp4_all_layer_logical_state_mib", 2
        ),
        "CorrectedBfSixteenIdealUram": macro_integer(
            "bf16_ideal_min_uram_for_mantissas"
        ),
        "CorrectedBfSixteenPhysicalFit": _escape(
            numbers["bf16_physical_fit_status"]["value"]
        ),
        "CorrectedBfSixteenRoute": _escape(
            numbers["bf16_route_completion_status"]["value"]
        ),
        "CorrectedBfSixteenTargetTiming": _escape(
            numbers["bf16_target_250mhz_status"]["value"]
        ),
        "CorrectedBfSixteenTargetWns": macro_number(
            "bf16_target_250mhz_wns_ns", 3
        ),
        "CorrectedBfSixteenClosingPeriod": macro_number(
            "bf16_first_tested_closing_period_ns", 3
        ),
        "CorrectedBfSixteenClosingFrequency": macro_number(
            "bf16_first_tested_closing_frequency_mhz", 2
        ),
        "CorrectedBfSixteenRoutedLut": macro_integer("bf16_routed_clb_lut"),
        "CorrectedBfSixteenRoutedFf": macro_integer("bf16_routed_ff"),
        "CorrectedBfSixteenRoutedBram": macro_number(
            "bf16_routed_bram_tiles", 1
        ),
        "CorrectedBfSixteenRoutedUram": macro_integer("bf16_routed_uram"),
        "CorrectedBfSixteenRoutedDsp": macro_integer("bf16_routed_dsp"),
        "CorrectedBfSixteenVectorlessPower": macro_number(
            "bf16_vectorless_power_first_closing_w", 3
        ),
        "CorrectedUniformMxfpFourIdealUram": macro_integer(
            "uniform_mxfp4_ideal_min_uram_for_mantissas"
        ),
        "CorrectedUniformMxfpFourIdealBram": macro_integer(
            "uniform_mxfp4_ideal_min_bram18k_for_scales"
        ),
        "CorrectedDeviceAvailableUram": macro_integer("u55c_available_uram"),
        "CorrectedBfSixteenStepInputBytes": macro_integer(
            "bf16_step_input_logical_bytes"
        ),
        "CorrectedUniformMxfpFourStepInputBytes": macro_integer(
            "uniform_mxfp4_step_input_logical_bytes"
        ),
        "CorrectedCandidateStepInputBytes": macro_integer(
            "corrected_candidate_step_input_logical_bytes"
        ),
        "CorrectedBfSixteenOutputBytes": macro_integer(
            "bf16_output_logical_bytes"
        ),
        "CorrectedNativeExpandedOutputBytes": macro_integer(
            "native_expanded_integer_output_logical_bytes"
        ),
        "CorrectedBfSixteenLut": macro_integer("bf16_hls_lut"),
        "CorrectedNativeEncodedMxfpFourLut": macro_integer(
            "uniform_mxfp4_hls_lut"
        ),
        "CorrectedBfSixteenStepMax": macro_integer("bf16_hls_step_cycles_max"),
        "CorrectedNativeEncodedMxfpFourStepMax": macro_integer(
            "uniform_mxfp4_hls_step_cycles_max"
        ),
        "CorrectedNativeMxfpEightLut": macro_integer(
            "native_mxfp8_hls_lut"
        ),
        "CorrectedNativeMxfpEightStepMax": macro_integer(
            "native_mxfp8_hls_step_cycles_max"
        ),
        "CorrectedNativeMxfpEightToBfSixteenLutRatio": macro_number(
            "native_mxfp8_to_bf16_lut_ratio", 3
        ),
        "CorrectedNativeMxfpEightToBfSixteenStepRatio": macro_number(
            "native_mxfp8_to_bf16_step_cycles_max_ratio", 3
        ),
        "CorrectedCandidateLut": macro_integer("corrected_candidate_hls_lut"),
        "CorrectedHlsToolVersion": _escape(
            numbers["corrected_candidate_hls_tool_version"]["value"]
        ),
        "CorrectedCandidateNonfoldStepMax": macro_integer(
            "corrected_candidate_nonfold_step_cycles_max"
        ),
        "CorrectedCandidateAmortizedStepMax": _tex_integer(
            round(float(numbers["corrected_candidate_amortized_cycles_max"]["value"]))
        ),
        "CorrectedCandidateToBfSixteenLutRatio": macro_number(
            "corrected_candidate_to_bf16_lut_ratio", 3
        ),
        "CorrectedCandidateToBfSixteenNonfoldRatio": macro_number(
            "corrected_candidate_to_bf16_nonfold_step_ratio", 3
        ),
        "CorrectedCandidateToBfSixteenAmortizedRatio": macro_number(
            "corrected_candidate_to_bf16_amortized_step_ratio", 3
        ),
        "CorrectedCandidatePathNs": macro_number(
            "corrected_candidate_hls_estimated_clock_ns", 3
        ),
        "CorrectedConfiguredTimingBudgetNs": macro_number(
            "corrected_effective_hls_timing_budget_ns", 3
        ),
        "CorrectedConfiguredTimingShortfallNs": macro_number(
            "corrected_configured_hls_timing_shortfall_ns", 3
        ),
        "CorrectedCandidateDsp": macro_integer("corrected_candidate_hls_dsp"),
        "CorrectedPostroutePhysicalFit": _escape(
            numbers["corrected_postroute_physical_fit"]["value"]
        ),
        "CorrectedPostrouteTwoFiftyStatus": _escape(
            numbers["corrected_postroute_250mhz_status"]["value"]
        ),
        "CorrectedPostrouteTargetMhz": macro_number(
            "corrected_postroute_target_frequency_mhz", 0
        ),
        "CorrectedPostrouteTwoFiftyWnsNs": macro_number(
            "corrected_postroute_250mhz_wns_ns", 3
        ),
        "CorrectedPostrouteTwoHundredStatus": _escape(
            numbers["corrected_postroute_200mhz_status"]["value"]
        ),
        "CorrectedPostrouteSecondaryMhz": macro_number(
            "corrected_postroute_secondary_frequency_mhz", 0
        ),
        "CorrectedPostrouteFirstClosingPeriodNs": macro_number(
            "corrected_postroute_first_closing_period_ns", 2
        ),
        "CorrectedPostrouteFirstClosingMhz": macro_number(
            "corrected_postroute_first_closing_frequency_mhz", 2
        ),
        "CorrectedPostrouteCriticalPathNs": macro_number(
            "corrected_postroute_critical_path_ns", 3
        ),
        "CorrectedPostrouteCriticalRoutePercent": macro_number(
            "corrected_postroute_critical_route_percent", 1
        ),
        "CorrectedPostrouteCriticalLogicLevels": macro_integer(
            "corrected_postroute_critical_logic_levels"
        ),
        "CorrectedPostrouteLut": macro_integer("corrected_postroute_lut_used"),
        "CorrectedPostrouteFf": macro_integer("corrected_postroute_ff_used"),
        "CorrectedPostrouteBram": macro_integer(
            "corrected_postroute_bram_tiles_used"
        ),
        "CorrectedPostrouteUram": macro_integer("corrected_postroute_uram_used"),
        "CorrectedPostrouteDsp": macro_integer("corrected_postroute_dsp_used"),
        "CorrectedPostrouteUramPercent": macro_number(
            "corrected_postroute_uram_utilization_percent", 1
        ),
        "CorrectedPostrouteDrcWarnings": macro_integer(
            "corrected_postroute_drc_warning_count"
        ),
        "CorrectedPostroutePowerTotalW": macro_number(
            "corrected_postroute_power_total_w", 3
        ),
        "CorrectedPostroutePowerPeriodNs": macro_number(
            "corrected_postroute_power_period_ns", 1
        ),
        "CorrectedPostroutePowerDynamicW": macro_number(
            "corrected_postroute_power_dynamic_w", 3
        ),
        "CorrectedPostroutePowerStaticW": macro_number(
            "corrected_postroute_power_static_w", 3
        ),
        "CorrectedPostroutePowerConfidence": _escape(
            numbers["corrected_postroute_power_confidence"]["value"]
        ),
        "CorrectedEZeroControlCosimStatus": _escape(
            numbers["corrected_e2m0_control_cosim_status"]["value"]
        ),
        "CorrectedEZeroControlCosimCommands": macro_integer(
            "corrected_e2m0_control_cosim_commands"
        ),
        "CorrectedEZeroControlCosimLatency": macro_integer(
            "corrected_e2m0_control_cosim_latency_cycles"
        ),
        "CorrectedEZeroRtlSixtyFourStatus": _escape(
            numbers["corrected_e2m0_rtl_64_token_status"]["value"]
        ),
        "CorrectedEZeroRtlTraceTokens": macro_integer(
            "corrected_e2m0_rtl_trace_tokens"
        ),
        "CorrectedEZeroRtlTransactions": macro_integer(
            "corrected_e2m0_rtl_transactions"
        ),
        "CorrectedEZeroRtlOutputValues": macro_integer(
            "corrected_e2m0_rtl_output_values_compared"
        ),
        "CorrectedEZeroHlsCsimSixtyFourStatus": _escape(
            numbers["corrected_e2m0_hls_csim_64_token_status"]["value"]
        ),
        "CorrectedEZeroRtlDirectLoadStatus": _escape(
            numbers["corrected_e2m0_rtl_direct_load_status"]["value"]
        ),
        "CorrectedEZeroRtlDirectLoadCycles": macro_integer(
            "corrected_e2m0_rtl_direct_load_cycles"
        ),
        "CorrectedEZeroRtlCompletedSteps": macro_integer(
            "corrected_e2m0_rtl_completed_recurrent_steps"
        ),
        "CorrectedMxfpEightPostrouteFit": _escape(
            numbers["mxfp8_postroute_physical_fit"]["value"]
        ),
        "CorrectedMxfpEightPostrouteTwoFiftyStatus": _escape(
            numbers["mxfp8_postroute_250mhz_status"]["value"]
        ),
        "CorrectedMxfpEightPostrouteTwoFiftyWns": macro_number(
            "mxfp8_postroute_250mhz_wns_ns", 3
        ),
        "CorrectedMxfpEightPostrouteFirstClosingPeriodNs": macro_number(
            "mxfp8_postroute_first_closing_period_ns", 2
        ),
        "CorrectedMxfpEightPostrouteFirstClosingMhz": macro_number(
            "mxfp8_postroute_first_closing_frequency_mhz", 2
        ),
        "CorrectedMxfpEightPostrouteLut": macro_integer(
            "mxfp8_postroute_lut_used"
        ),
        "CorrectedMxfpEightPostrouteFf": macro_integer(
            "mxfp8_postroute_ff_used"
        ),
        "CorrectedMxfpEightPostrouteBram": macro_integer(
            "mxfp8_postroute_bram_tiles_used"
        ),
        "CorrectedMxfpEightPostrouteUram": macro_integer(
            "mxfp8_postroute_uram_used"
        ),
        "CorrectedMxfpEightPostrouteDsp": macro_integer(
            "mxfp8_postroute_dsp_used"
        ),
        "CorrectedMxfpEightPostroutePowerTotalW": macro_number(
            "mxfp8_postroute_power_total_w", 3
        ),
        "CorrectedMxfpEightPostroutePowerPeriodNs": macro_number(
            "mxfp8_postroute_power_period_ns", 2
        ),
        "CorrectedMxfpEightPostroutePowerConfidence": _escape(
            numbers["mxfp8_postroute_power_confidence"]["value"]
        ),
        "CorrectedQwenCaptureLayer": macro_integer("qwen_capture_layer_index"),
        "CorrectedQwenCaptureElements": macro_integer(
            "qwen_capture_layer_input_elements"
        ),
        "CorrectedQwenCaptureAbsPnn": macro_number(
            "qwen_capture_layer_input_abs_p99", 4
        ),
        "CorrectedQwenCaptureAbsPnnn": macro_number(
            "qwen_capture_layer_input_abs_p999", 4
        ),
        "CorrectedQwenCaptureAbsMax": macro_number(
            "qwen_capture_layer_input_abs_max", 2
        ),
        "CorrectedQwenCaptureMaxToPnn": macro_number(
            "qwen_capture_layer_input_max_to_p99_ratio", 1
        ),
        "CorrectedQwenRecurrentPromptCount": macro_integer(
            "qwen_recurrent_prompt_count"
        ),
        "CorrectedQwenRecurrentTotalTokens": macro_integer(
            "qwen_recurrent_total_valid_tokens"
        ),
        "CorrectedQwenRecurrentMinTokens": macro_integer(
            "qwen_recurrent_min_valid_tokens"
        ),
        "CorrectedQwenRecurrentMaxTokens": macro_integer(
            "qwen_recurrent_max_valid_tokens"
        ),
        "CorrectedQwenRecurrentBfSixteenMeanFinalCosine": macro_number(
            "qwen_recurrent_bf16_mean_final_output_cosine", 6
        ),
        "CorrectedQwenRecurrentBfSixteenMeanStateRelLTwo": macro_number(
            "qwen_recurrent_bf16_mean_final_state_relative_l2", 6
        ),
        "CorrectedQwenRecurrentMxfpFourMeanFinalCosine": macro_number(
            "qwen_recurrent_mxfp4_mean_final_output_cosine", 6
        ),
        "CorrectedQwenRecurrentMxfpFourMeanStateRelLTwo": macro_number(
            "qwen_recurrent_mxfp4_mean_final_state_relative_l2", 6
        ),
        "CorrectedQwenRecurrentMxfpEightStateMeanFinalCosine": macro_number(
            "qwen_recurrent_mxfp8_state_mean_final_output_cosine", 6
        ),
        "CorrectedQwenRecurrentMxfpEightStateMeanStateRelLTwo": macro_number(
            "qwen_recurrent_mxfp8_state_mean_final_state_relative_l2", 6
        ),
        "CorrectedQwenRecurrentIntFourMeanFinalCosine": macro_number(
            "qwen_recurrent_flat_int4_mean_final_output_cosine", 6
        ),
        "CorrectedQwenRecurrentIntFourMeanStateRelLTwo": macro_number(
            "qwen_recurrent_flat_int4_mean_final_state_relative_l2", 6
        ),
        "CorrectedQwenRecurrentRsTwoMeanFinalCosine": macro_number(
            "qwen_recurrent_rs2_mean_final_output_cosine", 6
        ),
        "CorrectedQwenRecurrentRsTwoWorstCosine": macro_number(
            "qwen_recurrent_rs2_worst_output_cosine", 6
        ),
        "CorrectedQwenRecurrentRsTwoMeanStateRelLTwo": macro_number(
            "qwen_recurrent_rs2_mean_final_state_relative_l2", 6
        ),
        "CorrectedQwenRecurrentRsTwoWorstStateRelLTwo": macro_number(
            "qwen_recurrent_rs2_worst_state_relative_l2", 6
        ),
        "CorrectedQwenRecurrentRsTwoAccumulatorSaturations": macro_integer(
            "qwen_recurrent_rs2_accumulator_saturations"
        ),
        "CorrectedCandidateFailedIiLoops": macro_integer(
            "corrected_failed_ii_one_loop_count"
        ),
        "CorrectedTargetIi": macro_integer("corrected_target_loop_ii"),
        "CorrectedFailedLoopIi": macro_integer("corrected_failed_loop_final_ii"),
        "CorrectedCandidateSlrLutPercent": _format(
            numbers["corrected_reported_one_slr_lut_percent"]["value"], 0
        ),
        "CorrectedFoldPeriodTokens": macro_integer("corrected_fold_period_tokens"),
        "CorrectedFoldBurstCyclesMax": macro_integer(
            "corrected_fold_burst_cycles_max"
        ),
        "CorrectedTopCommandCyclesMax": macro_integer(
            "corrected_top_command_cycles_max"
        ),
        "CorrectedCorrectionMachineryLut": macro_integer(
            "corrected_correction_machinery_lut"
        ),
        "CorrectedCorrectionMachineryLutPercent": macro_number(
            "corrected_correction_machinery_lut_percent_of_top", 1
        ),
        "CorrectedArithmeticCsimCases": macro_integer(
            "corrected_arithmetic_csim_cases"
        ),
        "CorrectedStatefulCsimTokens": macro_integer(
            "corrected_stateful_csim_tokens"
        ),
        "CorrectedFixedScaleCosineEightK": macro_number(
            "scale_policy_fixed_token_8192_output_cosine_fp32", 6
        ),
        "CorrectedFixedScaleClipsEightK": macro_integer(
            "scale_policy_fixed_token_8192_state_element_saturations_cumulative"
        ),
        "CorrectedEveryTokenScaleClipsEightK": macro_integer(
            "scale_policy_every_token_token_8192_state_element_saturations_cumulative"
        ),
        "CorrectedScalePolicyCount": macro_integer("controlled_scale_policy_count"),
        "CorrectedNumLayers": macro_integer("controlled_num_layers"),
        "CorrectedNumQkHeads": macro_integer("controlled_num_qk_heads"),
        "CorrectedNumValueHeads": macro_integer("controlled_num_value_heads"),
        "CorrectedKeyDim": macro_integer("controlled_key_dim"),
        "CorrectedValueDim": macro_integer("controlled_value_dim"),
        "CorrectedPk": macro_integer("controlled_p_k"),
        "CorrectedPv": macro_integer("controlled_p_v"),
        "CorrectedBlockSize": macro_integer("controlled_block_size"),
        "CorrectedTargetClockNs": macro_number("controlled_target_clock_ns"),
        "CorrectedLogCapacity": macro_integer("corrected_log_capacity"),
        "CorrectedAccumulatorBits": macro_integer("corrected_accumulator_bits"),
        "CorrectedAlignmentGuardBits": macro_integer(
            "corrected_alignment_guard_bits"
        ),
        "CorrectedEZeroResidualBits": macro_integer(
            "corrected_e2m0_residual_bits"
        ),
        "CorrectedResidualStackTerms": macro_integer(
            "corrected_residual_stack_terms"
        ),
        "CorrectedOutputCosineThreshold": macro_number(
            "controlled_checkpoint_output_cosine_minimum", 2
        ),
        "CorrectedFinalStateRelLTwoThreshold": macro_number(
            "controlled_final_state_relative_l2_maximum", 2
        ),
        "CorrectedStateRelLTwoSensitivityProbe": macro_number(
            "corrected_state_l2_sensitivity_probe", 2
        ),
        "CorrectedExtendedStateRelLTwoGateMargin": macro_number(
            "corrected_extended_state_l2_gate_margin", 6
        ),
        "CorrectedCheckpointSet": ", ".join(
            f"{int(value):,}".replace(",", r"{,}") for value in checkpoints
        ),
        "CorrectedETwoMOneSignBits": macro_integer("mxfp4_e2m1_sign_bits"),
        "CorrectedETwoMOneExponentBits": macro_integer(
            "mxfp4_e2m1_exponent_bits"
        ),
        "CorrectedETwoMOneMantissaBits": macro_integer(
            "mxfp4_e2m1_mantissa_bits"
        ),
        "CorrectedETwoMOneMagnitudeCodebook": ", ".join(
            _format(value, 1) if isinstance(value, float) else str(value)
            for value in numbers["mxfp4_e2m1_positive_magnitudes"]["value"]
        ),
        "CorrectedEEightMZeroValidMinimum": macro_integer(
            "mxfp4_e8m0_valid_code_minimum"
        ),
        "CorrectedEEightMZeroValidMaximum": macro_integer(
            "mxfp4_e8m0_valid_code_maximum"
        ),
        "CorrectedEEightMZeroInvalidCode": macro_integer(
            "mxfp4_e8m0_invalid_code"
        ),
        "CorrectedEEightMZeroBias": macro_integer("mxfp4_e8m0_exponent_bias"),
        "CorrectedEEightMZeroZeroBlockScale": macro_integer(
            "mxfp4_e8m0_zero_block_scale_code"
        ),
    }
    if extended is not None:
        macros.update(
            {
                "CorrectedExtendedQualityStatus": _escape(
                    numbers["corrected_extended_quality_status"]["value"]
                ),
                "CorrectedExtendedReplayStatus": _escape(
                    numbers["corrected_extended_replay_status"]["value"]
                ),
                "CorrectedExtendedRunCount": macro_integer(
                    "corrected_extended_run_count"
                ),
                "CorrectedExtendedRecomputedRunCount": macro_integer(
                    "corrected_extended_recomputed_run_count"
                ),
                "CorrectedExtendedMinCheckpointCosine": macro_number(
                    "corrected_extended_minimum_checkpoint_output_cosine", 6
                ),
                "CorrectedExtendedMaxFinalStateRelLTwo": macro_number(
                    "corrected_extended_maximum_final_state_relative_l2", 6
                ),
                "CorrectedExtendedMinAllTokenCosine": macro_number(
                    "corrected_extended_minimum_all_token_output_cosine", 6
                ),
                "CorrectedExtendedMaxAllTokenStateRelLTwo": macro_number(
                    "corrected_extended_maximum_all_token_state_relative_l2", 6
                ),
                "CorrectedExtendedMaxAllTokenStateAbsError": macro_number(
                    "corrected_extended_maximum_all_token_state_abs_error", 6
                ),
                "CorrectedExtendedTotalElementSaturations": macro_integer(
                    "corrected_extended_total_element_saturations"
                ),
                "CorrectedExtendedTotalAccumulatorSaturations": macro_integer(
                    "corrected_extended_total_accumulator_saturations"
                ),
                "CorrectedExtendedTotalScaleClamps": macro_integer(
                    "corrected_extended_total_scale_clamps"
                ),
                "CorrectedExtendedTotalAlignmentUnderflows": macro_integer(
                    "corrected_extended_total_alignment_underflows"
                ),
                "CorrectedExtendedTotalResidualClips": macro_integer(
                    "corrected_extended_total_e2m0_residual_clips"
                ),
                "CorrectedExtendedTotalFolds": macro_integer(
                    "corrected_extended_total_folds"
                ),
            }
        )
    macro_text = "\n".join(
        f"\\newcommand{{\\{name}}}{{{value}}}" for name, value in macros.items()
    ) + "\n"
    (snippets / "corrected_result_macros.tex").write_text(macro_text, encoding="utf-8")

    inputs = (*required, *((EXTENDED,) if EXTENDED.exists() else ()))
    generated_outputs = [
        output / "numbers.json",
        output / "provenance.json",
        snippets / "corrected_result_macros.tex",
        tables / "long_sequence.tex",
        tables / "controlled_hls.tex",
        tables / "qwen_recurrent_stability.tex",
        tables / "mitigation_hls.tex",
        tables / "resource_ablation.tex",
        tables / "corrected_heldout.tex",
        tables / "scale_policy.tex",
        tables / "postroute_evidence.tex",
        *((extended_table, quality_table) if extended is not None else ()),
    ]
    manifest = {
        "schema": 1,
        "status": "PASS",
        "scope": "corrected manuscript assets generated from verified evidence",
        "generated_at": timestamp,
        "source_revision": revision,
        "source_identity": source_identity,
        "extended_8192_status": extended_status,
        "extended_8192_replay_status": extended_replay_status,
        "verified_figure_sha256": {
            relative: str(expected).upper()
            for relative, expected in {
                **plot_manifest["outputs"],
                **(datapath_manifest["outputs"] if datapath_values_match else {}),
                **long_panel_manifest["outputs"],
                **tradeoff_manifest["outputs"],
            }.items()
        },
        "inputs_sha256": {
            _display_path(path): _sha256(path) for path in inputs
        },
        "outputs_sha256": {
            _display_path(path): _sha256(path)
            for path in generated_outputs
        },
        "limitations": [
            "asset generation does not authorize PDF generation or submission",
            "audit-PDF, visual-review, finalization, and release gates are separate",
        ],
    }
    (output / "asset_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = generate(_resolve(args.output))
    print(json.dumps({"status": result["status"], "output": str(_resolve(args.output))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

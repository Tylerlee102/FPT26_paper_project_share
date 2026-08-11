"""Overlay selected RS2/R3 evidence onto the corrected manuscript assets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts import corrected_datapath_figure, corrected_paper_assets
from scripts.evidence_source_snapshot import describe_source_files
from scripts.rs2_paper_figures import generate as generate_figures


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "paper" / "corrected"
CONTROLLED = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_controlled"
    / "controlled_long_trace_checkpoints.csv"
)
CONTROLLED_MANIFEST = CONTROLLED.with_name("controlled_long_trace_manifest.json")
CANDIDATE = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_encoded"
    / "rs2_encoded_candidate_summary.json"
)
REGISTRATION = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_encoded_candidate_preregistration.json"
)
RS2_HLS = ROOT / "reports" / "csynth" / "corrected" / "rs2_hls_summary.json"
MXFP8_HLS = ROOT / "reports" / "csynth" / "corrected" / "mxfp8_hls_summary.json"
RS2_VIVADO = (
    ROOT
    / "reports"
    / "vivado"
    / "corrected"
    / "rs2_current"
    / "rs2_vivado_summary.json"
)
BF16_VIVADO = (
    ROOT
    / "reports"
    / "vivado"
    / "baselines"
    / "bf16"
    / "bf16_vivado_summary.json"
)
MXFP8_VIVADO = (
    ROOT
    / "reports"
    / "vivado"
    / "baselines"
    / "mxfp8"
    / "mxfp8_vivado_summary.json"
)
RS2_RTL = (
    ROOT
    / "reports"
    / "cosim"
    / "corrected"
    / "rs2_current"
    / "trace64_direct"
    / "rs2_trace64_direct_summary.json"
)
QWEN = ROOT / "reports" / "benchmark" / "qwen_recurrent_stability_manifest.json"
SCALE_POLICY = (
    ROOT / "reports" / "benchmark" / "corrected" / "scale_policy_manifest.json"
)
INTERFACE = (
    ROOT / "reports" / "benchmark" / "corrected" / "rs2_interface_accounting.json"
)
URAM_LATENCY_EXPERIMENT = (
    ROOT
    / "reports"
    / "csynth"
    / "experiments"
    / "rs2_uram_latency2_20260809"
    / "summary.json"
)
TIMING_EXPERIMENTS = (
    (
        "fold_control",
        "Local fold control",
        ROOT / "reports/vivado/experiments/rs2_fold_control_20260809/summary.json",
        "Better; misses target",
    ),
    (
        "fold_write",
        "Fold-write commit",
        ROOT / "reports/vivado/experiments/rs2_fold_write_20260809/summary.json",
        "Best WNS; misses target",
    ),
    (
        "layer_banks",
        "Full layer partition",
        ROOT / "reports/vivado/experiments/rs2_layer_banks_20260810/summary.json",
        "Worse timing and cost",
    ),
    (
        "partial_layer_banks",
        "Six-way layer banks",
        ROOT / "reports/vivado/experiments/rs2_partial_layer_banks_20260810/summary.json",
        "WNS gain; worse TNS",
    ),
    (
        "fold_write_partial_banks",
        "Banks + fold-write",
        ROOT / "reports/vivado/experiments/rs2_fold_write_partial_banks_20260810/summary.json",
        "Worse than both parents",
    ),
    (
        "snapshot_write_partial_banks",
        "Snapshot commit + banks",
        ROOT / "reports/vivado/experiments/rs2_snapshot_write_partial_banks_20260810/summary.json",
        "WNS gain; worse TNS",
    ),
    (
        "split_fold_write",
        "Split fold writes",
        ROOT / "reports/vivado/experiments/rs2_split_fold_write_20260810/summary.json",
        "Worse than parent",
    ),
    (
        "snapshot_write_unbanked",
        "Snapshot commit, unbanked",
        ROOT / "reports/vivado/experiments/rs2_snapshot_write_unbanked_20260810/summary.json",
        "Worse than parent",
    ),
    (
        "fold_write_contiguous_banks",
        "Two contiguous banks",
        ROOT / "reports/vivado/experiments/rs2_fold_write_contiguous_banks_20260810/summary.json",
        "AXI/SLR regression",
    ),
    (
        "snapshot_write_contiguous_banks",
        "Snapshot + contiguous banks",
        ROOT / "reports/vivado/experiments/rs2_snapshot_write_contiguous_banks_20260810/summary.json",
        "Top-FSM regression",
    ),
    (
        "snapshot_write_unbanked_fsm_fanout16",
        "FSM fanout 16",
        ROOT / "reports/vivado/experiments/rs2_snapshot_write_unbanked_fsm_fanout16_20260810/summary.json",
        "Replication worsens setup",
    ),
    (
        "fold_write_address_fanout16",
        "Address fanout 16",
        ROOT / "reports/vivado/experiments/rs2_fold_write_address_fanout16_20260810/summary.json",
        "Origins move; setup worsens",
    ),
)

CHECKPOINTS = (64, 256, 1024, 4096, 8192)
VARIANTS = {
    "fp32": "fp32",
    "bf16_qdq_fp32_accum_state_bf16": "bf16",
    "mxfp4_qdq_act_b32_state_b32": "mxfp4_qdq",
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32": "mxfp8_state",
    "flat_int4_qdq": "int4",
    "mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5": "rs2",
}
DISPLAY = {
    "fp32": "FP32 reference",
    "bf16": "BF16 operands/state",
    "mxfp4_qdq": "MXFP4 floating Q/DQ",
    "mxfp8_state": "MXFP4 + MXFP8 state",
    "int4": "Flat INT4",
    "rs2": "Native MXFP4 RS2/R3",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _git_revision() -> str:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _load_json(path: Path, *, required_status: str = "PASS") -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    if required_status and payload.get("status") != required_status:
        raise ValueError(
            f"RS2 paper evidence is not {required_status}: {path} "
            f"({payload.get('status')})"
        )
    return payload


def _line(path: Path, marker: str) -> int:
    for number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        if marker in line:
            return number
    raise ValueError(f"marker {marker!r} is absent from {path}")


def _line_after(path: Path, anchor: str, marker: str) -> int:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(
        (index for index, line in enumerate(lines) if anchor in line), None
    )
    if start is None:
        raise ValueError(f"anchor {anchor!r} is absent from {path}")
    for index in range(start, len(lines)):
        if marker in lines[index]:
            return index + 1
    raise ValueError(f"marker {marker!r} after {anchor!r} is absent from {path}")


def _record(
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
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"nonfinite paper number: {key}")
    row = {
        "value": value,
        "units": units,
        "source": _relative(source),
        "source_line": source_line,
        "extractor": "scripts.rs2_paper_assets",
        "git_sha": revision,
        "timestamp": timestamp,
    }
    numbers[key] = row
    provenance[key] = dict(row)


def _json_record(
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
    _record(
        numbers,
        provenance,
        key=key,
        value=value,
        units=units,
        source=source,
        source_line=_line(source, marker),
        revision=revision,
        timestamp=timestamp,
    )


def _tex_int(value: object) -> str:
    return f"{int(value):,}".replace(",", r"{,}")


def _tex_value(value: object, digits: int = 6) -> str:
    if isinstance(value, str):
        return value.replace("_", r"\_")
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, int):
        return _tex_int(value)
    return f"{float(value):.{digits}f}"


def _write_table(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _controlled_rows() -> tuple[list[dict[str, str]], dict[tuple[str, int], int]]:
    with CONTROLLED.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    line_by_key = {
        (row["variant"], int(row["token_index"])): index + 2
        for index, row in enumerate(rows)
    }
    expected = {
        (variant, token) for variant in VARIANTS for token in CHECKPOINTS
    }
    observed = {(row["variant"], int(row["token_index"])) for row in rows}
    if observed != expected or len(rows) != len(expected):
        raise ValueError("controlled RS2 checkpoint matrix is incomplete")
    return rows, line_by_key


def _add_controlled_numbers(
    numbers: dict[str, dict[str, object]],
    provenance: dict[str, dict[str, object]],
    rows: list[dict[str, str]],
    lines: dict[tuple[str, int], int],
    revision: str,
    timestamp: str,
) -> dict[tuple[str, int], dict[str, str]]:
    by_key = {(row["variant"], int(row["token_index"])): row for row in rows}
    for variant, slug in VARIANTS.items():
        for token in CHECKPOINTS:
            row = by_key[(variant, token)]
            source_line = lines[(variant, token)]
            for field, suffix, units in (
                ("output_cosine_fp32", "output_cosine", "cosine"),
                ("state_rel_l2", "state_relative_l2", "relative_l2"),
                ("state_max_abs", "state_max_abs", "absolute"),
            ):
                _record(
                    numbers,
                    provenance,
                    key=f"rs2_{slug}_token_{token}_{suffix}",
                    value=float(row[field]),
                    units=units,
                    source=CONTROLLED,
                    source_line=source_line,
                    revision=revision,
                    timestamp=timestamp,
                )
    return by_key


def _add_candidate_numbers(
    numbers: dict[str, dict[str, object]],
    provenance: dict[str, dict[str, object]],
    candidate: dict[str, object],
    registration: dict[str, object],
    revision: str,
    timestamp: str,
) -> None:
    held = candidate["gate_results"]["held_out"]
    extended = candidate["gate_results"]["extended_development"]
    if held["status"] != "PASS" or extended["status"] != "PASS":
        raise ValueError("selected RS2 candidate has not passed both registered gates")
    specs = {
        "rs2_candidate_name": (candidate["candidate_name"], "identifier", '"candidate_name"', '"candidate_name"'),
        "rs2_heldout_run_count": (held["run_count"], "runs", '"held_out": {', '"run_count"'),
        "rs2_heldout_min_all_token_cosine": (
            held["minimum_all_token_output_cosine"], "cosine", '"held_out": {', '"minimum_all_token_output_cosine"'
        ),
        "rs2_heldout_max_all_token_state_relative_l2": (
            held["maximum_all_token_state_relative_l2"], "relative_l2", '"held_out": {', '"maximum_all_token_state_relative_l2"'
        ),
        "rs2_heldout_max_final_state_relative_l2": (
            held["maximum_final_state_relative_l2"], "relative_l2", '"held_out": {', '"maximum_final_state_relative_l2"'
        ),
        "rs2_heldout_max_state_abs_error": (
            held["maximum_state_absolute_error"], "absolute", '"held_out": {', '"maximum_state_absolute_error"'
        ),
        "rs2_extended_run_count": (extended["run_count"], "runs", '"extended_development": {', '"run_count"'),
        "rs2_extended_min_all_token_cosine": (
            extended["minimum_all_token_output_cosine"], "cosine", '"extended_development": {', '"minimum_all_token_output_cosine"'
        ),
        "rs2_extended_max_all_token_state_relative_l2": (
            extended["maximum_all_token_state_relative_l2"], "relative_l2", '"extended_development": {', '"maximum_all_token_state_relative_l2"'
        ),
        "rs2_extended_max_final_state_relative_l2": (
            extended["maximum_final_state_relative_l2"], "relative_l2", '"extended_development": {', '"maximum_final_state_relative_l2"'
        ),
        "rs2_extended_max_state_abs_error": (
            extended["maximum_state_absolute_error"], "absolute", '"extended_development": {', '"maximum_state_absolute_error"'
        ),
        "rs2_extended_element_saturations": (
            extended["cumulative_element_saturations"], "events", '"extended_development": {', '"cumulative_element_saturations"'
        ),
        "rs2_extended_accumulator_saturations": (
            extended["cumulative_accumulator_saturations"], "events", '"extended_development": {', '"cumulative_accumulator_saturations"'
        ),
        "rs2_extended_scale_clamps": (
            extended["cumulative_scale_clamps"], "events", '"extended_development": {', '"cumulative_scale_clamps"'
        ),
    }
    for key, (value, units, anchor, marker) in specs.items():
        _record(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=CANDIDATE,
            source_line=_line_after(CANDIDATE, anchor, marker),
            revision=revision,
            timestamp=timestamp,
        )

    logical = registration["logical_state_bytes"]
    for slug, field in (
        ("candidate", "encoded_candidate"),
        ("bf16", "uniform_bf16"),
        ("mxfp8", "uniform_mxfp8_e4m3_b32"),
    ):
        _json_record(
            numbers,
            provenance,
            key=f"rs2_{slug}_logical_state_bytes",
            value=int(logical[field]),
            units="bytes/layer",
            source=REGISTRATION,
            marker=f'"{field}"',
            revision=revision,
            timestamp=timestamp,
        )
    _json_record(
        numbers,
        provenance,
        key="rs2_quality_minimum_cosine_gate",
        value=float(registration["quality_gate"]["minimum_all_token_output_cosine"]),
        units="cosine",
        source=REGISTRATION,
        marker='"minimum_all_token_output_cosine"',
        revision=revision,
        timestamp=timestamp,
    )
    _json_record(
        numbers,
        provenance,
        key="rs2_quality_maximum_state_relative_l2_gate",
        value=float(registration["quality_gate"]["maximum_all_token_state_relative_l2"]),
        units="relative_l2",
        source=REGISTRATION,
        marker='"maximum_all_token_state_relative_l2"',
        revision=revision,
        timestamp=timestamp,
    )


def _add_hardware_numbers(
    numbers: dict[str, dict[str, object]],
    provenance: dict[str, dict[str, object]],
    hls: dict[str, object],
    mxfp8_hls: dict[str, object],
    route: dict[str, object],
    rtl: dict[str, object],
    bf16_route: dict[str, object],
    mxfp8_route: dict[str, object],
    revision: str,
    timestamp: str,
) -> None:
    metrics = hls["csynth"]["metrics"]
    resources = metrics["resources"]
    comparison = hls["comparison"]
    hls_specs = {
        "rs2_hls_estimated_clock_ns": (metrics["estimated_clock_ns"], "ns", '"estimated_clock_ns"'),
        "rs2_hls_estimated_fmax_mhz": (metrics["estimated_fmax_mhz"], "MHz", '"estimated_fmax_mhz"'),
        "rs2_hls_lut": (resources["LUT"], "LUT", '"LUT"'),
        "rs2_hls_ff": (resources["FF"], "FF", '"FF"'),
        "rs2_hls_bram18k": (resources["BRAM_18K"], "BRAM18K", '"BRAM_18K"'),
        "rs2_hls_uram": (resources["URAM"], "URAM", '"URAM"'),
        "rs2_hls_dsp": (resources["DSP"], "DSP", '"DSP"'),
        "rs2_hls_nonfold_step_cycles_max": (
            hls["csynth"]["step_loop_latency_cycles"]["maximum"], "cycles", '"step_loop_latency_cycles"'
        ),
        "rs2_hls_fold_cycles_max": (
            hls["csynth"]["fold_latency_cycles"]["maximum"], "cycles", '"fold_latency_cycles"'
        ),
        "rs2_hls_amortized_cycles_max": (
            hls["csynth"]["steady_state_amortized_cycles_per_token"]["maximum"], "cycles/STEP", '"steady_state_amortized_cycles_per_token"'
        ),
        "rs2_hls_lut_ratio_to_bf16": (
            comparison["lut_ratio_rs2_to_bf16"], "ratio", '"lut_ratio_rs2_to_bf16"'
        ),
        "rs2_hls_nonfold_cycle_ratio_to_bf16": (
            comparison["nonfold_step_cycle_ratio_rs2_to_bf16"], "ratio", '"nonfold_step_cycle_ratio_rs2_to_bf16"'
        ),
        "rs2_hls_amortized_cycle_ratio_to_bf16": (
            comparison["amortized_cycle_ratio_rs2_to_bf16"], "ratio", '"amortized_cycle_ratio_rs2_to_bf16"'
        ),
        "rs2_hls_cost_latency_advantage": (
            comparison["hls_cost_latency_advantage_vs_bf16"], "status", '"hls_cost_latency_advantage_vs_bf16"'
        ),
        "rs2_hls_explicit_ii1_status": (
            hls["csynth"]["targeted_loop_ii_status"], "status", '"targeted_loop_ii_status"'
        ),
    }
    for key, (value, units, marker) in hls_specs.items():
        _json_record(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=RS2_HLS,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )
    for row in hls["comparison_rows"]:
        if row["variant"] == "BF16":
            for field, suffix, units in (
                ("lut", "lut", "LUT"),
                ("ff", "ff", "FF"),
                ("bram_18k", "bram18k", "BRAM18K"),
                ("uram", "uram", "URAM"),
                ("dsp", "dsp", "DSP"),
                ("step_cycles_max", "step_cycles_max", "cycles"),
                ("amortized_cycles_max", "amortized_cycles_max", "cycles/STEP"),
                ("estimated_fmax_mhz", "estimated_fmax_mhz", "MHz"),
            ):
                _json_record(
                    numbers,
                    provenance,
                    key=f"rs2_bf16_hls_{suffix}",
                    value=row[field],
                    units=units,
                    source=RS2_HLS,
                    marker='"variant": "BF16"',
                    revision=revision,
                    timestamp=timestamp,
                )
            break
    else:
        raise ValueError("RS2 HLS report has no BF16 comparison row")

    mx_metrics = mxfp8_hls["csynth"]["metrics"]
    _json_record(
        numbers,
        provenance,
        key="rs2_mxfp8_hls_step_cycles_max",
        value=mxfp8_hls["csynth"]["step_loop_latency_cycles"]["maximum"],
        units="cycles/STEP",
        source=MXFP8_HLS,
        marker='"step_loop_latency_cycles"',
        revision=revision,
        timestamp=timestamp,
    )
    _json_record(
        numbers,
        provenance,
        key="rs2_mxfp8_hls_lut",
        value=mx_metrics["resources"]["LUT"],
        units="LUT",
        source=MXFP8_HLS,
        marker='"LUT"',
        revision=revision,
        timestamp=timestamp,
    )

    route_specs = {
        "rs2_route_physical_fit": (route["physical_fit"], "status", '"physical_fit"'),
        "rs2_route_target_timing": (route["target_clock"]["status"], "status", '"target_clock"'),
        "rs2_route_target_frequency_mhz": (route["target_clock"]["frequency_mhz"], "MHz", '"frequency_mhz"'),
        "rs2_route_target_wns_ns": (route["target_clock"]["timing"]["wns_ns"], "ns", '"wns_ns"'),
        "rs2_route_closing_period_ns": (route["first_tested_closing_point"]["period_ns"], "ns", '"first_tested_closing_point"'),
        "rs2_route_closing_frequency_mhz": (route["first_tested_closing_point"]["frequency_mhz"], "MHz", '"first_tested_closing_point"'),
        "rs2_route_lut": (route["utilization"]["clb_luts"]["used"], "CLB LUT", '"clb_luts"'),
        "rs2_route_ff": (route["utilization"]["clb_registers"]["used"], "FF", '"clb_registers"'),
        "rs2_route_bram_tiles": (route["utilization"]["block_ram_tiles"]["used"], "BRAM tiles", '"block_ram_tiles"'),
        "rs2_route_uram": (route["utilization"]["uram"]["used"], "URAM", '"uram"'),
        "rs2_route_dsp": (route["utilization"]["dsps"]["used"], "DSP", '"dsps"'),
        "rs2_route_drc_status": (route["drc"]["signoff_status"], "status", '"signoff_status"'),
        "rs2_route_drc_warnings": (route["drc"]["warning_count"], "warnings", '"warning_count"'),
        "rs2_route_power_total_w": (route["vectorless_power"]["total_on_chip_w"], "W", '"total_on_chip_w"'),
        "rs2_route_power_dynamic_w": (route["vectorless_power"]["dynamic_w"], "W", '"dynamic_w"'),
        "rs2_route_power_static_w": (route["vectorless_power"]["static_w"], "W", '"static_w"'),
        "rs2_route_power_confidence": (route["vectorless_power"]["confidence"], "category", '"confidence"'),
    }
    for key, (value, units, marker) in route_specs.items():
        _json_record(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=RS2_VIVADO,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    rtl_specs = {
        "rs2_rtl_64_token_status": (rtl["required_64_token_rtl_parity"], "status", '"required_64_token_rtl_parity"'),
        "rs2_rtl_tokens": (rtl["trace"]["tokens"], "tokens", '"tokens"'),
        "rs2_rtl_transactions": (rtl["rtl_simulation"]["completed_transactions"], "commands", '"completed_transactions"'),
        "rs2_rtl_output_values": (rtl["parity"]["output_values_compared"], "values", '"output_values_compared"'),
        "rs2_rtl_step_cycles_min": (rtl["step_latency_cycles"]["minimum"], "cycles", '"step_latency_cycles"'),
        "rs2_rtl_step_cycles_mean": (rtl["step_latency_cycles"]["mean"], "cycles", '"step_latency_cycles"'),
        "rs2_rtl_step_cycles_max": (rtl["step_latency_cycles"]["maximum"], "cycles", '"step_latency_cycles"'),
    }
    for key, (value, units, marker) in rtl_specs.items():
        _json_record(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=RS2_RTL,
            marker=marker,
            revision=revision,
            timestamp=timestamp,
        )

    for prefix, source, payload in (
        ("bf16", BF16_VIVADO, bf16_route),
        ("mxfp8", MXFP8_VIVADO, mxfp8_route),
        ("candidate", RS2_VIVADO, route),
    ):
        power = payload["vectorless_power"]
        for field, suffix in (
            ("block_ram_w", "bram"),
            ("clb_logic_w", "clb"),
            ("clocks_w", "clocks"),
            ("dsps_w", "dsp"),
            ("signals_w", "signals"),
            ("uram_w", "uram"),
        ):
            _json_record(
                numbers,
                provenance,
                key=f"rs2_{prefix}_power_{suffix}_w",
                value=power["components"][field],
                units="W",
                source=source,
                marker=f'"{field}"',
                revision=revision,
                timestamp=timestamp,
            )
        for field, suffix in (
            ("dynamic_w", "dynamic"),
            ("static_w", "static"),
            ("total_on_chip_w", "total"),
        ):
            _json_record(
                numbers,
                provenance,
                key=f"rs2_{prefix}_power_{suffix}_w",
                value=power[field],
                units="W",
                source=source,
                marker=f'"{field}"',
                revision=revision,
                timestamp=timestamp,
            )


def _add_derived_numbers(
    numbers: dict[str, dict[str, object]],
    provenance: dict[str, dict[str, object]],
    by_key: dict[tuple[str, int], dict[str, str]],
    lines: dict[tuple[str, int], int],
    revision: str,
    timestamp: str,
) -> None:
    interface = _load_json(INTERFACE)
    commands = interface["commands"]
    candidate = int(numbers["rs2_candidate_logical_state_bytes"]["value"])
    bf16 = int(numbers["rs2_bf16_logical_state_bytes"]["value"])
    mxfp8 = int(numbers["rs2_mxfp8_logical_state_bytes"]["value"])
    for key, value, units, marker in (
        ("rs2_candidate_state_percent_of_bf16", 100.0 * candidate / bf16, "percent", '"logical_state_bytes"'),
        ("rs2_candidate_state_percent_above_mxfp8", 100.0 * (candidate / mxfp8 - 1.0), "percent", '"logical_state_bytes"'),
        ("rs2_candidate_all_layer_state_mib", candidate * 36 / (1024.0 * 1024.0), "MiB", '"logical_state_bytes"'),
        ("rs2_mxfp8_all_layer_state_mib", mxfp8 * 36 / (1024.0 * 1024.0), "MiB", '"logical_state_bytes"'),
        ("rs2_transfer_bf16_load_bytes", commands["LOAD"]["bf16_input_bytes"], "bytes", '"bf16_input_bytes"'),
        ("rs2_transfer_bf16_readback_bytes", commands["READBACK"]["bf16_output_bytes"], "bytes", '"bf16_output_bytes"'),
        ("rs2_transfer_candidate_load_bytes", commands["LOAD"]["rs2_input_bytes"], "bytes", '"rs2_input_bytes"'),
        ("rs2_transfer_candidate_readback_bytes", commands["READBACK"]["rs2_output_bytes"], "bytes", '"rs2_output_bytes"'),
        ("rs2_transfer_bf16_step_input_bytes", commands["STEP"]["bf16_input_bytes"], "bytes", '"bf16_input_bytes"'),
        ("rs2_transfer_candidate_step_input_bytes", commands["STEP"]["rs2_input_bytes"], "bytes", '"rs2_input_bytes"'),
        ("rs2_transfer_bf16_step_output_bytes", commands["STEP"]["bf16_output_bytes"], "bytes", '"bf16_output_bytes"'),
        ("rs2_transfer_candidate_step_output_bytes", commands["STEP"]["rs2_output_bytes"], "bytes", '"rs2_output_bytes"'),
    ):
        _record(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=(
                REGISTRATION
                if key.startswith("rs2_candidate_state_") or "_all_layer_state_" in key
                else INTERFACE
            ),
            source_line=(
                _line(REGISTRATION, marker)
                if key.startswith("rs2_candidate_state_") or "_all_layer_state_" in key
                else _line_after(
                    INTERFACE,
                    '"LOAD"' if "load" in key else '"READBACK"' if "readback" in key else '"STEP"',
                    marker,
                )
            ),
            revision=revision,
            timestamp=timestamp,
        )
    for key, value, units, source, marker in (
        ("corrected_log_capacity", 3, "entries", REGISTRATION, '"log_capacity"'),
        ("corrected_accumulator_bits", 32, "bits", REGISTRATION, '"accumulator_bits"'),
        ("corrected_alignment_guard_bits", 5, "bits", REGISTRATION, '"alignment_guard_bits"'),
        ("corrected_logical_state_bytes", candidate, "bytes/layer", REGISTRATION, '"encoded_candidate"'),
        ("corrected_candidate_step_input_logical_bytes", commands["STEP"]["rs2_input_bytes"], "bytes", INTERFACE, '"STEP"'),
    ):
        _record(
            numbers,
            provenance,
            key=key,
            value=value,
            units=units,
            source=source,
            source_line=_line(source, marker),
            revision=revision,
            timestamp=timestamp,
        )
    final_rows = {
        slug: by_key[(variant, 8192)] for variant, slug in VARIANTS.items()
    }
    for slug, source_key in (
        ("bf16", "bf16"),
        ("mxfp8", "mxfp8_state"),
        ("candidate", "rs2"),
    ):
        _record(
            numbers,
            provenance,
            key=f"rs2_tradeoff_{slug}_state_bytes",
            value={
                "bf16": bf16,
                "mxfp8": mxfp8,
                "candidate": candidate,
            }[slug],
            units="bytes/layer",
            source=REGISTRATION,
            source_line=_line(REGISTRATION, '"logical_state_bytes"'),
            revision=revision,
            timestamp=timestamp,
        )
        variant = next(name for name, mapped in VARIANTS.items() if mapped == source_key)
        row_line = lines[(variant, 8192)]
        _record(
            numbers,
            provenance,
            key=f"rs2_tradeoff_{slug}_output_cosine",
            value=float(final_rows[source_key]["output_cosine_fp32"]),
            units="cosine",
            source=CONTROLLED,
            source_line=row_line,
            revision=revision,
            timestamp=timestamp,
        )
    for slug, key in (
        ("bf16", "rs2_bf16_hls_amortized_cycles_max"),
        ("mxfp8", "rs2_mxfp8_hls_step_cycles_max"),
        ("candidate", "rs2_hls_amortized_cycles_max"),
    ):
        source = MXFP8_HLS if slug == "mxfp8" else RS2_HLS
        _record(
            numbers,
            provenance,
            key=f"rs2_tradeoff_{slug}_hls_cycles",
            value=numbers[key]["value"],
            units="cycles/STEP",
            source=source,
            source_line=int(numbers[key]["source_line"]),
            revision=revision,
            timestamp=timestamp,
        )


def _add_timing_ablation_numbers(
    numbers: dict[str, dict[str, object]],
    provenance: dict[str, dict[str, object]],
    revision: str,
    timestamp: str,
) -> None:
    route = _load_json(RS2_VIVADO)
    target = route["target_clock"]["timing"]
    for suffix, value, units, marker in (
        ("wns_ns", target["wns_ns"], "ns", '"wns_ns"'),
        (
            "setup_failing_endpoints",
            target["setup_failing_endpoints"],
            "endpoints",
            '"setup_failing_endpoints"',
        ),
    ):
        _record(
            numbers,
            provenance,
            key=f"rs2_timing_ablation_selected_{suffix}",
            value=value,
            units=units,
            source=RS2_VIVADO,
            source_line=_line_after(RS2_VIVADO, '"target_clock"', marker),
            revision=revision,
            timestamp=timestamp,
        )

    for slug, _, path, _ in TIMING_EXPERIMENTS:
        payload = _load_json(path)
        timing = payload["postroute"]["experiment_timing"]
        for suffix, value, units, marker in (
            ("wns_ns", timing["wns_ns"], "ns", '"wns_ns"'),
            (
                "setup_failing_endpoints",
                timing["setup_failing_endpoints"],
                "endpoints",
                '"setup_failing_endpoints"',
            ),
        ):
            _record(
                numbers,
                provenance,
                key=f"rs2_timing_ablation_{slug}_{suffix}",
                value=value,
                units=units,
                source=path,
                source_line=_line_after(path, '"experiment_timing"', marker),
                revision=revision,
                timestamp=timestamp,
            )


def _write_tables(
    output: Path,
    numbers: dict[str, dict[str, object]],
) -> list[Path]:
    tables = output / "tables"
    rows = [
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r"Variant & 64 & 256 & 1{,}024 & 4{,}096 & 8{,}192 \\",
        r"\midrule",
    ]
    for slug in ("fp32", "bf16", "mxfp4_qdq", "mxfp8_state", "int4", "rs2"):
        values = []
        for token in CHECKPOINTS:
            cosine = float(numbers[f"rs2_{slug}_token_{token}_output_cosine"]["value"])
            state = float(numbers[f"rs2_{slug}_token_{token}_state_relative_l2"]["value"])
            values.append(f"{cosine:.3f}/{state:.3f}")
        rows.append(f"{DISPLAY[slug]} & " + " & ".join(values) + r" \\")
    rows.extend([r"\bottomrule", r"\end{tabular}"])
    long_table = tables / "rs2_controlled_long.tex"
    _write_table(long_table, rows)

    gates = tables / "rs2_stability_gates.tex"
    _write_table(
        gates,
        [
            r"\begin{tabular}{lrrrrr}",
            r"\toprule",
            r"Evidence set & Runs & Min. cosine & Max. state rel. $L_2$ & Max. final rel. $L_2$ & Max. abs. error \\",
            r"\midrule",
            (
                "Held-out, 1{,}024 tokens & "
                f"{_tex_int(numbers['rs2_heldout_run_count']['value'])} & "
                f"{float(numbers['rs2_heldout_min_all_token_cosine']['value']):.6f} & "
                f"{float(numbers['rs2_heldout_max_all_token_state_relative_l2']['value']):.6f} & "
                f"{float(numbers['rs2_heldout_max_final_state_relative_l2']['value']):.6f} & "
                f"{float(numbers['rs2_heldout_max_state_abs_error']['value']):.6f} " + r"\\"
            ),
            (
                "Development, 8{,}192 tokens & "
                f"{_tex_int(numbers['rs2_extended_run_count']['value'])} & "
                f"{float(numbers['rs2_extended_min_all_token_cosine']['value']):.6f} & "
                f"{float(numbers['rs2_extended_max_all_token_state_relative_l2']['value']):.6f} & "
                f"{float(numbers['rs2_extended_max_final_state_relative_l2']['value']):.6f} & "
                f"{float(numbers['rs2_extended_max_state_abs_error']['value']):.6f} " + r"\\"
            ),
            r"\bottomrule",
            r"\end{tabular}",
        ],
    )

    hls_table = tables / "rs2_hls.tex"
    _write_table(
        hls_table,
        [
            r"\begin{tabular}{lrrr}",
            r"\toprule",
            r"Metric & BF16 & Native MXFP4 RS2/R3 & Ratio \\",
            r"\midrule",
            f"Logical state bytes/layer & {_tex_int(numbers['rs2_bf16_logical_state_bytes']['value'])} & {_tex_int(numbers['rs2_candidate_logical_state_bytes']['value'])} & {float(numbers['rs2_candidate_state_percent_of_bf16']['value']) / 100.0:.3f} " + r"\\",
            f"HLS LUT & {_tex_int(numbers['rs2_bf16_hls_lut']['value'])} & {_tex_int(numbers['rs2_hls_lut']['value'])} & {float(numbers['rs2_hls_lut_ratio_to_bf16']['value']):.3f} " + r"\\",
            f"Non-fold STEP max cycles & {_tex_int(numbers['rs2_bf16_hls_step_cycles_max']['value'])} & {_tex_int(numbers['rs2_hls_nonfold_step_cycles_max']['value'])} & {float(numbers['rs2_hls_nonfold_cycle_ratio_to_bf16']['value']):.3f} " + r"\\",
            f"Amortized cycles/STEP & {_tex_int(round(float(numbers['rs2_bf16_hls_amortized_cycles_max']['value'])))} & {_tex_int(round(float(numbers['rs2_hls_amortized_cycles_max']['value'])))} & {float(numbers['rs2_hls_amortized_cycle_ratio_to_bf16']['value']):.3f} " + r"\\",
            f"Estimated Fmax (MHz) & {float(numbers['rs2_bf16_hls_estimated_fmax_mhz']['value']):.2f} & {float(numbers['rs2_hls_estimated_fmax_mhz']['value']):.2f} & -- " + r"\\",
            f"Explicit II=1 loops & PASS & {_tex_value(numbers['rs2_hls_explicit_ii1_status']['value'])} & -- " + r"\\",
            r"\bottomrule",
            r"\end{tabular}",
        ],
    )

    postroute = tables / "rs2_postroute.tex"
    _write_table(
        postroute,
        [
            r"\begin{tabular}{lrrr}",
            r"\toprule",
            r"Metric & BF16 & Native MXFP8 & MXFP4 RS2/R3 \\",
            r"\midrule",
            f"Physical fit & {_tex_value(numbers['bf16_physical_fit_status']['value'])} & {_tex_value(numbers['mxfp8_postroute_physical_fit']['value'])} & {_tex_value(numbers['rs2_route_physical_fit']['value'])} " + r"\\",
            f"First tested closing MHz & {float(numbers['bf16_first_tested_closing_frequency_mhz']['value']):.2f} & {float(numbers['mxfp8_postroute_first_closing_frequency_mhz']['value']):.2f} & {float(numbers['rs2_route_closing_frequency_mhz']['value']):.2f} " + r"\\",
            f"CLB LUT & {_tex_int(numbers['bf16_routed_clb_lut']['value'])} & {_tex_int(numbers['mxfp8_postroute_lut_used']['value'])} & {_tex_int(numbers['rs2_route_lut']['value'])} " + r"\\",
            f"FF & {_tex_int(numbers['bf16_routed_ff']['value'])} & {_tex_int(numbers['mxfp8_postroute_ff_used']['value'])} & {_tex_int(numbers['rs2_route_ff']['value'])} " + r"\\",
            f"BRAM tiles & {float(numbers['bf16_routed_bram_tiles']['value']):.1f} & {float(numbers['mxfp8_postroute_bram_tiles_used']['value']):.1f} & {float(numbers['rs2_route_bram_tiles']['value']):.1f} " + r"\\",
            f"URAM & {_tex_int(numbers['bf16_routed_uram']['value'])} & {_tex_int(numbers['mxfp8_postroute_uram_used']['value'])} & {_tex_int(numbers['rs2_route_uram']['value'])} " + r"\\",
            f"DSP & {_tex_int(numbers['bf16_routed_dsp']['value'])} & {_tex_int(numbers['mxfp8_postroute_dsp_used']['value'])} & {_tex_int(numbers['rs2_route_dsp']['value'])} " + r"\\",
            f"Vectorless total power (W) & {float(numbers['rs2_bf16_power_total_w']['value']):.3f} & {float(numbers['rs2_mxfp8_power_total_w']['value']):.3f} & {float(numbers['rs2_candidate_power_total_w']['value']):.3f} " + r"\\",
            r"\bottomrule",
            r"\end{tabular}",
        ],
    )

    power = tables / "rs2_power_breakdown.tex"
    power_lines = [
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Component (W) & BF16 & Native MXFP8 & MXFP4 RS2/R3 \\",
        r"\midrule",
    ]
    for label, suffix in (
        ("CLB logic", "clb"),
        ("Signals", "signals"),
        ("Clocks", "clocks"),
        ("BRAM", "bram"),
        ("URAM", "uram"),
        ("DSP", "dsp"),
        ("Dynamic total", "dynamic"),
        ("Static", "static"),
        ("On-chip total", "total"),
    ):
        power_lines.append(
            f"{label} & {float(numbers[f'rs2_bf16_power_{suffix}_w']['value']):.3f} & "
            f"{float(numbers[f'rs2_mxfp8_power_{suffix}_w']['value']):.3f} & "
            f"{float(numbers[f'rs2_candidate_power_{suffix}_w']['value']):.3f} " + r"\\"
        )
    power_lines.extend([r"\bottomrule", r"\end{tabular}"])
    _write_table(power, power_lines)

    timing_ablation = tables / "rs2_timing_ablation.tex"
    timing_lines = [
        r"\begin{tabular}{lrrl}",
        r"\toprule",
        r"Design change & WNS (ns) & Failing endpoints & Outcome \\",
        r"\midrule",
        (
            "Selected RS2/R3 & "
            f"{float(numbers['rs2_timing_ablation_selected_wns_ns']['value']):.3f} & "
            f"{_tex_int(numbers['rs2_timing_ablation_selected_setup_failing_endpoints']['value'])} & Reference "
            + r"\\"
        ),
        "URAM output latency & -- & -- & HLS-only; path mismatch " + r"\\",
    ]
    for slug, label, _, outcome in TIMING_EXPERIMENTS:
        timing_lines.append(
            f"{label} & "
            f"{float(numbers[f'rs2_timing_ablation_{slug}_wns_ns']['value']):.3f} & "
            f"{_tex_int(numbers[f'rs2_timing_ablation_{slug}_setup_failing_endpoints']['value'])} & "
            f"{outcome} " + r"\\"
        )
    timing_lines.extend([r"\bottomrule", r"\end{tabular}"])
    _write_table(timing_ablation, timing_lines)

    transfers = tables / "rs2_transfer_sizes.tex"
    _write_table(
        transfers,
        [
            r"\begin{tabular}{lrr}",
            r"\toprule",
            r"Logical payload & BF16 & Native MXFP4 RS2/R3 \\",
            r"\midrule",
            f"LOAD/READBACK state (bytes/layer) & {_tex_int(numbers['rs2_transfer_bf16_load_bytes']['value'])} & {_tex_int(numbers['rs2_transfer_candidate_load_bytes']['value'])} " + r"\\",
            f"STEP input (bytes) & {_tex_int(numbers['rs2_transfer_bf16_step_input_bytes']['value'])} & {_tex_int(numbers['rs2_transfer_candidate_step_input_bytes']['value'])} " + r"\\",
            f"STEP output (bytes) & {_tex_int(numbers['rs2_transfer_bf16_step_output_bytes']['value'])} & {_tex_int(numbers['rs2_transfer_candidate_step_output_bytes']['value'])} " + r"\\",
            r"\bottomrule",
            r"\end{tabular}",
        ],
    )
    return [
        long_table,
        gates,
        hls_table,
        postroute,
        power,
        transfers,
        timing_ablation,
    ]


def _append_macros(output: Path, numbers: dict[str, dict[str, object]]) -> Path:
    path = output / "snippets" / "corrected_result_macros.tex"
    retained = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.startswith(r"\newcommand{\RsTwo")
    ]
    macros = {
        "RsTwoLongTokens": _tex_int(8192),
        "RsTwoCheckpointSet": r"64, 256, 1{,}024, 4{,}096, and 8{,}192",
        "RsTwoBfSixteenCosineEightK": f"{float(numbers['rs2_bf16_token_8192_output_cosine']['value']):.6f}",
        "RsTwoBfSixteenStateLTwoEightK": f"{float(numbers['rs2_bf16_token_8192_state_relative_l2']['value']):.6f}",
        "RsTwoQdqCosineEightK": f"{float(numbers['rs2_mxfp4_qdq_token_8192_output_cosine']['value']):.6f}",
        "RsTwoQdqStateLTwoEightK": f"{float(numbers['rs2_mxfp4_qdq_token_8192_state_relative_l2']['value']):.6f}",
        "RsTwoMxfpEightCosineEightK": f"{float(numbers['rs2_mxfp8_state_token_8192_output_cosine']['value']):.6f}",
        "RsTwoMxfpEightStateLTwoEightK": f"{float(numbers['rs2_mxfp8_state_token_8192_state_relative_l2']['value']):.6f}",
        "RsTwoIntFourCosineEightK": f"{float(numbers['rs2_int4_token_8192_output_cosine']['value']):.6f}",
        "RsTwoIntFourStateLTwoEightK": f"{float(numbers['rs2_int4_token_8192_state_relative_l2']['value']):.6f}",
        "RsTwoCandidateCosineEightK": f"{float(numbers['rs2_rs2_token_8192_output_cosine']['value']):.6f}",
        "RsTwoCandidateStateLTwoEightK": f"{float(numbers['rs2_rs2_token_8192_state_relative_l2']['value']):.6f}",
        "RsTwoCandidateStateMaxAbsEightK": f"{float(numbers['rs2_rs2_token_8192_state_max_abs']['value']):.6f}",
        "RsTwoHeldoutRuns": _tex_int(numbers["rs2_heldout_run_count"]["value"]),
        "RsTwoHeldoutMinCosine": f"{float(numbers['rs2_heldout_min_all_token_cosine']['value']):.6f}",
        "RsTwoHeldoutMaxStateLTwo": f"{float(numbers['rs2_heldout_max_all_token_state_relative_l2']['value']):.6f}",
        "RsTwoExtendedRuns": _tex_int(numbers["rs2_extended_run_count"]["value"]),
        "RsTwoExtendedMinCosine": f"{float(numbers['rs2_extended_min_all_token_cosine']['value']):.6f}",
        "RsTwoExtendedMaxStateLTwo": f"{float(numbers['rs2_extended_max_all_token_state_relative_l2']['value']):.6f}",
        "RsTwoExtendedElementSaturations": _tex_int(numbers["rs2_extended_element_saturations"]["value"]),
        "RsTwoExtendedAccumulatorSaturations": _tex_int(numbers["rs2_extended_accumulator_saturations"]["value"]),
        "RsTwoExtendedScaleClamps": _tex_int(numbers["rs2_extended_scale_clamps"]["value"]),
        "RsTwoLogicalStateBytes": _tex_int(numbers["rs2_candidate_logical_state_bytes"]["value"]),
        "RsTwoStatePercentOfBfSixteen": f"{float(numbers['rs2_candidate_state_percent_of_bf16']['value']):.2f}",
        "RsTwoStatePercentAboveMxfpEight": f"{float(numbers['rs2_candidate_state_percent_above_mxfp8']['value']):.2f}",
        "RsTwoAllLayerStateMiB": f"{float(numbers['rs2_candidate_all_layer_state_mib']['value']):.2f}",
        "RsTwoMxfpEightAllLayerStateMiB": f"{float(numbers['rs2_mxfp8_all_layer_state_mib']['value']):.2f}",
        "RsTwoHlsLut": _tex_int(numbers["rs2_hls_lut"]["value"]),
        "RsTwoHlsDsp": _tex_int(numbers["rs2_hls_dsp"]["value"]),
        "RsTwoHlsFmax": f"{float(numbers['rs2_hls_estimated_fmax_mhz']['value']):.2f}",
        "RsTwoHlsNonfoldCycles": _tex_int(numbers["rs2_hls_nonfold_step_cycles_max"]["value"]),
        "RsTwoHlsFoldCycles": _tex_int(numbers["rs2_hls_fold_cycles_max"]["value"]),
        "RsTwoHlsAmortizedCycles": _tex_int(round(float(numbers["rs2_hls_amortized_cycles_max"]["value"]))),
        "RsTwoHlsLutRatio": f"{float(numbers['rs2_hls_lut_ratio_to_bf16']['value']):.3f}",
        "RsTwoHlsNonfoldRatio": f"{float(numbers['rs2_hls_nonfold_cycle_ratio_to_bf16']['value']):.3f}",
        "RsTwoHlsAmortizedRatio": f"{float(numbers['rs2_hls_amortized_cycle_ratio_to_bf16']['value']):.3f}",
        "RsTwoHlsIiStatus": _tex_value(numbers["rs2_hls_explicit_ii1_status"]["value"]),
        "RsTwoRouteLut": _tex_int(numbers["rs2_route_lut"]["value"]),
        "RsTwoRouteFf": _tex_int(numbers["rs2_route_ff"]["value"]),
        "RsTwoRouteBram": _tex_value(numbers["rs2_route_bram_tiles"]["value"], 1),
        "RsTwoRouteUram": _tex_int(numbers["rs2_route_uram"]["value"]),
        "RsTwoRouteDsp": _tex_int(numbers["rs2_route_dsp"]["value"]),
        "RsTwoRouteTargetWns": f"{float(numbers['rs2_route_target_wns_ns']['value']):.3f}",
        "RsTwoRouteTargetMhz": f"{float(numbers['rs2_route_target_frequency_mhz']['value']):.0f}",
        "RsTwoRouteClosingPeriodNs": f"{float(numbers['rs2_route_closing_period_ns']['value']):.1f}",
        "RsTwoRouteClosingMhz": f"{float(numbers['rs2_route_closing_frequency_mhz']['value']):.2f}",
        "RsTwoRoutePowerW": f"{float(numbers['rs2_route_power_total_w']['value']):.3f}",
        "RsTwoRouteDynamicW": f"{float(numbers['rs2_route_power_dynamic_w']['value']):.3f}",
        "RsTwoRouteStaticW": f"{float(numbers['rs2_route_power_static_w']['value']):.3f}",
        "RsTwoRtlStatus": _tex_value(numbers["rs2_rtl_64_token_status"]["value"]),
        "RsTwoRtlTokens": _tex_int(numbers["rs2_rtl_tokens"]["value"]),
        "RsTwoRtlTransactions": _tex_int(numbers["rs2_rtl_transactions"]["value"]),
        "RsTwoRtlOutputs": _tex_int(numbers["rs2_rtl_output_values"]["value"]),
        "RsTwoRtlStepMean": _tex_int(round(float(numbers["rs2_rtl_step_cycles_mean"]["value"]))),
    }
    retained.extend(
        f"\\newcommand{{\\{name}}}{{{value}}}" for name, value in macros.items()
    )
    path.write_text("\n".join(retained) + "\n", encoding="utf-8")
    return path


def generate(output: Path) -> dict[str, object]:
    required = (
        CONTROLLED,
        CONTROLLED_MANIFEST,
        CANDIDATE,
        REGISTRATION,
        RS2_HLS,
        MXFP8_HLS,
        RS2_VIVADO,
        BF16_VIVADO,
        MXFP8_VIVADO,
        RS2_RTL,
        QWEN,
        SCALE_POLICY,
        INTERFACE,
        URAM_LATENCY_EXPERIMENT,
        *(path for _, _, path, _ in TIMING_EXPERIMENTS),
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    controlled_manifest = _load_json(CONTROLLED_MANIFEST)
    relative_controlled = _relative(CONTROLLED)
    controlled_hash = controlled_manifest.get("outputs", {}).get(relative_controlled)
    if isinstance(controlled_hash, dict):
        controlled_hash = controlled_hash.get("sha256")
    if str(controlled_hash).upper() != _sha256(CONTROLLED):
        raise ValueError("controlled checkpoint CSV is not bound by its manifest")
    candidate = _load_json(CANDIDATE)
    registration = _load_json(REGISTRATION, required_status="")
    if registration.get("registration_status") != "PASS":
        raise ValueError("selected RS2 candidate registration is not PASS")
    hls = _load_json(RS2_HLS)
    mxfp8_hls = _load_json(MXFP8_HLS)
    route = _load_json(RS2_VIVADO)
    bf16_route = _load_json(BF16_VIVADO)
    mxfp8_route = _load_json(MXFP8_VIVADO)
    rtl = _load_json(RS2_RTL)
    _load_json(QWEN)
    _load_json(SCALE_POLICY)

    legacy_manifest = corrected_paper_assets.generate(output)
    numbers_path = output / "numbers.json"
    provenance_path = output / "provenance.json"
    numbers = json.loads(numbers_path.read_text(encoding="utf-8"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    revision = _git_revision()
    timestamp = datetime.now(timezone.utc).isoformat()
    rows, line_by_key = _controlled_rows()
    by_key = _add_controlled_numbers(
        numbers, provenance, rows, line_by_key, revision, timestamp
    )
    _add_candidate_numbers(
        numbers, provenance, candidate, registration, revision, timestamp
    )
    _add_hardware_numbers(
        numbers,
        provenance,
        hls,
        mxfp8_hls,
        route,
        rtl,
        bf16_route,
        mxfp8_route,
        revision,
        timestamp,
    )
    _add_derived_numbers(
        numbers, provenance, by_key, line_by_key, revision, timestamp
    )
    _add_timing_ablation_numbers(numbers, provenance, revision, timestamp)
    if set(numbers) != set(provenance):
        raise ValueError("paper numbers and provenance keys diverged")
    numbers_path.write_text(
        json.dumps(numbers, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    generated_tables = _write_tables(output, numbers)
    macro_path = _append_macros(output, numbers)

    figure_manifest_path = (
        ROOT / "paper" / "figures" / "corrected" / "rs2_paper_figures_manifest.json"
    )
    figure_manifest = generate_figures(
        numbers_path,
        ROOT / "paper" / "figures" / "corrected",
        figure_manifest_path,
    )
    datapath_manifest_path = corrected_datapath_figure.DEFAULT_MANIFEST
    datapath_manifest = corrected_datapath_figure.generate(
        numbers_path,
        corrected_datapath_figure.DEFAULT_OUTPUT,
        datapath_manifest_path,
    )

    asset_path = output / "asset_manifest.json"
    asset = json.loads(asset_path.read_text(encoding="utf-8"))
    asset.update(
        {
            "status": "PASS",
            "scope": "selected RS2/R3 manuscript assets generated from verified evidence",
            "generated_at": timestamp,
            "source_revision": revision,
            "source_identity": describe_source_files(
                [
                    Path(__file__).resolve(),
                    ROOT / "scripts" / "rs2_paper_figures.py",
                    ROOT / "scripts" / "corrected_paper_assets.py",
                    output / "paper.tex",
                ]
            ),
            "selected_candidate": candidate["candidate_name"],
            "held_out_status": candidate["gate_results"]["held_out"]["status"],
            "extended_8192_status": candidate["gate_results"]["extended_development"]["status"],
            "rtl_64_token_status": rtl["required_64_token_rtl_parity"],
            "post_route_status": route["status"],
            "hls_cost_latency_advantage_vs_bf16": hls["comparison"]["hls_cost_latency_advantage_vs_bf16"],
        }
    )
    asset.setdefault("inputs_sha256", {}).update(
        {_relative(path): _sha256(path) for path in required}
    )
    # The legacy generator records this shared manifest as an input. The RS2
    # overlay regenerates it, so replace that earlier hash with the final bytes.
    asset["inputs_sha256"][_relative(datapath_manifest_path)] = _sha256(
        datapath_manifest_path
    )
    generated = [numbers_path, provenance_path, macro_path, *generated_tables]
    asset.setdefault("outputs_sha256", {}).update(
        {_relative(path): _sha256(path) for path in generated}
    )
    asset.setdefault("verified_figure_sha256", {}).update(figure_manifest["outputs"])
    asset["verified_figure_sha256"][_relative(figure_manifest_path)] = _sha256(
        figure_manifest_path
    )
    asset["verified_figure_sha256"].update(datapath_manifest["outputs"])
    asset["verified_figure_sha256"][_relative(datapath_manifest_path)] = _sha256(
        datapath_manifest_path
    )
    asset["legacy_asset_manifest_status"] = legacy_manifest["status"]
    asset["limitations"] = [
        "long-horizon quality is layer-level synthetic evidence",
        "short model-derived recurrence is not closed-loop model quality",
        "Vivado power is vectorless and is not board energy",
        "the current RS2/R3 mitigation has no HLS cost/latency advantage over BF16",
    ]
    asset_path.write_text(
        json.dumps(asset, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return asset


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = generate(_resolve(args.output))
    print(
        json.dumps(
            {
                "status": result["status"],
                "held_out": result["held_out_status"],
                "extended": result["extended_8192_status"],
                "rtl": result["rtl_64_token_status"],
                "post_route": result["post_route_status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

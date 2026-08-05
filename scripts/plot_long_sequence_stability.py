"""Generate vector-PDF long-sequence stability plots from corrected CSV data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from scripts.evidence_source_snapshot import describe_source_files
from scripts.reportlab_fonts import FONT_SOURCE, register_embedded_sans


register_embedded_sans()


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports" / "benchmark" / "corrected" / "long_trace_tokens.csv"
DEFAULT_EVIDENCE_MANIFEST = (
    ROOT / "reports" / "benchmark" / "corrected" / "long_trace_manifest.json"
)
DEFAULT_ENCODED_INPUT = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "native_encoded_long_trace_tokens.csv"
)
DEFAULT_ENCODED_EVIDENCE_MANIFEST = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "native_encoded_long_trace_manifest.json"
)
DEFAULT_OUTPUT_COSINE = ROOT / "paper" / "figures" / "corrected" / "output_cosine_vs_token.pdf"
DEFAULT_STATE_ERROR = ROOT / "paper" / "figures" / "corrected" / "state_relative_l2_vs_token.pdf"
DEFAULT_MANIFEST = ROOT / "paper" / "figures" / "corrected" / "long_trace_plot_manifest.json"

PAGE_WIDTH = 7.16 * 72.0
PAGE_HEIGHT = 4.35 * 72.0
LEFT = 62.0
RIGHT = 18.0
BOTTOM = 52.0
TOP = 68.0

COLORS = (
    (0.08, 0.08, 0.08),
    (0.00, 0.45, 0.48),
    (0.88, 0.48, 0.05),
    (0.20, 0.38, 0.70),
    (0.55, 0.32, 0.62),
    (0.78, 0.20, 0.18),
)
VARIANT_ORDER = (
    "fp32",
    "bf16_qdq_fp32_accum_state_bf16",
    "native_mxfp4_encoded_act_b32_state_b32",
    "mxfp4_qdq_act_b32_state_b32",
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32",
    "flat_int4_qdq",
)
VARIANT_COLORS = {
    "fp32": COLORS[0],
    "bf16_qdq_fp32_accum_state_bf16": COLORS[1],
    "mxfp4_qdq_act_b32_state_b32": COLORS[2],
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32": COLORS[3],
    "flat_int4_qdq": COLORS[4],
    "native_mxfp4_encoded_act_b32_state_b32": COLORS[5],
}
VARIANT_DASHES = {
    "fp32": (),
    "bf16_qdq_fp32_accum_state_bf16": (7, 2),
    "mxfp4_qdq_act_b32_state_b32": (2, 2),
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32": (5, 2),
    "flat_int4_qdq": (1, 2),
    "native_mxfp4_encoded_act_b32_state_b32": (9, 2),
}


def _variant_color(variant: str, fallback_index: int) -> tuple[float, float, float]:
    return VARIANT_COLORS.get(variant, COLORS[fallback_index % len(COLORS)])


def _variant_dash(variant: str) -> tuple[int, ...]:
    return VARIANT_DASHES.get(variant, ())


def _set_dash(pdf: canvas.Canvas, variant: str) -> None:
    dash = _variant_dash(variant)
    if dash:
        pdf.setDash(list(dash))
    else:
        pdf.setDash()


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("input CSV contains no rows")
    required = {"variant", "token_index", "output_cosine_fp32", "state_rel_l2"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"input CSV is missing columns: {sorted(missing)}")
    return rows


def _group_series(
    rows: list[dict[str, str]],
    metric: str,
    *,
    include_fp32: bool,
) -> dict[str, list[tuple[int, float]]]:
    grouped: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        variant = row["variant"]
        if variant == "fp32" and not include_fp32:
            continue
        grouped[variant].append((int(row["token_index"]), float(row[metric])))
    for values in grouped.values():
        values.sort(key=lambda item: item[0])
    order = {name: index for index, name in enumerate(VARIANT_ORDER)}
    return dict(
        sorted(
            grouped.items(),
            key=lambda item: (order.get(item[0], len(order)), item[0]),
        )
    )


def _display_name(name: str) -> str:
    replacements = {
        "fp32": "FP32 reference",
        "bf16_qdq_fp32_accum_state_bf16": "BF16 operands/state (FP32 accum)",
        "flat_int4_qdq": "Flat INT4 Q/DQ",
        "native_mxfp4_encoded_act_b32_state_b32": "Native encoded MXFP4",
    }
    if name in replacements:
        return replacements[name]
    if name.startswith("mxfp4_qdq_act_b"):
        fields = name.split("_")
        activation_block = fields[3].upper()
        state_block = fields[-1].upper()
        if "mxfp8" in fields:
            return (
                "MXFP4 Q/DQ + MXFP8-E4M3 state "
                f"(act {activation_block}, state {state_block})"
            )
        return f"MXFP4 floating Q/DQ (act {activation_block}, state {state_block})"
    return name.replace("_", " ")


def _nice_linear_ticks(low: float, high: float, count: int = 5) -> list[float]:
    if high <= low:
        return [low]
    raw_step = (high - low) / max(count - 1, 1)
    exponent = math.floor(math.log10(raw_step))
    fraction = raw_step / (10.0**exponent)
    if fraction <= 1.0:
        nice_fraction = 1.0
    elif fraction <= 2.0:
        nice_fraction = 2.0
    elif fraction <= 5.0:
        nice_fraction = 5.0
    else:
        nice_fraction = 10.0
    step = nice_fraction * (10.0**exponent)
    start = math.floor(low / step) * step
    values = []
    value = start
    while value <= high + step * 0.5:
        if value >= low - step * 0.5:
            values.append(value)
        value += step
    return values


def _draw_plot(
    path: Path,
    *,
    series: dict[str, list[tuple[int, float]]],
    title: str,
    y_label: str,
    log_y: bool,
    footer_lines: tuple[str, ...],
    decision_line: tuple[float, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), invariant=1)
    pdf.setTitle(title)
    pdf.setAuthor("FPT26_data_review evidence pipeline")

    plot_width = PAGE_WIDTH - LEFT - RIGHT
    plot_height = PAGE_HEIGHT - BOTTOM - TOP
    all_points = [point for points in series.values() for point in points]
    max_token = max(token for token, _ in all_points)
    min_token = max(1, min(token for token, _ in all_points))
    x_low = math.log10(min_token)
    x_high = math.log10(max_token) if max_token > min_token else x_low + 1.0

    all_values = [value for _, value in all_points]
    if log_y:
        positive = [value for value in all_values if value > 0.0]
        if not positive:
            raise ValueError("logarithmic plot requires positive values")
        y_low_raw = max(min(positive), 1e-8)
        y_high_raw = max(positive)
        y_low = math.floor(math.log10(y_low_raw))
        y_high = math.ceil(math.log10(y_high_raw))
        if y_high <= y_low:
            y_high = y_low + 1.0
        y_ticks = [10.0**exponent for exponent in range(int(y_low), int(y_high) + 1)]
    else:
        y_low_raw = min(all_values)
        y_high_raw = max(all_values)
        padding = max((y_high_raw - y_low_raw) * 0.08, 0.002)
        y_low = max(-1.0, y_low_raw - padding)
        y_high = min(1.0, y_high_raw + padding)
        if y_high <= y_low:
            y_high = y_low + 0.01
        y_ticks = _nice_linear_ticks(y_low, y_high)

    def x_position(token: int) -> float:
        return LEFT + (math.log10(max(token, 1)) - x_low) / (x_high - x_low) * plot_width

    def y_position(value: float) -> float:
        transformed = math.log10(max(value, 1e-8)) if log_y else value
        return BOTTOM + (transformed - y_low) / (y_high - y_low) * plot_height

    pdf.setFillColorRGB(1.0, 1.0, 1.0)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColorRGB(0.08, 0.08, 0.08)
    pdf.drawString(LEFT, PAGE_HEIGHT - 19, title)

    pdf.setStrokeColorRGB(0.85, 0.86, 0.87)
    pdf.setLineWidth(0.45)
    for tick in y_ticks:
        y = y_position(tick)
        if BOTTOM - 0.1 <= y <= BOTTOM + plot_height + 0.1:
            pdf.line(LEFT, y, LEFT + plot_width, y)
            pdf.setFillColorRGB(0.25, 0.25, 0.25)
            pdf.setFont("Helvetica", 7.5)
            label = f"{tick:.0e}" if log_y else f"{tick:.3f}"
            pdf.drawRightString(LEFT - 6, y - 2.5, label)

    powers = range(int(math.floor(x_low)), int(math.ceil(x_high)) + 1)
    x_ticks = sorted(
        {
            value
            for power in powers
            for value in (1 * 10**power, 2 * 10**power, 5 * 10**power)
            if min_token <= value <= max_token
        }
    )
    for tick in x_ticks:
        x = x_position(tick)
        pdf.setStrokeColorRGB(0.91, 0.92, 0.93)
        pdf.line(x, BOTTOM, x, BOTTOM + plot_height)
        pdf.setFillColorRGB(0.25, 0.25, 0.25)
        pdf.setFont("Helvetica", 7.5)
        pdf.drawCentredString(x, BOTTOM - 12, str(tick))

    pdf.setStrokeColorRGB(0.12, 0.12, 0.12)
    pdf.setLineWidth(0.8)
    pdf.rect(LEFT, BOTTOM, plot_width, plot_height, fill=0, stroke=1)

    decision_label: tuple[str, float] | None = None
    if decision_line is not None:
        threshold, label = decision_line
        threshold_y = y_position(threshold)
        if BOTTOM <= threshold_y <= BOTTOM + plot_height:
            pdf.setStrokeColorRGB(0.35, 0.35, 0.35)
            pdf.setFillColorRGB(0.25, 0.25, 0.25)
            pdf.setLineWidth(0.7)
            pdf.setDash(3, 2)
            pdf.line(LEFT, threshold_y, LEFT + plot_width, threshold_y)
            pdf.setDash()
            label_y = min(threshold_y + 3, BOTTOM + plot_height - 8)
            decision_label = (label, label_y)

    for index, (variant, points) in enumerate(series.items()):
        color = _variant_color(variant, index)
        pdf.setStrokeColorRGB(*color)
        pdf.setFillColorRGB(*color)
        pdf.setLineWidth(1.45)
        _set_dash(pdf, variant)
        first = True
        path_object = pdf.beginPath()
        for token, value in points:
            if log_y and value <= 0.0:
                continue
            x = x_position(token)
            y = y_position(value)
            if first:
                path_object.moveTo(x, y)
                first = False
            else:
                path_object.lineTo(x, y)
        if not first:
            pdf.drawPath(path_object, stroke=1, fill=0)
        pdf.setDash()

    if decision_label is not None:
        label, label_y = decision_label
        pdf.setFont("Helvetica", 6.5)
        label_width = stringWidth(label, "Helvetica", 6.5)
        label_right = LEFT + plot_width - 3
        pdf.setFillColorRGB(1.0, 1.0, 1.0)
        pdf.rect(label_right - label_width - 3, label_y - 2, label_width + 6, 8, fill=1, stroke=0)
        pdf.setFillColorRGB(0.25, 0.25, 0.25)
        pdf.drawRightString(label_right, label_y, label)

    pdf.setFillColorRGB(0.12, 0.12, 0.12)
    pdf.setFont("Helvetica", 8.5)
    pdf.drawCentredString(LEFT + plot_width / 2, 17, "Decode token index (log scale)")
    pdf.saveState()
    pdf.translate(14, BOTTOM + plot_height / 2)
    pdf.rotate(90)
    pdf.drawCentredString(0, 0, y_label)
    pdf.restoreState()

    legend_y = PAGE_HEIGHT - 38
    legend_x = LEFT
    pdf.setFont("Helvetica", 7.2)
    for index, variant in enumerate(series):
        label = _display_name(variant)
        width = stringWidth(label, "Helvetica", 7.2)
        item_width = width + 30
        if legend_x + item_width > PAGE_WIDTH - RIGHT:
            legend_x = LEFT
            legend_y -= 12
        color = _variant_color(variant, index)
        pdf.setStrokeColorRGB(*color)
        pdf.setLineWidth(1.5)
        _set_dash(pdf, variant)
        pdf.line(legend_x, legend_y + 2, legend_x + 13, legend_y + 2)
        pdf.setDash()
        pdf.setFillColorRGB(0.12, 0.12, 0.12)
        pdf.drawString(legend_x + 16, legend_y - 0.5, label)
        legend_x += item_width

    pdf.setFillColorRGB(0.35, 0.35, 0.35)
    pdf.setFont("Helvetica", 5.8)
    for index, footer in enumerate(footer_lines):
        pdf.drawRightString(PAGE_WIDTH - RIGHT, 9.0 - 6.0 * index, footer)
    pdf.showPage()
    pdf.save()


def generate_plots(
    input_csv: Path,
    output_cosine: Path,
    state_error: Path,
    manifest_path: Path,
    evidence_manifest_path: Path | None = None,
    encoded_input_csv: Path | None = None,
    encoded_evidence_manifest_path: Path | None = None,
) -> None:
    rows = _read_rows(input_csv)
    metadata = rows[0]
    encoded_rows: list[dict[str, str]] = []
    upstream_manifest = None
    encoded_manifest = None
    configuration: dict[str, object] = {
        "tokens": max(int(row["token_index"]) for row in rows),
        "split": metadata["split"],
        "seed": int(metadata["seed"]),
        "trace_family": metadata["trace_family"],
        "state_orientation": "KxV",
        "uncertainty": "single deterministic trace; no interval",
    }
    if evidence_manifest_path is not None:
        upstream_manifest = json.loads(
            evidence_manifest_path.read_text(encoding="utf-8")
        )
        if upstream_manifest.get("status") != "PASS":
            raise ValueError("long-trace evidence manifest status is not PASS")
        relative_input = input_csv.relative_to(ROOT).as_posix()
        input_hash = hashlib.sha256(input_csv.read_bytes()).hexdigest()
        if upstream_manifest["outputs"].get(relative_input, "").lower() != input_hash:
            raise ValueError("long-trace CSV does not match its evidence manifest")
        upstream_config = upstream_manifest["configuration"]
        configuration.update(upstream_config)
        configuration["state_orientation"] = "KxV"
        configuration["uncertainty"] = "single deterministic trace; no interval"

    if (encoded_input_csv is None) != (encoded_evidence_manifest_path is None):
        raise ValueError("encoded CSV and evidence manifest must be provided together")
    if encoded_input_csv is not None and encoded_evidence_manifest_path is not None:
        encoded_rows = _read_rows(encoded_input_csv)
        encoded_manifest = json.loads(
            encoded_evidence_manifest_path.read_text(encoding="utf-8")
        )
        if encoded_manifest.get("status") != "PASS":
            raise ValueError("native encoded evidence manifest status is not PASS")
        relative_encoded = encoded_input_csv.relative_to(ROOT).as_posix()
        encoded_meta = encoded_manifest["outputs"].get(relative_encoded)
        if not isinstance(encoded_meta, dict):
            raise ValueError("native encoded CSV metadata is absent")
        encoded_hash = hashlib.sha256(encoded_input_csv.read_bytes()).hexdigest()
        if encoded_meta.get("sha256", "").lower() != encoded_hash:
            raise ValueError("native encoded CSV does not match its evidence manifest")
        encoded_configuration = encoded_manifest["configuration"]
        for field in (
            "tokens",
            "split",
            "seed",
            "trace_family",
            "num_value_heads",
            "num_qk_heads",
            "key_dim",
            "value_dim",
            "activation_block_size",
            "state_block_size",
        ):
            if str(encoded_configuration[field]) != str(configuration[field]):
                raise ValueError(f"native and floating plot input mismatch: {field}")
        if upstream_manifest is not None and (
            encoded_manifest["input_stream_sha256"].lower()
            != upstream_manifest["input_sha256"].lower()
        ):
            raise ValueError("native and floating plot inputs do not share a trace")
        rows.extend(encoded_rows)

    variants = sorted({row["variant"] for row in rows})
    configuration["variants"] = variants

    shape = "recurrence core; KxV state"
    if upstream_manifest is not None:
        shape += (
            f"; {configuration['num_qk_heads']} Q/K + "
            f"{configuration['num_value_heads']} value heads; "
            f"K={configuration['key_dim']}, V={configuration['value_dim']}; "
            f"act/state B{configuration['activation_block_size']}/"
            f"B{configuration['state_block_size']}"
        )
    arithmetic_scope = (
        "Floating Q/DQ baselines plus native encoded MXFP4"
        if encoded_rows
        else "Floating Q/DQ only"
    )
    footer_lines = (
        (
            f"Synthetic {metadata['split']} {metadata['trace_family']}; "
            f"seed={metadata['seed']}; {shape}"
        ),
        (
            "Single deterministic trace (no uncertainty interval); relative L2 "
            f"denominator=max(||reference||2, 1e-12); {arithmetic_scope}"
        ),
    )
    _draw_plot(
        output_cosine,
        series=_group_series(rows, "output_cosine_fp32", include_fp32=True),
        title="Output cosine similarity over decode tokens",
        y_label="Cosine similarity versus FP32",
        log_y=False,
        footer_lines=footer_lines,
        decision_line=(0.99, "Synthetic engineering threshold: 0.99"),
    )
    _draw_plot(
        state_error,
        series=_group_series(rows, "state_rel_l2", include_fp32=False),
        title="Recurrent-state relative L2 error",
        y_label="State relative L2 error (log scale)",
        log_y=True,
        footer_lines=footer_lines,
        decision_line=(0.10, "Synthetic token-8192 threshold: 0.10"),
    )

    source_identity = describe_source_files([Path(__file__).resolve(), FONT_SOURCE])
    manifest = {
        "schema": 1,
        "status": "PASS",
        "evidence_scope": (
            "synthetic_floating_qdq_and_native_encoded_figures"
            if encoded_rows
            else "synthetic_floating_qdq_figures"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "execution": {
            "command": "python -m scripts.plot_long_sequence_stability",
            "exit_code": 0,
            "raw_log": manifest_path.relative_to(ROOT).as_posix(),
        },
        "input": {
            "path": input_csv.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(input_csv.read_bytes()).hexdigest(),
        },
        "encoded_input": (
            {
                "path": encoded_input_csv.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(encoded_input_csv.read_bytes()).hexdigest(),
            }
            if encoded_input_csv is not None
            else None
        ),
        "upstream_manifest": (
            {
                "path": evidence_manifest_path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(
                    evidence_manifest_path.read_bytes()
                ).hexdigest(),
            }
            if evidence_manifest_path is not None
            else None
        ),
        "encoded_upstream_manifest": (
            {
                "path": encoded_evidence_manifest_path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(
                    encoded_evidence_manifest_path.read_bytes()
                ).hexdigest(),
            }
            if encoded_evidence_manifest_path is not None
            else None
        ),
        "outputs": {
            output_cosine.relative_to(ROOT).as_posix(): hashlib.sha256(
                output_cosine.read_bytes()
            ).hexdigest(),
            state_error.relative_to(ROOT).as_posix(): hashlib.sha256(
                state_error.read_bytes()
            ).hexdigest(),
        },
        "configuration": configuration,
        "metric_contract": {
            "output_cosine": "cosine similarity against FP32 recurrence output after flattening all value heads and V coordinates",
            "state_relative_l2": (
                "complete H,K,V tensor flattened; ||candidate-reference||2 / max(||reference||2, 1e-12)"
            ),
            "headwise_metrics": "NOT_RUN",
        },
        "source": {
            "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "limitations": [
            "synthetic nominal inputs",
            (
                "native encoded MXFP4 is software-executed; HLS/RTL parity is separately bounded to 64 tokens"
                if encoded_rows
                else "floating quantize/dequantize arithmetic rather than encoded HLS arithmetic"
            ),
            "single deterministic development trace without an uncertainty interval",
            "not closed-loop Qwen quality or physical-FPGA evidence",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-cosine", type=Path, default=DEFAULT_OUTPUT_COSINE)
    parser.add_argument("--state-error", type=Path, default=DEFAULT_STATE_ERROR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--evidence-manifest", type=Path, default=DEFAULT_EVIDENCE_MANIFEST
    )
    parser.add_argument("--encoded-input", type=Path, default=DEFAULT_ENCODED_INPUT)
    parser.add_argument(
        "--encoded-evidence-manifest",
        type=Path,
        default=DEFAULT_ENCODED_EVIDENCE_MANIFEST,
    )
    args = parser.parse_args(argv)
    encoded_input = _resolve(args.encoded_input)
    encoded_manifest = _resolve(args.encoded_evidence_manifest)
    if encoded_input.exists() != encoded_manifest.exists():
        raise FileNotFoundError(
            "native encoded plot input and manifest must either both exist or both be absent"
        )
    generate_plots(
        _resolve(args.input),
        _resolve(args.output_cosine),
        _resolve(args.state_error),
        _resolve(args.manifest),
        _resolve(args.evidence_manifest),
        encoded_input if encoded_input.exists() else None,
        encoded_manifest if encoded_manifest.exists() else None,
    )
    print(_resolve(args.output_cosine).relative_to(ROOT).as_posix())
    print(_resolve(args.state_error).relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

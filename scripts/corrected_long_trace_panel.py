"""Generate a compact paper panel from verified corrected long-trace data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from scripts.evidence_source_snapshot import describe_source_files
from scripts.reportlab_fonts import FONT_SOURCE, register_embedded_sans
from scripts.plot_long_sequence_stability import (
    ROOT,
    RS2_VARIANT,
    VARIANT_ORDER,
    _group_series,
    _read_rows,
    _variant_color,
    _variant_dash,
)


register_embedded_sans()


DEFAULT_UPSTREAM = (
    ROOT / "paper" / "figures" / "corrected" / "long_trace_plot_manifest.json"
)
DEFAULT_OUTPUT = (
    ROOT / "paper" / "figures" / "corrected" / "long_sequence_stability_panel.pdf"
)
DEFAULT_MANIFEST = (
    ROOT
    / "paper"
    / "figures"
    / "corrected"
    / "long_sequence_stability_panel_manifest.json"
)
PAGE_WIDTH = 7.16 * 72
PAGE_HEIGHT = 3.25 * 72

SHORT_NAMES = {
    "fp32": "FP32 reference",
    "bf16_qdq_fp32_accum_state_bf16": "BF16",
    "native_mxfp4_encoded_act_b32_state_b32": "Encoded MXFP4",
    RS2_VARIANT: "Native MXFP4 RS2/R3",
    "mxfp4_qdq_act_b32_state_b32": "MXFP4 floating Q/DQ",
    "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32": "MXFP4 Q/DQ + MXFP8 state",
    "flat_int4_qdq": "Flat INT4",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _verified_rows(upstream_path: Path) -> tuple[list[dict[str, str]], dict[str, object]]:
    upstream = json.loads(upstream_path.read_text(encoding="utf-8"))
    if upstream.get("status") != "PASS":
        raise ValueError("upstream long-trace plot manifest is not PASS")
    rows: list[dict[str, str]] = []
    for field in ("input", "encoded_input"):
        record = upstream.get(field)
        if not record:
            continue
        path = ROOT / str(record["path"])
        if not path.is_file() or _sha256(path) != str(record["sha256"]).upper():
            raise ValueError(f"upstream long-trace input hash mismatch: {path}")
        rows.extend(_read_rows(path))
    if not rows:
        raise ValueError("upstream manifest provides no plot rows")
    return rows, upstream


def _draw_panel(
    drawing: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    series: dict[str, list[tuple[int, float]]],
    y_ticks: list[float],
    y_min: float,
    y_max: float,
    log_y: bool,
    threshold: float,
    threshold_label: str,
) -> None:
    max_token = max(token for values in series.values() for token, _ in values)
    x_max = math.log10(max_token)

    def x_pos(token: int) -> float:
        return x + math.log10(max(token, 1)) / x_max * width

    def y_pos(value: float) -> float:
        transformed = math.log10(max(value, 1e-12)) if log_y else value
        low = math.log10(y_min) if log_y else y_min
        high = math.log10(y_max) if log_y else y_max
        return y + (transformed - low) / (high - low) * height

    drawing.setFillColorRGB(0.08, 0.08, 0.08)
    drawing.setFont("Helvetica-Bold", 8.0)
    drawing.drawString(x, y + height + 8, title)

    drawing.setLineWidth(0.35)
    for tick in y_ticks:
        tick_y = y_pos(tick)
        drawing.setStrokeColorRGB(0.86, 0.88, 0.89)
        drawing.line(x, tick_y, x + width, tick_y)
        drawing.setFillColorRGB(0.25, 0.25, 0.25)
        drawing.setFont("Helvetica", 6.2)
        label = f"{tick:.0e}" if log_y else f"{tick:.1f}"
        drawing.drawRightString(x - 4, tick_y - 2, label)

    x_ticks = (1, 8, 64, 512, max_token)
    for tick in x_ticks:
        tick_x = x_pos(tick)
        drawing.setStrokeColorRGB(0.91, 0.92, 0.93)
        drawing.line(tick_x, y, tick_x, y + height)
        drawing.setFillColorRGB(0.25, 0.25, 0.25)
        drawing.setFont("Helvetica", 6.2)
        drawing.drawCentredString(tick_x, y - 10, f"{tick:,}")

    drawing.setStrokeColorRGB(0.12, 0.12, 0.12)
    drawing.setLineWidth(0.7)
    drawing.rect(x, y, width, height, fill=0, stroke=1)

    threshold_y = y_pos(threshold)
    drawing.setDash(3, 2)
    drawing.setStrokeColorRGB(0.34, 0.34, 0.34)
    drawing.line(x, threshold_y, x + width, threshold_y)
    drawing.setDash()

    for index, variant in enumerate(VARIANT_ORDER):
        points = series.get(variant)
        if not points:
            continue
        color = _variant_color(variant, index)
        drawing.setStrokeColorRGB(*color)
        drawing.setLineWidth(1.0)
        dash = _variant_dash(variant)
        if dash:
            drawing.setDash(list(dash))
        else:
            drawing.setDash()
        trace = drawing.beginPath()
        started = False
        for token, value in points:
            if log_y and value <= 0:
                continue
            point_y = y_pos(value)
            if not (y - 1 <= point_y <= y + height + 1):
                continue
            if started:
                trace.lineTo(x_pos(token), point_y)
            else:
                trace.moveTo(x_pos(token), point_y)
                started = True
        if started:
            drawing.drawPath(trace, fill=0, stroke=1)
        drawing.setDash()

    drawing.setFont("Helvetica", 5.8)
    label_width = stringWidth(threshold_label, "Helvetica", 5.8)
    label_x = x + width - 2
    label_y = min(threshold_y + 3, y + height - 7)
    drawing.setFillColorRGB(1, 1, 1)
    drawing.rect(
        label_x - label_width - 3,
        label_y - 2,
        label_width + 5,
        7,
        fill=1,
        stroke=0,
    )
    drawing.setFillColorRGB(0.28, 0.28, 0.28)
    drawing.drawRightString(label_x, label_y, threshold_label)


def generate(upstream_path: Path, output: Path, manifest_path: Path) -> dict[str, object]:
    rows, upstream = _verified_rows(upstream_path)
    cosine = _group_series(rows, "output_cosine_fp32", include_fp32=True)
    state = _group_series(rows, "state_rel_l2", include_fp32=False)
    variants = [variant for variant in VARIANT_ORDER if variant in cosine or variant in state]

    output.parent.mkdir(parents=True, exist_ok=True)
    drawing = canvas.Canvas(
        str(output), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), invariant=1
    )
    drawing.setTitle("Long-horizon synthetic GDN drift")
    drawing.setAuthor("FPT26_data_review evidence pipeline")
    drawing.setFillColorRGB(1, 1, 1)
    drawing.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    drawing.setFillColorRGB(0.08, 0.08, 0.08)
    drawing.setFont("Helvetica-Bold", 9.2)
    drawing.drawString(35, PAGE_HEIGHT - 13, "Long-horizon synthetic recurrence drift")

    legend_x = 35
    legend_y = PAGE_HEIGHT - 29
    drawing.setFont("Helvetica", 6.3)
    for index, variant in enumerate(variants):
        label = SHORT_NAMES[variant]
        color = _variant_color(variant, index)
        drawing.setStrokeColorRGB(*color)
        drawing.setLineWidth(1.3)
        dash = _variant_dash(variant)
        if dash:
            drawing.setDash(list(dash))
        else:
            drawing.setDash()
        drawing.line(legend_x, legend_y + 2, legend_x + 12, legend_y + 2)
        drawing.setDash()
        drawing.setFillColorRGB(0.15, 0.15, 0.15)
        drawing.drawString(legend_x + 15, legend_y, label)
        legend_x += 22 + stringWidth(label, "Helvetica", 6.3) + 9

    panel_y = 34
    panel_h = 145
    panel_w = 203
    left_x = 42
    right_x = 300
    _draw_panel(
        drawing,
        x=left_x,
        y=panel_y,
        width=panel_w,
        height=panel_h,
        title="(a) Output cosine versus FP32",
        series=cosine,
        y_ticks=[0.4, 0.6, 0.8, 1.0],
        y_min=0.3,
        y_max=1.01,
        log_y=False,
        threshold=0.99,
        threshold_label="gate 0.99",
    )
    _draw_panel(
        drawing,
        x=right_x,
        y=panel_y,
        width=panel_w,
        height=panel_h,
        title="(b) Recurrent-state relative L2",
        series=state,
        y_ticks=[1e-3, 1e-2, 1e-1, 1, 10],
        y_min=1e-3,
        y_max=10,
        log_y=True,
        threshold=0.10,
        threshold_label="gate 0.10",
    )
    drawing.setFillColorRGB(0.15, 0.15, 0.15)
    drawing.setFont("Helvetica", 6.8)
    drawing.drawCentredString(PAGE_WIDTH / 2, 9, "Decode token index (log scale)")
    drawing.saveState()
    drawing.translate(11, panel_y + panel_h / 2)
    drawing.rotate(90)
    drawing.drawCentredString(0, 0, "Cosine similarity")
    drawing.restoreState()
    drawing.saveState()
    drawing.translate(269, panel_y + panel_h / 2)
    drawing.rotate(90)
    drawing.drawCentredString(0, 0, "Relative L2 error (log scale)")
    drawing.restoreState()
    drawing.showPage()
    drawing.save()

    source_identity = describe_source_files(
        [
            Path(__file__),
            FONT_SOURCE,
            ROOT / "scripts" / "plot_long_sequence_stability.py",
        ]
    )
    output_key = (
        output.relative_to(ROOT).as_posix()
        if output.is_relative_to(ROOT)
        else str(output)
    )
    manifest = {
        "schema": 1,
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "paper-scale combined long-sequence synthetic drift panel",
        "source_identity": source_identity,
        "upstream_manifest": (
            upstream_path.relative_to(ROOT).as_posix()
            if upstream_path.is_relative_to(ROOT)
            else str(upstream_path)
        ),
        "upstream_manifest_sha256": _sha256(upstream_path),
        "upstream_output_sha256": upstream["outputs"],
        "variants": variants,
        "outputs": {output_key: _sha256(output)},
        "limitations": [
            "single deterministic layer-level synthetic trace",
            "thresholds are engineering criteria, not model-quality guarantees",
            "full-resolution standalone plots remain separate artifacts",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    manifest = generate(
        _resolve(args.upstream), _resolve(args.output), _resolve(args.manifest)
    )
    print(json.dumps({"status": manifest["status"], "outputs": manifest["outputs"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate an evidence-level storage, quality, and HLS trade-off figure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from scripts.evidence_source_snapshot import describe_source_files
from scripts.reportlab_fonts import FONT_SOURCE, register_embedded_sans


register_embedded_sans()


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "reports" / "benchmark" / "corrected"
DEFAULT_CAPACITY = BENCHMARK / "state_capacity_lower_bound.json"
DEFAULT_LONG_CHECKPOINTS = BENCHMARK / "long_trace_checkpoints.csv"
DEFAULT_LONG_MANIFEST = BENCHMARK / "long_trace_manifest.json"
DEFAULT_NATIVE_CHECKPOINTS = BENCHMARK / "native_encoded_long_trace_checkpoints.csv"
DEFAULT_NATIVE_MANIFEST = BENCHMARK / "native_encoded_long_trace_manifest.json"
DEFAULT_HLS = BENCHMARK / "hls_arithmetic_comparison.json"
DEFAULT_OUTPUT = ROOT / "paper" / "figures" / "corrected" / "tradeoff_evidence.pdf"
DEFAULT_MANIFEST = (
    ROOT / "paper" / "figures" / "corrected" / "tradeoff_evidence_manifest.json"
)

PAGE_WIDTH = 7.16 * 72.0
PAGE_HEIGHT = 3.18 * 72.0

COLORS = {
    "bf16": (0.00, 0.43, 0.46),
    "mxfp4": (0.90, 0.48, 0.04),
    "native_mxfp4": (0.73, 0.16, 0.16),
    "mxfp8": (0.18, 0.39, 0.69),
    "int4": (0.49, 0.30, 0.60),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_pass(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise ValueError(f"input evidence is not PASS: {path}")
    return payload


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"input CSV is empty: {path}")
    return rows


def _verify_manifest_output(
    manifest: dict[str, object], path: Path, *, nested: bool
) -> None:
    relative = path.relative_to(ROOT).as_posix()
    record = manifest.get("outputs", {}).get(relative)
    if nested:
        expected = None if not isinstance(record, dict) else record.get("sha256")
    else:
        expected = record
    if not expected or str(expected).upper() != _sha256(path):
        raise ValueError(f"evidence-manifest hash mismatch: {relative}")


def _bar_panel(
    pdf: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    rows: list[tuple[str, float | None, str, tuple[float, float, float]]],
    maximum: float,
    tick_values: tuple[float, ...],
    tick_format: str,
    value_format: str,
) -> None:
    label_width = 48.0
    plot_x = x + label_width
    plot_width = width - label_width - 5.0
    plot_top = y + height - 19.0
    plot_bottom = y + 17.0
    row_height = (plot_top - plot_bottom) / len(rows)

    pdf.setFillColorRGB(0.08, 0.08, 0.08)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(x, y + height - 8.0, title)

    for tick in tick_values:
        tick_x = plot_x + tick / maximum * plot_width
        pdf.setStrokeColorRGB(0.88, 0.89, 0.90)
        pdf.setLineWidth(0.35)
        pdf.line(tick_x, plot_bottom - 2.0, tick_x, plot_top + 2.0)
        pdf.setFillColorRGB(0.32, 0.32, 0.32)
        pdf.setFont("Helvetica", 5.7)
        pdf.drawCentredString(tick_x, y + 5.0, tick_format.format(tick))

    for index, (label, value, annotation, color) in enumerate(rows):
        center_y = plot_top - (index + 0.5) * row_height
        pdf.setFillColorRGB(0.15, 0.15, 0.15)
        pdf.setFont("Helvetica", 5.9)
        pdf.drawRightString(plot_x - 4.0, center_y - 2.0, label)
        if value is None:
            pdf.setFillColorRGB(0.38, 0.38, 0.38)
            pdf.setFont("Helvetica-Oblique", 5.8)
            pdf.drawString(plot_x + 3.0, center_y - 2.0, annotation)
            continue
        bar_width = value / maximum * plot_width
        pdf.setFillColorRGB(*color)
        pdf.rect(plot_x, center_y - 3.4, bar_width, 6.8, fill=1, stroke=0)
        value_text = value_format.format(value)
        value_width = stringWidth(value_text, "Helvetica-Bold", 5.7)
        text_x = min(plot_x + bar_width + 2.0, x + width - value_width - 1.0)
        pdf.setFillColorRGB(0.12, 0.12, 0.12)
        pdf.setFont("Helvetica-Bold", 5.7)
        pdf.drawString(text_x, center_y - 2.0, value_text)
        if annotation:
            pdf.setFillColorRGB(0.34, 0.34, 0.34)
            pdf.setFont("Helvetica", 4.9)
            pdf.drawString(plot_x + 1.0, center_y - 8.4, annotation)


def generate(
    capacity_path: Path,
    long_checkpoints_path: Path,
    long_manifest_path: Path,
    native_checkpoints_path: Path,
    native_manifest_path: Path,
    hls_path: Path,
    output: Path,
    manifest_path: Path,
) -> dict[str, object]:
    capacity = _load_pass(capacity_path)
    long_manifest = _load_pass(long_manifest_path)
    native_manifest = _load_pass(native_manifest_path)
    hls = _load_pass(hls_path)
    _verify_manifest_output(long_manifest, long_checkpoints_path, nested=False)
    _verify_manifest_output(native_manifest, native_checkpoints_path, nested=True)

    capacity_rows = {row["variant"]: row for row in capacity["rows"]}
    required_capacity = {
        "BF16",
        "uniform_mxfp4_e2m1_e8m0_b32",
        "mxfp8_e4m3_e8m0_b32",
        "flat_int4",
    }
    if set(capacity_rows) != required_capacity:
        raise ValueError("capacity evidence does not contain the controlled variants")

    long_rows = {
        row["variant"]: row
        for row in _read_csv(long_checkpoints_path)
        if int(row["token_index"]) == 8192
    }
    native_rows = [
        row
        for row in _read_csv(native_checkpoints_path)
        if int(row["token_index"]) == 8192
    ]
    if len(native_rows) != 1:
        raise ValueError("native checkpoint evidence must contain one token-8192 row")
    native_row = native_rows[0]

    quality_specs = (
        ("BF16", "bf16_qdq_fp32_accum_state_bf16", "bf16"),
        ("MXFP4 Q/DQ", "mxfp4_qdq_act_b32_state_b32", "mxfp4"),
        ("Native MXFP4", native_row["variant"], "native_mxfp4"),
        (
            "MXFP8-state Q/DQ",
            "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32",
            "mxfp8",
        ),
        ("Flat INT4", "flat_int4_qdq", "int4"),
    )
    quality: list[tuple[str, float | None, str, tuple[float, float, float]]] = []
    for label, variant, color_key in quality_specs:
        row = native_row if variant == native_row["variant"] else long_rows.get(variant)
        if row is None:
            raise ValueError(f"missing token-8192 quality row: {variant}")
        quality.append(
            (label, float(row["output_cosine_fp32"]), "", COLORS[color_key])
        )

    hls_rows = {row["variant"]: row for row in hls["rows"]}
    if set(hls_rows) != {"BF16", "uniform_mxfp4", "native_mxfp8"}:
        raise ValueError("HLS evidence must contain the matched BF16/MXFP4/MXFP8 points")

    layer_count = int(capacity["configuration"]["num_layers"])
    if layer_count != int(hls["controlled_configuration"]["num_layers"]):
        raise ValueError("capacity and HLS layer counts differ")

    storage_specs = (
        ("BF16", "BF16", "bf16"),
        ("MXFP4", "uniform_mxfp4_e2m1_e8m0_b32", "mxfp4"),
        ("MXFP8", "mxfp8_e4m3_e8m0_b32", "mxfp8"),
        ("INT4", "flat_int4", "int4"),
    )
    storage = []
    for label, variant, color_key in storage_specs:
        row = capacity_rows[variant]
        physical = str(row["physical_banked_fit"])
        physical_label = "N/R" if physical == "NOT_RUN" else physical
        storage.append(
            (
                label,
                float(row["logical_state_bytes"]) / (1024.0 * 1024.0),
                f"raw {row['raw_bit_capacity_necessary_condition']}; phys {physical_label}",
                COLORS[color_key],
            )
        )

    hls_panel = [
        (
            "BF16",
            float(hls_rows["BF16"]["step_cycles_max"]) / 1_000_000.0,
            "HLS estimate",
            COLORS["bf16"],
        ),
        (
            "Native MXFP4",
            float(hls_rows["uniform_mxfp4"]["step_cycles_max"]) / 1_000_000.0,
            "HLS estimate",
            COLORS["native_mxfp4"],
        ),
        (
            "Native MXFP8",
            float(hls_rows["native_mxfp8"]["step_cycles_max"]) / 1_000_000.0,
            "HLS estimate",
            COLORS["mxfp8"],
        ),
        ("INT4", None, "matched HLS not run", COLORS["int4"]),
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), invariant=1)
    pdf.setTitle("Evidence-level storage, quality, and HLS trade-offs")
    pdf.setAuthor("FPT26_data_review evidence pipeline")
    pdf.setFillColorRGB(1.0, 1.0, 1.0)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    pdf.setFillColorRGB(0.08, 0.08, 0.08)
    pdf.setFont("Helvetica-Bold", 9.2)
    pdf.drawString(28.0, PAGE_HEIGHT - 14.0, "Controlled evidence across three non-interchangeable levels")
    pdf.setFont("Helvetica", 5.7)
    pdf.setFillColorRGB(0.32, 0.32, 0.32)
    pdf.drawRightString(
        PAGE_WIDTH - 26.0,
        PAGE_HEIGHT - 24.0,
        "Logical storage / synthetic trace / Vitis HLS estimate",
    )

    panel_y = 34.0
    panel_height = PAGE_HEIGHT - 58.0
    gap = 12.0
    panel_width = (PAGE_WIDTH - 56.0 - 2.0 * gap) / 3.0
    panel_x = [28.0, 28.0 + panel_width + gap, 28.0 + 2.0 * (panel_width + gap)]
    _bar_panel(
        pdf,
        x=panel_x[0],
        y=panel_y,
        width=panel_width,
        height=panel_height,
        title=f"(a) Logical state, {layer_count} cores (MiB)",
        rows=storage,
        maximum=40.0,
        tick_values=(0.0, 20.0, 40.0),
        tick_format="{:.0f}",
        value_format="{:.2f}",
    )
    _bar_panel(
        pdf,
        x=panel_x[1],
        y=panel_y,
        width=panel_width,
        height=panel_height,
        title="(b) Token-8,192 output cosine",
        rows=quality,
        maximum=1.05,
        tick_values=(0.0, 0.5, 1.0),
        tick_format="{:.1f}",
        value_format="{:.3f}",
    )
    _bar_panel(
        pdf,
        x=panel_x[2],
        y=panel_y,
        width=panel_width,
        height=panel_height,
        title="(c) HLS max STEP (M cycles)",
        rows=hls_panel,
        maximum=7.0,
        tick_values=(0.0, 3.5, 7.0),
        tick_format="{:.1f}",
        value_format="{:.3f}",
    )
    pdf.setFillColorRGB(0.31, 0.31, 0.31)
    pdf.setFont("Helvetica", 5.4)
    pdf.drawString(
        28.0,
        11.0,
        "Raw capacity is necessary, not routed fit. Phys reports per-format implementation status. N/R points are not imputed.",
    )
    pdf.showPage()
    pdf.save()

    source_identity = describe_source_files([Path(__file__).resolve(), FONT_SOURCE])
    output_key = (
        output.relative_to(ROOT).as_posix()
        if output.is_relative_to(ROOT)
        else str(output)
    )
    used_values = {
        "storage_mib": {row[0]: row[1] for row in storage},
        "token_8192_output_cosine": {row[0]: row[1] for row in quality},
        "hls_step_max_mcycles": {
            row[0]: row[1] for row in hls_panel if row[1] is not None
        },
    }
    inputs = (
        capacity_path,
        long_checkpoints_path,
        long_manifest_path,
        native_checkpoints_path,
        native_manifest_path,
        hls_path,
    )
    manifest = {
        "schema": 1,
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "cross-evidence logical-storage, synthetic-quality, and HLS-schedule figure",
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "inputs_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in inputs
        },
        "outputs": {output_key: _sha256(output)},
        "used_values": used_values,
        "evidence_levels": {
            "storage": "logical bits, ideal primitive-capacity lower bounds, and per-format physical-fit status",
            "quality": "one deterministic layer-level synthetic nominal trace",
            "schedule": "Vitis HLS C-synthesis estimate",
        },
        "not_run": [
            "matched INT4 HLS baseline",
            "uniform-MXFP4 and flat-INT4 physical all-layer banking and fit",
            "board energy",
        ],
        "limitations": [
            "panels juxtapose evidence levels and do not form a measured Pareto frontier",
            "floating Q/DQ quality points are not native hardware implementations",
            "raw bit capacity ignores width, banking, ports, replication, placement, and routing",
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
    parser.add_argument("--capacity", type=Path, default=DEFAULT_CAPACITY)
    parser.add_argument("--long-checkpoints", type=Path, default=DEFAULT_LONG_CHECKPOINTS)
    parser.add_argument("--long-manifest", type=Path, default=DEFAULT_LONG_MANIFEST)
    parser.add_argument(
        "--native-checkpoints", type=Path, default=DEFAULT_NATIVE_CHECKPOINTS
    )
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument("--hls", type=Path, default=DEFAULT_HLS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    result = generate(
        _resolve(args.capacity),
        _resolve(args.long_checkpoints),
        _resolve(args.long_manifest),
        _resolve(args.native_checkpoints),
        _resolve(args.native_manifest),
        _resolve(args.hls),
        _resolve(args.output),
        _resolve(args.manifest),
    )
    print(json.dumps({"status": result["status"], "outputs": result["outputs"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

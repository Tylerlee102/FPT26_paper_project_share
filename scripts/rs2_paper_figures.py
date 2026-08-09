"""Generate RS2/R3 paper figures exclusively from canonical paper numbers."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NUMBERS = ROOT / "paper" / "corrected" / "numbers.json"
DEFAULT_OUTPUT = ROOT / "paper" / "figures" / "corrected"
DEFAULT_MANIFEST = DEFAULT_OUTPUT / "rs2_paper_figures_manifest.json"

CHECKPOINTS = (64, 256, 1024, 4096, 8192)
SERIES = (
    ("fp32", "FP32", (0.08, 0.08, 0.08), ()),
    ("bf16", "BF16", (0.00, 0.43, 0.48), (7, 2)),
    ("mxfp4_qdq", "MXFP4 Q/DQ", (0.88, 0.48, 0.05), (2, 2)),
    ("mxfp8_state", "MXFP8 state", (0.20, 0.38, 0.70), (5, 2)),
    ("int4", "Flat INT4", (0.55, 0.32, 0.62), (1, 2)),
    ("rs2", "Native MXFP4 RS2/R3", (0.05, 0.52, 0.27), (9, 2, 2, 2)),
)

TRACE_PAGE_WIDTH = 3.45 * 72.0
TRACE_PAGE_HEIGHT = 2.85 * 72.0
TRACE_LEFT = 43.0
TRACE_RIGHT = 20.0
TRACE_BOTTOM = 36.0
TRACE_TOP = 58.0

TRADEOFF_PAGE_WIDTH = 7.16 * 72.0
TRADEOFF_PAGE_HEIGHT = 3.55 * 72.0
TRADEOFF_LEFT = 55.0
TRADEOFF_RIGHT = 16.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_numbers(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise ValueError("canonical paper numbers must be a non-empty object")
    return payload


def _value(numbers: dict[str, dict[str, object]], key: str) -> float:
    row = numbers.get(key)
    if not isinstance(row, dict) or "value" not in row:
        raise KeyError(f"missing canonical RS2 paper number: {key}")
    value = float(row["value"])
    if not math.isfinite(value):
        raise ValueError(f"nonfinite canonical RS2 paper number: {key}")
    return value


def _set_dash(pdf: canvas.Canvas, dash: tuple[int, ...]) -> None:
    pdf.setDash(list(dash) if dash else [])


def _draw_axes(
    pdf: canvas.Canvas,
    *,
    title: str,
    y_label: str,
    y_ticks: list[float],
    y_map,
    page_width: float,
    page_height: float,
    left: float,
    right: float,
    bottom: float,
    top: float,
) -> tuple[float, float, float, float]:
    x0 = left
    y0 = bottom
    width = page_width - left - right
    height = page_height - bottom - top
    pdf.setFillColorRGB(0.08, 0.08, 0.08)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(x0, page_height - 15, title)
    pdf.setLineWidth(0.6)
    pdf.line(x0, y0, x0 + width, y0)
    pdf.line(x0, y0, x0, y0 + height)
    pdf.setFont("Helvetica", 7.5)
    for tick in y_ticks:
        y = y_map(tick)
        pdf.setStrokeColorRGB(0.84, 0.84, 0.84)
        pdf.setLineWidth(0.35)
        pdf.line(x0, y, x0 + width, y)
        pdf.setFillColorRGB(0.15, 0.15, 0.15)
        label = f"{tick:.3g}"
        pdf.drawRightString(x0 - 5, y - 2.5, label)
    pdf.saveState()
    pdf.translate(11, y0 + height / 2)
    pdf.rotate(90)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(0, 0, y_label)
    pdf.restoreState()
    pdf.setFillColorRGB(0.15, 0.15, 0.15)
    pdf.setFont("Helvetica", 7.5)
    for token in CHECKPOINTS:
        x = x0 + width * (
            (math.log10(token) - math.log10(CHECKPOINTS[0]))
            / (math.log10(CHECKPOINTS[-1]) - math.log10(CHECKPOINTS[0]))
        )
        pdf.line(x, y0, x, y0 - 3)
        pdf.drawCentredString(x, y0 - 13, f"{token:,}")
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(x0 + width / 2, 10, "Token index")
    return x0, y0, width, height


def _draw_legend(
    pdf: canvas.Canvas,
    series,
    *,
    page_width: float,
    page_height: float,
    left: float,
    right: float,
) -> None:
    pdf.setFont("Helvetica", 6.5)
    x = left
    y = page_height - 29
    for _, label, color, dash in series:
        needed = 18 + stringWidth(label, "Helvetica", 6.5) + 7
        if x + needed > page_width - right:
            x = left
            y -= 9
        pdf.setStrokeColorRGB(*color)
        pdf.setLineWidth(1.5)
        _set_dash(pdf, dash)
        pdf.line(x, y + 2, x + 13, y + 2)
        pdf.setDash()
        pdf.setFillColorRGB(0.12, 0.12, 0.12)
        pdf.drawString(x + 16, y, label)
        x += needed


def _draw_trace_figure(
    path: Path,
    numbers: dict[str, dict[str, object]],
    *,
    metric: str,
    title: str,
    y_label: str,
    logarithmic: bool,
) -> None:
    plotted = SERIES if metric == "output_cosine" else SERIES[1:]
    values = {
        slug: [_value(numbers, f"rs2_{slug}_token_{token}_{metric}") for token in CHECKPOINTS]
        for slug, _, _, _ in plotted
    }
    all_values = [value for row in values.values() for value in row]
    if logarithmic:
        positive = [value for value in all_values if value > 0.0]
        if len(positive) != len(all_values):
            raise ValueError("state-relative-L2 figure requires positive values")
        low_power = math.floor(math.log10(min(positive)))
        high_power = math.ceil(math.log10(max(positive)))
        if high_power == low_power:
            high_power += 1
        y_ticks = [10.0**power for power in range(low_power, high_power + 1)]

        def y_norm(value: float) -> float:
            return (math.log10(value) - low_power) / (high_power - low_power)

    else:
        low = max(0.0, math.floor((min(all_values) - 0.04) * 10.0) / 10.0)
        high = 1.0
        if low >= high:
            low = max(0.0, high - 0.1)
        step = 0.1 if high - low > 0.25 else 0.02
        count = int(round((high - low) / step))
        y_ticks = [low + index * step for index in range(count + 1)]

        def y_norm(value: float) -> float:
            return (value - low) / (high - low)

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(
        str(path), pagesize=(TRACE_PAGE_WIDTH, TRACE_PAGE_HEIGHT), invariant=1
    )
    pdf.setTitle(title)
    pdf.setAuthor("FPT26_data_review evidence pipeline")

    x0 = TRACE_LEFT
    y0 = TRACE_BOTTOM
    plot_width = TRACE_PAGE_WIDTH - TRACE_LEFT - TRACE_RIGHT
    plot_height = TRACE_PAGE_HEIGHT - TRACE_BOTTOM - TRACE_TOP

    def y_map(value: float) -> float:
        return y0 + plot_height * y_norm(value)

    _draw_axes(
        pdf,
        title=title,
        y_label=y_label,
        y_ticks=y_ticks,
        y_map=y_map,
        page_width=TRACE_PAGE_WIDTH,
        page_height=TRACE_PAGE_HEIGHT,
        left=TRACE_LEFT,
        right=TRACE_RIGHT,
        bottom=TRACE_BOTTOM,
        top=TRACE_TOP,
    )
    _draw_legend(
        pdf,
        plotted,
        page_width=TRACE_PAGE_WIDTH,
        page_height=TRACE_PAGE_HEIGHT,
        left=TRACE_LEFT,
        right=TRACE_RIGHT,
    )
    if metric == "output_cosine":
        threshold = _value(numbers, "rs2_quality_minimum_cosine_gate")
        threshold_label = f"gate >= {threshold:.2f}"
    else:
        threshold = _value(numbers, "rs2_quality_maximum_state_relative_l2_gate")
        threshold_label = f"gate <= {threshold:.2f}"
    threshold_y = y_map(threshold)
    if y0 <= threshold_y <= y0 + plot_height:
        pdf.setStrokeColorRGB(0.35, 0.35, 0.35)
        pdf.setFillColorRGB(0.25, 0.25, 0.25)
        pdf.setLineWidth(0.7)
        pdf.setDash(3, 2)
        pdf.line(x0, threshold_y, x0 + plot_width, threshold_y)
        pdf.setDash()
        pdf.setFont("Helvetica", 6.0)
        pdf.drawRightString(x0 + plot_width - 2, threshold_y + 3, threshold_label)
    for slug, _, color, dash in plotted:
        points: list[tuple[float, float]] = []
        for token, value in zip(CHECKPOINTS, values[slug], strict=True):
            x = x0 + plot_width * (
                (math.log10(token) - math.log10(CHECKPOINTS[0]))
                / (math.log10(CHECKPOINTS[-1]) - math.log10(CHECKPOINTS[0]))
            )
            points.append((x, y_map(value)))
        pdf.setStrokeColorRGB(*color)
        pdf.setFillColorRGB(*color)
        pdf.setLineWidth(1.35)
        _set_dash(pdf, dash)
        for left, right in zip(points, points[1:]):
            pdf.line(left[0], left[1], right[0], right[1])
        pdf.setDash()
        for x, y in points:
            pdf.circle(x, y, 2.1, stroke=1, fill=1)
    pdf.showPage()
    pdf.save()


def _bar_panel(
    pdf: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    values: list[tuple[str, float, tuple[float, float, float]]],
    formatter,
    logarithmic: bool = False,
) -> None:
    pdf.setFillColorRGB(0.08, 0.08, 0.08)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(x, y + height + 10, title)
    transformed = [math.log10(value) if logarithmic else value for _, value, _ in values]
    high = max(transformed) * 1.12 if max(transformed) > 0 else 1.0
    bar_width = width / (len(values) * 1.7)
    gap = (width - bar_width * len(values)) / (len(values) + 1)
    pdf.setStrokeColorRGB(0.35, 0.35, 0.35)
    pdf.setLineWidth(0.4)
    pdf.line(x, y, x + width, y)
    for index, ((label, raw, color), value) in enumerate(zip(values, transformed, strict=True)):
        bar_x = x + gap * (index + 1) + bar_width * index
        bar_height = height * value / high
        pdf.setFillColorRGB(*color)
        pdf.rect(bar_x, y, bar_width, bar_height, stroke=0, fill=1)
        pdf.setFillColorRGB(0.10, 0.10, 0.10)
        pdf.setFont("Helvetica", 6.7)
        pdf.drawCentredString(bar_x + bar_width / 2, y - 9, label)
        pdf.setFont("Helvetica-Bold", 6.5)
        pdf.drawCentredString(
            bar_x + bar_width / 2,
            min(y + bar_height + 3, y + height + 1),
            formatter(raw),
        )


def _draw_tradeoff(
    path: Path,
    numbers: dict[str, dict[str, object]],
) -> None:
    colors = {
        "BF16": (0.00, 0.43, 0.48),
        "MXFP8": (0.20, 0.38, 0.70),
        "RS2/R3": (0.05, 0.52, 0.27),
    }
    labels = ("BF16", "MXFP8", "RS2/R3")
    storage = [
        (label, _value(numbers, f"rs2_tradeoff_{slug}_state_bytes") / 1024.0, colors[label])
        for label, slug in zip(labels, ("bf16", "mxfp8", "candidate"), strict=True)
    ]
    quality = [
        (label, _value(numbers, f"rs2_tradeoff_{slug}_output_cosine"), colors[label])
        for label, slug in zip(labels, ("bf16", "mxfp8", "candidate"), strict=True)
    ]
    schedule = [
        (label, _value(numbers, f"rs2_tradeoff_{slug}_hls_cycles"), colors[label])
        for label, slug in zip(labels, ("bf16", "mxfp8", "candidate"), strict=True)
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(
        str(path),
        pagesize=(TRADEOFF_PAGE_WIDTH, TRADEOFF_PAGE_HEIGHT),
        invariant=1,
    )
    pdf.setTitle("Memory, stability, and HLS schedule trade-off")
    pdf.setAuthor("FPT26_data_review evidence pipeline")
    pdf.setFillColorRGB(0.08, 0.08, 0.08)
    pdf.setFont("Helvetica-Bold", 10.5)
    pdf.drawString(
        TRADEOFF_LEFT,
        TRADEOFF_PAGE_HEIGHT - 20,
        "Memory, stability, and HLS schedule trade-off",
    )
    panel_gap = 18.0
    panel_width = (
        TRADEOFF_PAGE_WIDTH - TRADEOFF_LEFT - TRADEOFF_RIGHT - 2 * panel_gap
    ) / 3
    panel_y = 57.0
    panel_height = 125.0
    _bar_panel(
        pdf,
        x=TRADEOFF_LEFT,
        y=panel_y,
        width=panel_width,
        height=panel_height,
        title="(a) State payload (KiB/layer)",
        values=storage,
        formatter=lambda value: f"{value:.0f}",
    )
    _bar_panel(
        pdf,
        x=TRADEOFF_LEFT + panel_width + panel_gap,
        y=panel_y,
        width=panel_width,
        height=panel_height,
        title="(b) Token-8192 cosine",
        values=quality,
        formatter=lambda value: f"{value:.3f}",
    )
    _bar_panel(
        pdf,
        x=TRADEOFF_LEFT + 2 * (panel_width + panel_gap),
        y=panel_y,
        width=panel_width,
        height=panel_height,
        title="(c) HLS cycles/STEP (log10)",
        values=schedule,
        formatter=lambda value: f"{value / 1e6:.1f}M",
        logarithmic=True,
    )
    pdf.setFillColorRGB(0.20, 0.20, 0.20)
    pdf.setFont("Helvetica", 6.8)
    pdf.drawString(
        TRADEOFF_LEFT,
        25,
        "MXFP8 quality uses MXFP4 operands with MXFP8 state; its HLS bar is the separately scoped native-MXFP8 comparator.",
    )
    pdf.drawString(
        TRADEOFF_LEFT,
        15,
        "Schedule bars are estimates; they are not board latency or energy measurements.",
    )
    pdf.showPage()
    pdf.save()


def generate(
    numbers_path: Path,
    output_dir: Path,
    manifest_path: Path,
) -> dict[str, object]:
    numbers = _load_numbers(numbers_path)
    cosine = output_dir / "rs2_output_cosine_vs_token.pdf"
    state = output_dir / "rs2_state_relative_l2_vs_token.pdf"
    tradeoff = output_dir / "rs2_memory_performance_accuracy.pdf"
    _draw_trace_figure(
        cosine,
        numbers,
        metric="output_cosine",
        title="Output cosine over token index",
        y_label="Cosine similarity to FP32",
        logarithmic=False,
    )
    _draw_trace_figure(
        state,
        numbers,
        metric="state_relative_l2",
        title="State relative L2 error over token index",
        y_label="State relative L2 error",
        logarithmic=True,
    )
    _draw_tradeoff(tradeoff, numbers)
    outputs = (cosine, state, tradeoff)
    manifest = {
        "schema": 1,
        "status": "PASS",
        "scope": "RS2/R3 paper figures generated exclusively from canonical paper numbers",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "numbers": {"path": _relative(numbers_path), "sha256": _sha256(numbers_path)},
        "checkpoints": list(CHECKPOINTS),
        "threshold_keys": [
            "rs2_quality_minimum_cosine_gate",
            "rs2_quality_maximum_state_relative_l2_gate",
        ],
        "outputs": {_relative(path): _sha256(path) for path in outputs},
        "limitations": [
            "quality panels are layer-level synthetic evidence",
            "HLS schedules are estimates rather than board latency or energy",
            "the MXFP8 quality and native-HLS bars have separately labeled arithmetic boundaries",
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
    parser.add_argument("--numbers", type=Path, default=DEFAULT_NUMBERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    result = generate(
        _resolve(args.numbers), _resolve(args.output), _resolve(args.manifest)
    )
    print(json.dumps({"status": result["status"], "outputs": result["outputs"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
NUMBERS = ROOT / "paper" / "numbers.json"
SWEEP_CSV = ROOT / "reports" / "benchmark" / "sweep.csv"
OUT_DIR = ROOT / "paper" / "graph_previews"
REPORT = ROOT / "reports" / "graph_previews.md"


INK = "#15202b"
MUTED = "#5b6673"
GRID = "#d8dee8"
PAPER = "#ffffff"
SOFT = "#f4f7fb"
NAVY = "#1f3a5f"
BLUE = "#2e5e9e"
TEAL = "#137c72"
GREEN = "#2d7d46"
AMBER = "#b86b18"
RED = "#b43d3d"
PLUM = "#5d4a7d"


def _font_path(name: str) -> str | None:
    candidates = [
        Path("C:/Windows/Fonts") / name,
        Path("/usr/share/fonts/truetype/dejavu") / name,
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    names = ["segoeuib.ttf", "DejaVuSans-Bold.ttf"] if bold else ["segoeui.ttf", "DejaVuSans.ttf"]
    for name in names:
        path = _font_path(name)
        if path:
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _load_numbers() -> dict[str, dict[str, object]]:
    return json.loads(NUMBERS.read_text(encoding="utf-8"))


def _read_sweep() -> list[dict[str, str]]:
    if not SWEEP_CSV.exists():
        return []
    with SWEEP_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _v(numbers: dict[str, dict[str, object]], key: str) -> float:
    return float(numbers[key]["value"])


def _fmt(value: float, digits: int = 2) -> str:
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    size: int = 28,
    color: str = INK,
    bold: bool = False,
    anchor: str | None = None,
) -> None:
    draw.text(xy, text, fill=color, font=_font(size, bold=bold), anchor=anchor)


def _base(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1800, 1120), "#f7f9fc")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((46, 46, 1754, 1074), radius=34, fill=PAPER, outline="#dfe5ee", width=2)
    draw.rectangle((46, 46, 1754, 182), fill=NAVY)
    draw.rounded_rectangle((46, 46, 1754, 182), radius=34, fill=NAVY)
    draw.rectangle((46, 148, 1754, 182), fill=NAVY)
    _text(draw, (86, 74), title, size=44, color=PAPER, bold=True)
    _text(draw, (88, 130), subtitle, size=25, color="#dbe7f7")
    return image, draw


def _save(image: Image.Image, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    image.save(path)
    return path


def _panel(draw: ImageDraw.ImageDraw, xyxy: tuple[int, int, int, int], title: str) -> None:
    draw.rounded_rectangle(xyxy, radius=22, fill=PAPER, outline=GRID, width=2)
    _text(draw, (xyxy[0] + 28, xyxy[1] + 24), title, size=28, bold=True, color=INK)


def _legend(draw: ImageDraw.ImageDraw, x: int, y: int, items: list[tuple[str, str]]) -> None:
    cursor = x
    for label, color in items:
        draw.rounded_rectangle((cursor, y, cursor + 28, y + 18), radius=8, fill=color)
        _text(draw, (cursor + 38, y - 3), label, size=20, color=MUTED)
        cursor += 38 + int(draw.textbbox((0, 0), label, font=_font(20))[2]) + 34


def _bar_chart(
    draw: ImageDraw.ImageDraw,
    *,
    box: tuple[int, int, int, int],
    labels: list[str],
    values: list[float],
    colors: list[str],
    unit: str,
    log_scale: bool = False,
    lower: float = 0.0,
) -> None:
    x1, y1, x2, y2 = box
    chart_x, chart_y = x1 + 70, y1 + 76
    chart_w, chart_h = x2 - x1 - 120, y2 - y1 - 145
    draw.line((chart_x, chart_y + chart_h, chart_x + chart_w, chart_y + chart_h), fill=GRID, width=2)
    draw.line((chart_x, chart_y, chart_x, chart_y + chart_h), fill=GRID, width=2)

    if log_scale:
        min_v = max(min(values) * 0.65, 1e-4)
        max_v = max(values) * 1.25
        min_log, max_log = math.log10(min_v), math.log10(max_v)
        def y_for(v: float) -> float:
            return chart_y + chart_h - chart_h * (math.log10(max(v, min_v)) - min_log) / (max_log - min_log)
        ticks = [0.1, 1, 10, 100, 1000, 10000]
        for tick in ticks:
            if min_v <= tick <= max_v:
                y = y_for(tick)
                draw.line((chart_x - 8, y, chart_x + chart_w, y), fill="#edf1f6", width=1)
                _text(draw, (chart_x - 18, int(y)), f"{tick:g}", size=17, color=MUTED, anchor="rm")
    else:
        max_v = max(values + [lower + 1e-9])
        span = max_v - lower
        if span <= 0:
            span = 1.0
        def y_for(v: float) -> float:
            return chart_y + chart_h - chart_h * (v - lower) / span
        for i in range(5):
            tick = lower + span * i / 4
            y = y_for(tick)
            draw.line((chart_x - 8, y, chart_x + chart_w, y), fill="#edf1f6", width=1)
            _text(draw, (chart_x - 18, int(y)), _fmt(tick, 2), size=17, color=MUTED, anchor="rm")

    slot = chart_w / len(values)
    bar_w = min(110, slot * 0.56)
    for idx, (label, value, color) in enumerate(zip(labels, values, colors)):
        cx = chart_x + slot * idx + slot / 2
        y = y_for(value)
        draw.rounded_rectangle((cx - bar_w / 2, y, cx + bar_w / 2, chart_y + chart_h), radius=10, fill=color)
        _text(draw, (int(cx), chart_y + chart_h + 26), label, size=20, color=INK, anchor="mm")
        _text(draw, (int(cx), int(y) - 14), f"{_fmt(value, 3)} {unit}", size=19, color=INK, bold=True, anchor="mm")


def latency_energy(numbers: dict[str, dict[str, object]]) -> Path:
    image, draw = _base(
        "Graph A: Latency and Energy Comparison",
        "The first visual claim: persistent-state MXFP4 is measured below both cited baselines.",
    )
    labels = ["H100", "USC FPGA", "Ours"]
    colors = [MUTED, BLUE, GREEN]
    _panel(draw, (88, 238, 850, 934), "Latency per token")
    _bar_chart(
        draw,
        box=(116, 300, 822, 880),
        labels=labels,
        values=[
            _v(numbers, "h100_baseline_latency_us"),
            _v(numbers, "usc_baseline_latency_us"),
            _v(numbers, "ours_mxfp4_b32_latency_us"),
        ],
        colors=colors,
        unit="us",
    )
    _panel(draw, (948, 238, 1660, 934), "Energy per token")
    _bar_chart(
        draw,
        box=(976, 300, 1632, 880),
        labels=labels,
        values=[
            _v(numbers, "h100_baseline_energy_mj"),
            _v(numbers, "usc_baseline_energy_mj"),
            _v(numbers, "ours_mxfp4_b32_energy_mj"),
        ],
        colors=colors,
        unit="mJ",
        log_scale=True,
    )
    _text(draw, (100, 982), "Use in paper: shows the headline result without making the reader hunt through a dense table.", size=25, color=MUTED)
    return _save(image, "graph_a_latency_energy.png")


def speedup_energy_eff(numbers: dict[str, dict[str, object]]) -> Path:
    image, draw = _base(
        "Graph B: Derived Speedup and Energy-Efficiency",
        "Ratios are derived from traced source rows in numbers.json; no hand-typed paper numbers.",
    )
    _panel(draw, (88, 238, 850, 934), "Latency speedup")
    _bar_chart(
        draw,
        box=(116, 300, 822, 880),
        labels=["vs H100", "vs USC"],
        values=[_v(numbers, "headline_speedup_vs_h100"), _v(numbers, "headline_speedup_vs_usc")],
        colors=[GREEN, TEAL],
        unit="x",
    )
    _panel(draw, (948, 238, 1660, 934), "Energy efficiency")
    _bar_chart(
        draw,
        box=(976, 300, 1632, 880),
        labels=["vs H100", "vs USC"],
        values=[
            _v(numbers, "headline_energy_efficiency_vs_h100"),
            _v(numbers, "headline_energy_efficiency_vs_usc"),
        ],
        colors=[GREEN, TEAL],
        unit="x",
    )
    _text(draw, (100, 982), "This is the cleanest reviewer-facing way to show what your measured datapath buys.", size=25, color=MUTED)
    return _save(image, "graph_b_speedup_efficiency.png")


def resource_util(numbers: dict[str, dict[str, object]]) -> Path:
    image, draw = _base(
        "Graph C: Post-Implementation Resource Utilization",
        "Shows the design closes comfortably under the Phase 4 utilization gates.",
    )
    x0, y0 = 220, 322
    width = 1120
    rows = [
        ("LUT", _v(numbers, "ours_mxfp4_b32_lut_pct"), BLUE),
        ("DSP", _v(numbers, "ours_mxfp4_b32_dsp_pct"), AMBER),
        ("BRAM", _v(numbers, "ours_mxfp4_b32_bram_pct"), TEAL),
    ]
    draw.line((x0, y0 - 36, x0 + width, y0 - 36), fill=GRID, width=2)
    for pct in (0, 20, 40, 60, 80, 100):
        x = x0 + width * pct / 100
        draw.line((x, y0 - 54, x, y0 + 382), fill="#edf1f6", width=2 if pct == 80 else 1)
        _text(draw, (int(x), y0 - 84), f"{pct}%", size=19, color=RED if pct == 80 else MUTED, anchor="mm")
    _text(draw, (int(x0 + width * 0.8), y0 + 420), "80% gate", size=22, color=RED, bold=True, anchor="mm")
    for idx, (name, value, color) in enumerate(rows):
        y = y0 + idx * 130
        _text(draw, (102, y + 20), name, size=32, bold=True)
        draw.rounded_rectangle((x0, y, x0 + width, y + 58), radius=18, fill=SOFT)
        draw.rounded_rectangle((x0, y, x0 + width * value / 100, y + 58), radius=18, fill=color)
        _text(draw, (x0 + int(width * value / 100) + 24, y + 12), f"{_fmt(value, 2)}%", size=28, bold=True)
    _text(draw, (100, 910), f"Total on-chip power: {_fmt(_v(numbers, 'ours_mxfp4_b32_power_w'), 3)} W.", size=30, color=INK, bold=True)
    return _save(image, "graph_c_resource_utilization.png")


def design_pareto(sweep_rows: list[dict[str, str]]) -> Path:
    image, draw = _base(
        "Graph D: Design-Space Pareto Sweep",
        "Scatter view makes clear which measured configuration is the headline point.",
    )
    x0, y0, w, h = 210, 270, 1240, 620
    draw.line((x0, y0 + h, x0 + w, y0 + h), fill=GRID, width=3)
    draw.line((x0, y0, x0, y0 + h), fill=GRID, width=3)
    _text(draw, (x0 + w // 2, 950), "LUT utilization (%)", size=26, color=MUTED, anchor="mm")
    _text(draw, (84, y0 + h // 2), "Latency per token (log us)", size=25, color=MUTED)

    raw_points: list[dict[str, object]] = []
    for row in sweep_rows:
        raw_points.append(
            {
                "name": row["config"],
                "lut": float(row["lut_pct"]),
                "latency": float(row["latency_us"]),
                "power": float(row["power_w"]),
                "default": row["config"] == "ours_mxfp4_b32_pk16_pv8",
            }
        )
    if not raw_points:
        raw_points = [{"name": "default", "lut": 6.64, "latency": 51.472, "power": 8.976, "default": True}]
    grouped: dict[tuple[float, float], list[dict[str, object]]] = {}
    for point in raw_points:
        grouped.setdefault((round(float(point["lut"]), 2), round(float(point["latency"]), 3)), []).append(point)
    points: list[dict[str, object]] = []
    for group in grouped.values():
        names = [str(item["name"]) for item in group]
        points.append(
            {
                "name": "+".join(names),
                "lut": float(group[0]["lut"]),
                "latency": float(group[0]["latency"]),
                "power": max(float(item["power"]) for item in group),
                "default": any(bool(item["default"]) for item in group),
            }
        )
    max_lut = max(float(p["lut"]) for p in points) * 1.2
    min_latency = min(float(p["latency"]) for p in points) * 0.75
    max_latency = max(float(p["latency"]) for p in points) * 1.35
    min_log, max_log = math.log10(min_latency), math.log10(max_latency)

    for pct in (0, 5, 10, 20, 30):
        x = x0 + w * pct / max_lut
        if x <= x0 + w:
            draw.line((x, y0, x, y0 + h), fill="#edf1f6", width=1)
            _text(draw, (int(x), y0 + h + 28), f"{pct}", size=18, color=MUTED, anchor="mm")
    for tick in (50, 100, 1000, 10000):
        if min_latency <= tick <= max_latency:
            y = y0 + h - h * (math.log10(tick) - min_log) / (max_log - min_log)
            draw.line((x0 - 10, y, x0 + w, y), fill="#edf1f6", width=1)
            _text(draw, (x0 - 20, int(y)), f"{tick}", size=18, color=MUTED, anchor="rm")

    label_map = {
        "ours_mxfp4_b32_pk16_pv8": "default",
        "parallel_pk8_pv4_b32": "small",
        "parallel_pk32_pv16_b32": "wide B32",
        "block_b16_pk16_pv8": "B16",
        "block_b16_pk32_pv16": "wide B16",
        "block_b16_pk32_pv16+parallel_pk32_pv16_b32": "wide B16/B32",
        "parallel_pk32_pv16_b32+block_b16_pk32_pv16": "wide B16/B32",
    }
    for p in points:
        x = x0 + w * float(p["lut"]) / max_lut
        y = y0 + h - h * (math.log10(float(p["latency"])) - min_log) / (max_log - min_log)
        radius = 20 + min(float(p["power"]) * 1.6, 28)
        color = GREEN if p["default"] else PLUM
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=PAPER, width=3)
        _text(draw, (int(x + radius + 10), int(y - 10)), label_map.get(str(p["name"]), str(p["name"])), size=22, color=INK, bold=bool(p["default"]))
        _text(draw, (int(x + radius + 10), int(y + 18)), f"{_fmt(float(p['latency']), 1)} us", size=18, color=MUTED)
    _legend(draw, 1040, 230, [("default", GREEN), ("sweep point", PLUM)])
    return _save(image, "graph_d_design_pareto.png")


def accuracy(numbers: dict[str, dict[str, object]]) -> Path:
    image, draw = _base(
        "Graph E: Quantization Accuracy Boundary",
        "Useful synthetic evidence, with the real-Qwen caveat visible instead of hidden.",
    )
    labels = ["MXFP4 B32", "MXFP4 B16", "INT4 fallback"]
    values = [
        _v(numbers, "synthetic_mxfp4_b32_output_cosine"),
        _v(numbers, "synthetic_mxfp4_b16_output_cosine"),
        _v(numbers, "synthetic_int4_output_cosine"),
    ]
    lower = max(min(values) - 0.01, 0.0)
    _bar_chart(
        draw,
        box=(150, 260, 1210, 850),
        labels=labels,
        values=values,
        colors=[TEAL, BLUE, AMBER],
        unit="cos",
        lower=lower,
    )
    draw.rounded_rectangle((1260, 420, 1640, 620), radius=20, fill="#fff0f0", outline="#f0c8c8", width=2)
    _text(draw, (1290, 456), "Claim boundary", size=25, color=RED, bold=True)
    _text(draw, (1290, 502), f"Real Qwen status:", size=21, color=INK)
    _text(draw, (1290, 538), str(json.loads(NUMBERS.read_text(encoding="utf-8"))["qwen_capture_status"]["value"]), size=24, color=INK, bold=True)
    _text(draw, (1290, 584), "No PPL claim yet.", size=20, color=MUTED)
    return _save(image, "graph_e_accuracy_boundary.png")


def write_index(paths: Iterable[Path]) -> None:
    lines = [
        "# Graph Preview Images",
        "",
        "Generated from `paper/numbers.json` and `reports/benchmark/sweep.csv`.",
        "These are visual drafts for deciding the paper story before LaTeX integration.",
        "",
    ]
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        title = re.sub(r"[_-]+", " ", path.stem).title()
        lines.extend([f"## {title}", "", f"![{title}](../{rel})", ""])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    numbers = _load_numbers()
    sweep_rows = _read_sweep()
    paths = [
        latency_energy(numbers),
        speedup_energy_eff(numbers),
        resource_util(numbers),
        design_pareto(sweep_rows),
        accuracy(numbers),
    ]
    write_index(paths)
    print(f"Wrote {len(paths)} graph previews to {OUT_DIR.relative_to(ROOT)}")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

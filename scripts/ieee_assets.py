from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
NUMBERS = ROOT / "paper" / "numbers.json"
SWEEP_CSV = ROOT / "reports" / "benchmark" / "sweep.csv"
FIG_DIR = ROOT / "paper" / "ieee_figures"
TAB_DIR = ROOT / "paper" / "ieee_tables"
REPORT = ROOT / "reports" / "ieee_assets.md"

PT_PER_IN = 72.0
SINGLE_COL = (3.48 * PT_PER_IN, 2.35 * PT_PER_IN)
DOUBLE_COL = (7.16 * PT_PER_IN, 2.85 * PT_PER_IN)
PNG_SCALE = 4

BLACK = "#000000"
GRAY1 = "#333333"
GRAY2 = "#666666"
GRAY3 = "#999999"
GRID = "#d0d0d0"
LIGHT = "#f3f3f3"
WHITE = "#ffffff"


@dataclass(frozen=True)
class Series:
    label: str
    values: list[float]
    fill: str
    hatch: str = ""


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
    if value >= 1000:
        return f"{value:.0f}"
    if value >= 100:
        return f"{value:.1f}"
    if value >= 10:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _tex_escape(text: str) -> str:
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "$": r"\$",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def _pil_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    names = ["timesbd.ttf", "Times New Roman Bold.ttf", "DejaVuSerif-Bold.ttf"] if bold else [
        "times.ttf",
        "Times New Roman.ttf",
        "DejaVuSerif.ttf",
    ]
    roots = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")]
    for root in roots:
        for name in names:
            path = root / name
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def _rl_color(color: str):
    r, g, b = _hex_to_rgb(color)
    return colors.Color(r / 255.0, g / 255.0, b / 255.0)


def _hatch_pdf(c: canvas.Canvas, x: float, y: float, w: float, h: float, *, spacing: float = 5.0) -> None:
    c.saveState()
    c.setStrokeColor(_rl_color("#555555"))
    c.setLineWidth(0.35)
    cursor = x - h
    while cursor < x + w:
        c.line(cursor, y, cursor + h, y + h)
        cursor += spacing
    c.restoreState()


def _hatch_png(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, *, spacing: int = 18) -> None:
    cursor = x - h
    while cursor < x + w:
        draw.line((cursor, y + h, cursor + h, y), fill="#555555", width=2)
        cursor += spacing


class PdfPlot:
    def __init__(self, path: Path, size: tuple[float, float] = SINGLE_COL) -> None:
        self.path = path
        self.w, self.h = size
        self.c = canvas.Canvas(str(path), pagesize=size)
        self.c.setTitle(path.stem)

    def text(self, x: float, y: float, value: str, size: float = 7.0, *, bold: bool = False, anchor: str = "left") -> None:
        self.c.setFillColor(colors.black)
        self.c.setFont("Times-Bold" if bold else "Times-Roman", size)
        if anchor == "center":
            self.c.drawCentredString(x, y, value)
        elif anchor == "right":
            self.c.drawRightString(x, y, value)
        else:
            self.c.drawString(x, y, value)

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = BLACK, width: float = 0.45) -> None:
        self.c.setStrokeColor(_rl_color(color))
        self.c.setLineWidth(width)
        self.c.line(x1, y1, x2, y2)

    def rect(self, x: float, y: float, w: float, h: float, fill: str, *, hatch: bool = False) -> None:
        self.c.setFillColor(_rl_color(fill))
        self.c.setStrokeColor(colors.black)
        self.c.setLineWidth(0.35)
        self.c.rect(x, y, w, h, fill=1, stroke=1)
        if hatch:
            _hatch_pdf(self.c, x, y, w, h)

    def circle(self, x: float, y: float, r: float, fill: str, *, hatch: bool = False) -> None:
        self.c.setFillColor(_rl_color(fill))
        self.c.setStrokeColor(colors.black)
        self.c.setLineWidth(0.35)
        self.c.circle(x, y, r, fill=1, stroke=1)
        if hatch:
            _hatch_pdf(self.c, x - r, y - r, 2 * r, 2 * r)

    def save(self) -> None:
        self.c.showPage()
        self.c.save()


class PngPlot:
    def __init__(self, path: Path, size: tuple[float, float] = SINGLE_COL) -> None:
        self.path = path
        self.w = int(size[0] * PNG_SCALE)
        self.h = int(size[1] * PNG_SCALE)
        self.s = PNG_SCALE
        self.image = Image.new("RGB", (self.w, self.h), WHITE)
        self.draw = ImageDraw.Draw(self.image)

    def xy(self, x: float, y: float) -> tuple[int, int]:
        return int(x * self.s), int((self.h / self.s - y) * self.s)

    def text(self, x: float, y: float, value: str, size: float = 7.0, *, bold: bool = False, anchor: str = "la") -> None:
        font = _pil_font(max(int(size * self.s), 8), bold=bold)
        px, py = self.xy(x, y)
        pil_anchor = {"left": "la", "center": "ma", "right": "ra"}.get(anchor, anchor)
        self.draw.text((px, py), value, fill=BLACK, font=font, anchor=pil_anchor)

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = BLACK, width: float = 0.45) -> None:
        p1 = self.xy(x1, y1)
        p2 = self.xy(x2, y2)
        self.draw.line((p1, p2), fill=color, width=max(int(width * self.s), 1))

    def rect(self, x: float, y: float, w: float, h: float, fill: str, *, hatch: bool = False) -> None:
        p1 = self.xy(x, y + h)
        p2 = self.xy(x + w, y)
        self.draw.rectangle((p1, p2), fill=fill, outline=BLACK, width=max(self.s // 2, 1))
        if hatch:
            _hatch_png(self.draw, p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1])

    def circle(self, x: float, y: float, r: float, fill: str, *, hatch: bool = False) -> None:
        cx, cy = self.xy(x, y)
        rr = int(r * self.s)
        box = (cx - rr, cy - rr, cx + rr, cy + rr)
        self.draw.ellipse(box, fill=fill, outline=BLACK, width=max(self.s // 2, 1))
        if hatch:
            _hatch_png(self.draw, box[0], box[1], box[2] - box[0], box[3] - box[1])

    def save(self) -> None:
        self.image.save(self.path)


def _paired_plots(stem: str, size: tuple[float, float] = SINGLE_COL) -> tuple[PdfPlot, PngPlot]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    return PdfPlot(FIG_DIR / f"{stem}.pdf", size), PngPlot(FIG_DIR / f"{stem}.png", size)


def _draw_axes(plot, x: float, y: float, w: float, h: float, *, xlabel: str, ylabel: str, yticks: Sequence[float], y_to_px) -> None:
    plot.line(x, y, x + w, y, width=0.55)
    plot.line(x, y, x, y + h, width=0.55)
    for tick in yticks:
        yy = y_to_px(tick)
        plot.line(x - 2.5, yy, x + w, yy, color=GRID, width=0.25)
        plot.text(x - 4, yy - 2.2, _fmt(float(tick), 2), size=6.3, anchor="right")
    if xlabel:
        plot.text(x + w / 2, y - 18, xlabel, size=7.1, anchor="center")
    plot.text(x, y + h + 8, ylabel, size=7.1)


def _bar_figure(
    stem: str,
    *,
    labels: list[str],
    values: list[float],
    ylabel: str,
    unit: str,
    log: bool = False,
    lower: float = 0.0,
    size: tuple[float, float] = SINGLE_COL,
) -> list[Path]:
    pdf, png = _paired_plots(stem, size)
    plots = [pdf, png]
    fill = ["#222222", "#777777", "#e6e6e6", "#aaaaaa", "#f2f2f2"]
    for plot in plots:
        margin_l, margin_b = 36, 34
        chart_w, chart_h = size[0] - 52, size[1] - 56
        x0, y0 = margin_l, margin_b
        if log:
            min_v = max(min(values) * 0.65, 1e-4)
            max_v = max(values) * 1.25
            min_log, max_log = math.log10(min_v), math.log10(max_v)

            def y_for(v: float) -> float:
                return y0 + chart_h * (math.log10(max(v, min_v)) - min_log) / (max_log - min_log)

            ticks = [0.1, 1, 10, 100, 1000, 10000]
            yticks = [tick for tick in ticks if min_v <= tick <= max_v]
        else:
            max_v = max(values) * 1.18
            span = max(max_v - lower, 1e-9)

            def y_for(v: float) -> float:
                return y0 + chart_h * (v - lower) / span

            yticks = [lower + span * i / 4 for i in range(5)]
        _draw_axes(plot, x0, y0, chart_w, chart_h, xlabel="", ylabel=ylabel, yticks=yticks, y_to_px=y_for)
        slot = chart_w / len(values)
        bar_w = min(slot * 0.48, 24)
        for idx, (label, value) in enumerate(zip(labels, values)):
            cx = x0 + slot * (idx + 0.5)
            yy = y_for(value)
            plot.rect(cx - bar_w / 2, y0, bar_w, max(yy - y0, 0.01), fill[idx % len(fill)], hatch=False)
            plot.text(cx, y0 - 10, label, size=6.5, anchor="center")
            plot.text(cx, yy + 3, f"{_fmt(value, 3)} {unit}", size=6.2, bold=True, anchor="center")
        plot.save()
    return [FIG_DIR / f"{stem}.pdf", FIG_DIR / f"{stem}.png"]


def latency_energy(numbers: dict[str, dict[str, object]]) -> list[Path]:
    paths: list[Path] = []
    paths.extend(
        _bar_figure(
            "fig1_latency",
            labels=["H100", "USC", "Ours"],
            values=[_v(numbers, "h100_baseline_latency_us"), _v(numbers, "usc_baseline_latency_us"), _v(numbers, "ours_mxfp4_b32_latency_us")],
            ylabel="Latency (us/token)",
            unit="us",
        )
    )
    paths.extend(
        _bar_figure(
            "fig2_energy",
            labels=["H100", "USC", "Ours"],
            values=[_v(numbers, "h100_baseline_energy_mj"), _v(numbers, "usc_baseline_energy_mj"), _v(numbers, "ours_mxfp4_b32_energy_mj")],
            ylabel="Energy (mJ/token, log)",
            unit="mJ",
            log=True,
        )
    )
    return paths


def resource_util(numbers: dict[str, dict[str, object]]) -> list[Path]:
    return _bar_figure(
        "fig3_resource_util",
        labels=["LUT", "DSP", "BRAM"],
        values=[_v(numbers, "ours_mxfp4_b32_lut_pct"), _v(numbers, "ours_mxfp4_b32_dsp_pct"), _v(numbers, "ours_mxfp4_b32_bram_pct")],
        ylabel="Device utilization (%)",
        unit="%",
    )


def accuracy(numbers: dict[str, dict[str, object]]) -> list[Path]:
    values = [
        _v(numbers, "synthetic_mxfp4_b32_output_cosine"),
        _v(numbers, "synthetic_mxfp4_b16_output_cosine"),
        _v(numbers, "synthetic_int4_output_cosine"),
    ]
    return _bar_figure(
        "fig4_accuracy",
        labels=["MX B32", "MX B16", "INT4"],
        values=values,
        ylabel="Output cosine",
        unit="",
        lower=max(min(values) - 0.01, 0.0),
    )


def pareto(sweep_rows: list[dict[str, str]]) -> list[Path]:
    pdf, png = _paired_plots("fig5_design_pareto", DOUBLE_COL)
    plots = [pdf, png]
    points: list[dict[str, object]] = []
    for row in sweep_rows:
        points.append(
            {
                "name": row["config"],
                "lut": float(row["lut_pct"]),
                "latency": float(row["latency_us"]),
                "power": float(row["power_w"]),
                "default": row["config"] == "ours_mxfp4_b32_pk16_pv8",
            }
        )
    grouped: dict[tuple[float, float], list[dict[str, object]]] = {}
    for point in points:
        grouped.setdefault((round(float(point["lut"]), 2), round(float(point["latency"]), 3)), []).append(point)
    points = []
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
    if not points:
        points = [{"name": "default", "lut": 6.64, "latency": 51.472, "power": 8.976, "default": True}]

    max_lut = max(float(p["lut"]) for p in points) * 1.18
    min_lat = min(float(p["latency"]) for p in points) * 0.75
    max_lat = max(float(p["latency"]) for p in points) * 1.25
    min_log, max_log = math.log10(min_lat), math.log10(max_lat)
    label_map = {
        "ours_mxfp4_b32_pk16_pv8": "default",
        "parallel_pk8_pv4_b32": "small",
        "parallel_pk32_pv16_b32": "wide",
        "block_b16_pk16_pv8": "B16",
        "block_b16_pk32_pv16": "B16 wide",
        "block_b16_pk32_pv16+parallel_pk32_pv16_b32": "wide/B16",
        "parallel_pk32_pv16_b32+block_b16_pk32_pv16": "wide/B16",
    }

    for plot in plots:
        x0, y0, w, h = 48, 36, DOUBLE_COL[0] - 80, DOUBLE_COL[1] - 62

        def x_for(lut: float) -> float:
            return x0 + w * lut / max_lut

        def y_for(latency: float) -> float:
            return y0 + h * (math.log10(latency) - min_log) / (max_log - min_log)

        plot.line(x0, y0, x0 + w, y0, width=0.55)
        plot.line(x0, y0, x0, y0 + h, width=0.55)
        for pct in (0, 5, 10, 20, 30):
            xx = x_for(pct)
            if xx <= x0 + w:
                plot.line(xx, y0, xx, y0 + h, color=GRID, width=0.25)
                plot.text(xx, y0 - 10, str(pct), size=6.3, anchor="center")
        for tick in (50, 100, 1000, 10000):
            if min_lat <= tick <= max_lat:
                yy = y_for(tick)
                plot.line(x0, yy, x0 + w, yy, color=GRID, width=0.25)
                plot.text(x0 - 4, yy - 2, str(tick), size=6.3, anchor="right")
        plot.text(x0 + w / 2, 10, "LUT utilization (%)", size=7.1, anchor="center")
        plot.text(x0, y0 + h + 8, "Latency (us/token, log)", size=7.1)
        for point in points:
            x = x_for(float(point["lut"]))
            y = y_for(float(point["latency"]))
            r = 3.4 + min(float(point["power"]) * 0.35, 4.6)
            plot.circle(x, y, r, "#d9d9d9" if not point["default"] else "#555555", hatch=False)
            plot.text(x + r + 2, y + 1.5, label_map.get(str(point["name"]), str(point["name"])), size=6.4, bold=bool(point["default"]))
        plot.save()
    return [FIG_DIR / "fig5_design_pareto.pdf", FIG_DIR / "fig5_design_pareto.png"]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def tables(numbers: dict[str, dict[str, object]], sweep_rows: list[dict[str, str]]) -> list[Path]:
    TAB_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    main = rf"""% AUTO-GENERATED -- DO NOT EDIT BY HAND
\begin{{table}}[t]
\centering
\caption{{Batch-1 decode comparison. Latency and energy baselines are cited from prior work; MXFP4 values are measured post-implementation.}}
\label{{tab:main-ieee}}
\begin{{tabular}}{{llrrrrr}}
\toprule
System & Datapath / state & Lat. & Speedup & Energy & Eff. & Power \\
 &  & ($\mu$s) & vs. H100 & (mJ) & vs. H100 & (W) \\
\midrule
H100 PCIe GPU~\cite{{gupta_gdn}} & HBM state traffic & {_fmt(_v(numbers, 'h100_baseline_latency_us'), 1)} & 1.00$\times$ & {_fmt(_v(numbers, 'h100_baseline_energy_mj'), 1)} & 1.00$\times$ & {_fmt(_v(numbers, 'h100_baseline_power_w'), 0)} \\
USC FPGA~\cite{{gupta_gdn}} & persistent state & {_fmt(_v(numbers, 'usc_baseline_latency_us'), 1)} & {_fmt(_v(numbers, 'h100_baseline_latency_us') / _v(numbers, 'usc_baseline_latency_us'), 2)}$\times$ & {_fmt(_v(numbers, 'usc_baseline_energy_mj'), 1)} & {_fmt(_v(numbers, 'h100_baseline_energy_mj') / _v(numbers, 'usc_baseline_energy_mj'), 2)}$\times$ & $\le${_fmt(_v(numbers, 'usc_baseline_power_w'), 0)} \\
Ours & MXFP4 persistent state & {_fmt(_v(numbers, 'ours_mxfp4_b32_latency_us'), 3)} & {_fmt(_v(numbers, 'headline_speedup_vs_h100'), 2)}$\times$ & {_fmt(_v(numbers, 'ours_mxfp4_b32_energy_mj'), 3)} & {_fmt(_v(numbers, 'headline_energy_efficiency_vs_h100'), 1)}$\times$ & {_fmt(_v(numbers, 'ours_mxfp4_b32_power_w'), 3)} \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
    path = TAB_DIR / "tab1_main_results.tex"
    _write(path, main)
    paths.append(path)

    hardware = rf"""% AUTO-GENERATED -- DO NOT EDIT BY HAND
\begin{{table}}[t]
\centering
\caption{{Measured default MXFP4 implementation results.}}
\label{{tab:evidence-ieee}}
\begin{{tabular}}{{lr}}
\toprule
Metric & Measured result \\
\midrule
C-sim parity & {int(_v(numbers, 'hls_csim_vectors_passed'))}/{int(_v(numbers, 'hls_csim_vectors_total'))} vectors \\
C/RTL cosim length & {int(_v(numbers, 'ours_mxfp4_b32_tokens_cosim'))} tokens \\
HLS estimated Fmax & {_fmt(_v(numbers, 'ours_mxfp4_b32_csynth_fmax_mhz'), 2)} MHz \\
HLS latency & {int(_v(numbers, 'ours_mxfp4_b32_csynth_latency_cycles'))} cycles \\
Post-implementation WNS & {_fmt(_v(numbers, 'ours_mxfp4_b32_impl_wns_ns'), 3)} ns \\
LUT utilization & {_fmt(_v(numbers, 'ours_mxfp4_b32_lut_pct'), 2)}\% \\
DSP utilization & {_fmt(_v(numbers, 'ours_mxfp4_b32_dsp_pct'), 2)}\% \\
BRAM utilization & {_fmt(_v(numbers, 'ours_mxfp4_b32_bram_pct'), 2)}\% \\
On-chip power & {_fmt(_v(numbers, 'ours_mxfp4_b32_power_w'), 3)} W \\
Qwen capture status & {_tex_escape(str(numbers['qwen_capture_status']['value']))} \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
    path = TAB_DIR / "tab2_implementation_evidence.tex"
    _write(path, hardware)
    paths.append(path)

    sweep_lines = [
        "% AUTO-GENERATED -- DO NOT EDIT BY HAND",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Measured MXFP4 design-space sweep. This table replaces the earlier Pareto-style Figure~5.}",
        r"\label{tab:sweep-ieee}",
        r"\begin{tabular}{lrrrrrrrr}",
        r"\toprule",
        r"Configuration & $B$ & $P_K$ & $P_V$ & Tokens & Lat. & Power & LUT & DSP \\",
        r" &  &  &  &  & ($\mu$s) & (W) & (\%) & (\%) \\",
        r"\midrule",
    ]
    label_map = {
        "ours_mxfp4_b32_pk16_pv8": "default",
        "parallel_pk8_pv4_b32": "small fabric",
        "parallel_pk32_pv16_b32": "wide fabric",
        "block_b16_pk16_pv8": "B16 default parallelism",
        "block_b16_pk32_pv16": "B16 wide fabric",
    }
    for row in sweep_rows:
        sweep_lines.append(
            f"{_tex_escape(label_map.get(row['config'], row['config']))} & {row['block_size']} & {row['p_k']} & {row['p_v']} & {row['tokens']} & {float(row['latency_us']):.3f} & {float(row['power_w']):.3f} & {float(row['lut_pct']):.2f} & {float(row['dsp_pct']):.2f} \\\\"
        )
    sweep_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""])
    path = TAB_DIR / "tab3_design_sweep.tex"
    _write(path, "\n".join(sweep_lines))
    paths.append(path)

    accuracy_tex = rf"""% AUTO-GENERATED -- DO NOT EDIT BY HAND
\begin{{table}}[t]
\centering
\caption{{Synthetic quantization fidelity and claim boundary.}}
\label{{tab:accuracy-ieee}}
\begin{{tabular}}{{llrr}}
\toprule
Configuration & State & Output cosine & Output rel. $L_2$ \\
\midrule
MXFP4 B=32 & MXFP4 B=16 & {_fmt(_v(numbers, 'synthetic_mxfp4_b32_output_cosine'), 6)} & {_fmt(_v(numbers, 'synthetic_mxfp4_b32_output_rel_l2'), 6)} \\
MXFP4 B=16 & MXFP4 B=16 & {_fmt(_v(numbers, 'synthetic_mxfp4_b16_output_cosine'), 6)} & {_fmt(_v(numbers, 'synthetic_mxfp4_b16_output_rel_l2'), 6)} \\
INT4 fallback & INT4 & {_fmt(_v(numbers, 'synthetic_int4_output_cosine'), 6)} & -- \\
Real Qwen3-Next & capture required & \multicolumn{{2}}{{c}}{{{_tex_escape(str(numbers['qwen_capture_status']['value']))}}} \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
    path = TAB_DIR / "tab4_accuracy.tex"
    _write(path, accuracy_tex)
    paths.append(path)
    return paths


def table_pngs(table_paths: Iterable[Path]) -> list[Path]:
    paths: list[Path] = []
    for table_path in table_paths:
        text = table_path.read_text(encoding="utf-8")
        rows = [line for line in text.splitlines() if "&" in line and r"\\" in line]
        clean_rows = []
        for row in rows:
            row = row.replace(r"\\", "")
            row = row.replace(r"$\mu$", "u").replace(r"\%", "%")
            row = row.replace(r"\le", "<=").replace(r"\times", "x").replace("$", "")
            row = row.replace(r"\_", "_").replace("~", " ")
            row = row.replace(r"\textbf", "")
            row = row.replace("{", "").replace("}", "")
            cells = [cell.strip() for cell in row.split("&")]
            cells = [__import__("re").sub(r"\\cite[^ ]*", "", cell).strip() for cell in cells]
            clean_rows.append(cells)
        if not clean_rows:
            continue
        cols = max(len(row) for row in clean_rows)
        cell_w = [420] + [245] * (cols - 1)
        width = sum(cell_w) + 80
        row_h = 58
        height = 80 + row_h * len(clean_rows)
        image = Image.new("RGB", (width, height), WHITE)
        draw = ImageDraw.Draw(image)
        font = _pil_font(22)
        bold_font = _pil_font(22, bold=True)
        y = 34
        draw.line((36, y - 12, width - 36, y - 12), fill=BLACK, width=3)
        for r, row in enumerate(clean_rows):
            x = 40
            if r == 0:
                draw.line((36, y + row_h - 8, width - 36, y + row_h - 8), fill=BLACK, width=2)
            for c, cell in enumerate(row):
                draw.text((x, y), cell, fill=BLACK, font=bold_font if r == 0 else font)
                x += cell_w[c]
            y += row_h
        draw.line((36, y - 8, width - 36, y - 8), fill=BLACK, width=3)
        png = table_path.with_suffix(".png")
        image.save(png)
        paths.append(png)
    return paths


def write_index(paths: Iterable[Path]) -> None:
    lines = [
        "# IEEE-Style Assets",
        "",
        "Generated publication-style figures and tables. Figures are vector PDFs with PNG previews.",
        "Tables are booktabs-style LaTeX with PNG previews for quick inspection.",
        "",
    ]
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        lines.append(f"- `{rel}`")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    numbers = _load_numbers()
    sweep_rows = _read_sweep()
    paths: list[Path] = []
    paths.extend(latency_energy(numbers))
    paths.extend(resource_util(numbers))
    paths.extend(accuracy(numbers))
    table_paths = tables(numbers, sweep_rows)
    paths.extend(table_paths)
    paths.extend(table_pngs(table_paths))
    write_index(paths)
    print(f"Wrote IEEE-style assets to {FIG_DIR.relative_to(ROOT)} and {TAB_DIR.relative_to(ROOT)}")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

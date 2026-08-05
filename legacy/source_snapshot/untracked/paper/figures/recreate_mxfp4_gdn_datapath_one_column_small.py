from __future__ import annotations

import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "paper" / "figures"
SVG_PATH = FIGURES / "mxfp4_gdn_datapath_one_column_small.svg"
PNG_PATH = FIGURES / "mxfp4_gdn_datapath_one_column_small.png"
WIDTH = 720
HEIGHT = 940


COLORS = {
    "bg": "#f8fafc",
    "ink": "#111827",
    "tiny": "#334155",
    "rule": "#cbd5e1",
    "input_fill": "#eaf3ff",
    "input_stroke": "#1d4e89",
    "compute_fill": "#ffffff",
    "compute_stroke": "#475569",
    "state_fill": "#fff4d6",
    "state_stroke": "#a16207",
    "math_fill": "#ecfdf3",
    "math_stroke": "#15803d",
    "result_fill": "#f1f5f9",
    "result_stroke": "#334155",
    "arrow": "#475569",
}


def _font(name: str, size: int) -> ImageFont.ImageFont:
    fonts = {
        "regular": Path("C:/Windows/Fonts/arial.ttf"),
        "bold": Path("C:/Windows/Fonts/arialbd.ttf"),
    }
    try:
        return ImageFont.truetype(str(fonts[name]), size=size)
    except OSError:
        return ImageFont.load_default()


FONT_SECTION = _font("bold", 24)
FONT_LABEL = _font("bold", 25)
FONT_TINY = _font("regular", 18)


def _text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    color: str = COLORS["ink"],
    anchor: str = "mm",
) -> None:
    draw.text((x, y), text, font=font, fill=color, anchor=anchor)


def _box(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: str,
    outline: str,
    width: int = 4,
    radius: int = 14,
) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill, outline=outline, width=width)


def _arrow(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int) -> None:
    color = COLORS["arrow"]
    dx = x2 - x1
    dy = y2 - y1
    distance = math.hypot(dx, dy)
    if distance == 0:
        return
    ux = dx / distance
    uy = dy / distance
    head_len = 14
    head_w = 8
    shaft_end = (x2 - ux * head_len, y2 - uy * head_len)
    draw.line((x1, y1, shaft_end[0], shaft_end[1]), fill=color, width=5)
    points = [
        (x2, y2),
        (shaft_end[0] - uy * head_w, shaft_end[1] + ux * head_w),
        (shaft_end[0] + uy * head_w, shaft_end[1] - ux * head_w),
    ]
    draw.polygon(points, fill=color)


def write_png(path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
    draw = ImageDraw.Draw(image)

    x = 80
    w = 560
    cx = WIDTH // 2

    _text(draw, cx, 32, "Token-level datapath", FONT_SECTION)

    _box(draw, x, 54, w, 66, COLORS["input_fill"], COLORS["input_stroke"])
    _text(draw, cx, 82, "Token inputs", FONT_LABEL)
    _text(draw, cx, 108, "q, k, v, beta, gate", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 126, cx, 152)
    _box(draw, x, 158, w, 66, COLORS["input_fill"], COLORS["input_stroke"])
    _text(draw, cx, 186, "MXFP4 pack", FONT_LABEL)
    _text(draw, cx, 212, "E2M1 elements + E8M0 block scales", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 230, cx, 256)
    _box(draw, x, 262, w, 122, COLORS["compute_fill"], COLORS["compute_stroke"])
    _text(draw, cx, 291, "Stateful GDN compute", FONT_LABEL)
    _text(draw, cx, 323, "predict r = S k", FONT_TINY, COLORS["tiny"])
    _text(draw, cx, 347, "update S with beta e k^T", FONT_TINY, COLORS["tiny"])
    _text(draw, cx, 371, "gate output", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 390, cx, 414)
    _box(draw, 132, 420, 456, 58, COLORS["state_fill"], COLORS["state_stroke"])
    _text(draw, cx, 444, "On-chip state", FONT_LABEL)
    _text(draw, cx, 469, "MXFP4 state in BRAM/URAM", FONT_TINY, COLORS["tiny"])

    _arrow(draw, 226, 419, 226, 394)
    _arrow(draw, 494, 394, 494, 419)

    _arrow(draw, cx, 484, cx, 510)
    _box(draw, x, 516, w, 66, COLORS["result_fill"], COLORS["result_stroke"])
    _text(draw, cx, 544, "Packed output", FONT_LABEL)
    _text(draw, cx, 570, "FP16 boundary value", FONT_TINY, COLORS["tiny"])

    draw.line((58, 620, 662, 620), fill=COLORS["rule"], width=3)
    _text(draw, cx, 658, "Native MXFP4 arithmetic path", FONT_SECTION)

    _box(draw, x, 686, w, 58, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, cx, 709, "E2M1 LUT multiply", FONT_LABEL)
    _text(draw, cx, 733, "sign XOR, exponent add, mantissa multiply", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 750, cx, 772)
    _box(draw, x, 778, w, 58, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, cx, 801, "Block-scale alignment", FONT_LABEL)
    _text(draw, cx, 825, "combine E8M0 scales, shift partials", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 842, cx, 864)
    _box(draw, x, 870, w, 58, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, cx, 893, "Fixed-point accumulation", FONT_LABEL)
    _text(draw, cx, 917, "Q4.3 partials into INT24", FONT_TINY, COLORS["tiny"])

    image.save(path)


def _svg_text(x: int, y: int, text: str, cls: str, anchor: str = "middle") -> str:
    return f'  <text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{html.escape(text)}</text>'


def _svg_box(x: int, y: int, w: int, h: int, cls: str) -> str:
    return f'  <rect class="box {cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>'


def write_svg(path: Path) -> None:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <defs>
    <style>
      .bg {{ fill: {COLORS["bg"]}; }}
      .section {{ font: 700 24px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .label {{ font: 700 25px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .tiny {{ font: 400 18px Arial, sans-serif; fill: {COLORS["tiny"]}; }}
      .box {{ rx: 14; ry: 14; stroke-width: 4; }}
      .input {{ fill: {COLORS["input_fill"]}; stroke: {COLORS["input_stroke"]}; }}
      .compute {{ fill: {COLORS["compute_fill"]}; stroke: {COLORS["compute_stroke"]}; }}
      .state {{ fill: {COLORS["state_fill"]}; stroke: {COLORS["state_stroke"]}; }}
      .math {{ fill: {COLORS["math_fill"]}; stroke: {COLORS["math_stroke"]}; }}
      .result {{ fill: {COLORS["result_fill"]}; stroke: {COLORS["result_stroke"]}; }}
      .rule {{ stroke: {COLORS["rule"]}; stroke-width: 3; }}
      .arrow {{ stroke: {COLORS["arrow"]}; stroke-width: 5; fill: none; marker-end: url(#arrow); stroke-linecap: round; }}
    </style>
    <marker id="arrow" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="12" markerHeight="12" orient="auto">
      <path d="M 0 0 L 12 6 L 0 12 z" fill="{COLORS["arrow"]}"/>
    </marker>
  </defs>

  <rect class="bg" x="0" y="0" width="{WIDTH}" height="{HEIGHT}"/>
{_svg_text(360, 32, "Token-level datapath", "section")}
{_svg_box(80, 54, 560, 66, "input")}
{_svg_text(360, 82, "Token inputs", "label")}
{_svg_text(360, 108, "q, k, v, beta, gate", "tiny")}
  <path class="arrow" d="M 360 126 L 360 152"/>

{_svg_box(80, 158, 560, 66, "input")}
{_svg_text(360, 186, "MXFP4 pack", "label")}
{_svg_text(360, 212, "E2M1 elements + E8M0 block scales", "tiny")}
  <path class="arrow" d="M 360 230 L 360 256"/>

{_svg_box(80, 262, 560, 122, "compute")}
{_svg_text(360, 291, "Stateful GDN compute", "label")}
{_svg_text(360, 323, "predict r = S k", "tiny")}
{_svg_text(360, 347, "update S with beta e k^T", "tiny")}
{_svg_text(360, 371, "gate output", "tiny")}
  <path class="arrow" d="M 360 390 L 360 414"/>

{_svg_box(132, 420, 456, 58, "state")}
{_svg_text(360, 444, "On-chip state", "label")}
{_svg_text(360, 469, "MXFP4 state in BRAM/URAM", "tiny")}
  <path class="arrow" d="M 226 419 L 226 394"/>
  <path class="arrow" d="M 494 394 L 494 419"/>
  <path class="arrow" d="M 360 484 L 360 510"/>

{_svg_box(80, 516, 560, 66, "result")}
{_svg_text(360, 544, "Packed output", "label")}
{_svg_text(360, 570, "FP16 boundary value", "tiny")}

  <line class="rule" x1="58" y1="620" x2="662" y2="620"/>
{_svg_text(360, 658, "Native MXFP4 arithmetic path", "section")}
{_svg_box(80, 686, 560, 58, "math")}
{_svg_text(360, 709, "E2M1 LUT multiply", "label")}
{_svg_text(360, 733, "sign XOR, exponent add, mantissa multiply", "tiny")}
  <path class="arrow" d="M 360 750 L 360 772"/>

{_svg_box(80, 778, 560, 58, "math")}
{_svg_text(360, 801, "Block-scale alignment", "label")}
{_svg_text(360, 825, "combine E8M0 scales, shift partials", "tiny")}
  <path class="arrow" d="M 360 842 L 360 864"/>

{_svg_box(80, 870, 560, 58, "math")}
{_svg_text(360, 893, "Fixed-point accumulation", "label")}
{_svg_text(360, 917, "Q4.3 partials into INT24", "tiny")}
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    write_png(PNG_PATH)
    write_svg(SVG_PATH)
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {SVG_PATH}")


if __name__ == "__main__":
    main()

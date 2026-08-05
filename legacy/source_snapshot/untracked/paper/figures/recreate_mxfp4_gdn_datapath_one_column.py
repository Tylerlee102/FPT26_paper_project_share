from __future__ import annotations

import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "paper" / "figures"
SVG_PATH = FIGURES / "mxfp4_gdn_datapath_one_column.svg"
PNG_PATH = FIGURES / "mxfp4_gdn_datapath_one_column.png"
WIDTH = 720
HEIGHT = 1190


COLORS = {
    "bg": "#f8fafc",
    "ink": "#111827",
    "small": "#1f2937",
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


FONT_SECTION = _font("bold", 26)
FONT_LABEL = _font("bold", 27)
FONT_SMALL = _font("regular", 22)
FONT_TINY = _font("regular", 19)


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
    radius: int = 16,
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
    head_len = 16
    head_w = 9
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

    _text(draw, cx, 42, "Token-level datapath", FONT_SECTION)

    _box(draw, x, 78, w, 84, COLORS["input_fill"], COLORS["input_stroke"])
    _text(draw, cx, 110, "Token inputs", FONT_LABEL)
    _text(draw, cx, 141, "q_t, k_t, v_t, beta, gate", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 168, cx, 205)
    _box(draw, x, 212, w, 84, COLORS["input_fill"], COLORS["input_stroke"])
    _text(draw, cx, 244, "MXFP4 pack", FONT_LABEL)
    _text(draw, cx, 275, "E2M1 elements + E8M0 block scales", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 302, cx, 340)
    _box(draw, x, 348, w, 142, COLORS["compute_fill"], COLORS["compute_stroke"])
    _text(draw, cx, 382, "Stateful GDN compute", FONT_LABEL)
    _text(draw, cx, 420, "predict r = S k", FONT_TINY, COLORS["tiny"])
    _text(draw, cx, 449, "update S with beta e k^T", FONT_TINY, COLORS["tiny"])
    _text(draw, cx, 478, "output S q, then gate", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 498, cx, 535)
    _box(draw, 130, 548, 460, 76, COLORS["state_fill"], COLORS["state_stroke"])
    _text(draw, cx, 578, "On-chip state", FONT_LABEL)
    _text(draw, cx, 606, "MXFP4 S_t in BRAM/URAM", FONT_TINY, COLORS["tiny"])

    _arrow(draw, 230, 547, 230, 505)
    _arrow(draw, 490, 505, 490, 547)

    _arrow(draw, cx, 632, cx, 668)
    _box(draw, x, 678, w, 84, COLORS["result_fill"], COLORS["result_stroke"])
    _text(draw, cx, 710, "Packed output", FONT_LABEL)
    _text(draw, cx, 741, "FP16 boundary value", FONT_TINY, COLORS["tiny"])

    draw.line((58, 808, 662, 808), fill=COLORS["rule"], width=3)
    _text(draw, cx, 848, "Native MXFP4 arithmetic path", FONT_SECTION)

    _box(draw, x, 880, w, 70, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, cx, 907, "E2M1 LUT multiply", FONT_LABEL)
    _text(draw, cx, 932, "sign XOR, exponent add, mantissa multiply", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 956, cx, 982)
    _box(draw, x, 990, w, 70, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, cx, 1017, "Block-scale alignment", FONT_LABEL)
    _text(draw, cx, 1042, "combine E8M0 scales, shift partials", FONT_TINY, COLORS["tiny"])

    _arrow(draw, cx, 1066, cx, 1092)
    _box(draw, x, 1100, w, 70, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, cx, 1127, "Fixed-point accumulation", FONT_LABEL)
    _text(draw, cx, 1152, "Q4.3 partials into INT24", FONT_TINY, COLORS["tiny"])

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
      .section {{ font: 700 26px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .label {{ font: 700 27px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .tiny {{ font: 400 19px Arial, sans-serif; fill: {COLORS["tiny"]}; }}
      .box {{ rx: 16; ry: 16; stroke-width: 4; }}
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
{_svg_text(360, 42, "Token-level datapath", "section")}
{_svg_box(80, 78, 560, 84, "input")}
{_svg_text(360, 110, "Token inputs", "label")}
{_svg_text(360, 141, "q_t, k_t, v_t, beta, gate", "tiny")}
  <path class="arrow" d="M 360 168 L 360 205"/>

{_svg_box(80, 212, 560, 84, "input")}
{_svg_text(360, 244, "MXFP4 pack", "label")}
{_svg_text(360, 275, "E2M1 elements + E8M0 block scales", "tiny")}
  <path class="arrow" d="M 360 302 L 360 340"/>

{_svg_box(80, 348, 560, 142, "compute")}
{_svg_text(360, 382, "Stateful GDN compute", "label")}
{_svg_text(360, 420, "predict r = S k", "tiny")}
{_svg_text(360, 449, "update S with beta e k^T", "tiny")}
{_svg_text(360, 478, "output S q, then gate", "tiny")}
  <path class="arrow" d="M 360 498 L 360 535"/>

{_svg_box(130, 548, 460, 76, "state")}
{_svg_text(360, 578, "On-chip state", "label")}
{_svg_text(360, 606, "MXFP4 S_t in BRAM/URAM", "tiny")}
  <path class="arrow" d="M 230 547 L 230 505"/>
  <path class="arrow" d="M 490 505 L 490 547"/>
  <path class="arrow" d="M 360 632 L 360 668"/>

{_svg_box(80, 678, 560, 84, "result")}
{_svg_text(360, 710, "Packed output", "label")}
{_svg_text(360, 741, "FP16 boundary value", "tiny")}

  <line class="rule" x1="58" y1="808" x2="662" y2="808"/>
{_svg_text(360, 848, "Native MXFP4 arithmetic path", "section")}
{_svg_box(80, 880, 560, 70, "math")}
{_svg_text(360, 907, "E2M1 LUT multiply", "label")}
{_svg_text(360, 932, "sign XOR, exponent add, mantissa multiply", "tiny")}
  <path class="arrow" d="M 360 956 L 360 982"/>

{_svg_box(80, 990, 560, 70, "math")}
{_svg_text(360, 1017, "Block-scale alignment", "label")}
{_svg_text(360, 1042, "combine E8M0 scales, shift partials", "tiny")}
  <path class="arrow" d="M 360 1066 L 360 1092"/>

{_svg_box(80, 1100, 560, 70, "math")}
{_svg_text(360, 1127, "Fixed-point accumulation", "label")}
{_svg_text(360, 1152, "Q4.3 partials into INT24", "tiny")}
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

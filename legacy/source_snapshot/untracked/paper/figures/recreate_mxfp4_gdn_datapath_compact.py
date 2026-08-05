from __future__ import annotations

import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "paper" / "figures"
SVG_PATH = FIGURES / "mxfp4_gdn_datapath_compact.svg"
PNG_PATH = FIGURES / "mxfp4_gdn_datapath_compact.png"
WIDTH = 1000
HEIGHT = 320


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


FONT_SECTION = _font("bold", 18)
FONT_LABEL = _font("bold", 18)
FONT_SMALL = _font("regular", 14)
FONT_TINY = _font("regular", 12)


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
    width: int = 3,
    radius: int = 9,
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
    head_len = 8
    head_w = 5
    shaft_end = (x2 - ux * head_len, y2 - uy * head_len)
    draw.line((x1, y1, shaft_end[0], shaft_end[1]), fill=color, width=3)
    points = [
        (x2, y2),
        (shaft_end[0] - uy * head_w, shaft_end[1] + ux * head_w),
        (shaft_end[0] + uy * head_w, shaft_end[1] - ux * head_w),
    ]
    draw.polygon(points, fill=color)


def write_png(path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
    draw = ImageDraw.Draw(image)

    _text(draw, 36, 27, "Token-level persistent-state datapath", FONT_SECTION, anchor="lm")
    draw.line((36, 196, 964, 196), fill=COLORS["rule"], width=2)
    _text(draw, 36, 224, "Native MXFP4 arithmetic path reused inside compute", FONT_SECTION, anchor="lm")

    _box(draw, 45, 57, 135, 72, COLORS["input_fill"], COLORS["input_stroke"])
    _text(draw, 112, 86, "Token inputs", FONT_LABEL)
    _text(draw, 112, 109, "q_t, k_t, v_t, beta, gate", FONT_TINY, COLORS["tiny"])

    _box(draw, 235, 57, 150, 72, COLORS["input_fill"], COLORS["input_stroke"])
    _text(draw, 310, 85, "MXFP4 pack", FONT_LABEL)
    _text(draw, 310, 108, "E2M1 + E8M0 blocks", FONT_TINY, COLORS["tiny"])

    _box(draw, 445, 43, 270, 100, COLORS["compute_fill"], COLORS["compute_stroke"])
    _text(draw, 580, 70, "Stateful GDN compute", FONT_LABEL)
    _text(draw, 580, 95, "predict r_t = S k_t", FONT_TINY, COLORS["tiny"])
    _text(draw, 580, 113, "update S_t = S - beta_t e_t k_t^T", FONT_TINY, COLORS["tiny"])
    _text(draw, 580, 131, "output o_t = S_t q_t, then gate", FONT_TINY, COLORS["tiny"])

    _box(draw, 798, 57, 150, 72, COLORS["result_fill"], COLORS["result_stroke"])
    _text(draw, 873, 86, "Packed output", FONT_LABEL)
    _text(draw, 873, 109, "FP16 boundary value", FONT_TINY, COLORS["tiny"])

    _box(draw, 485, 154, 190, 42, COLORS["state_fill"], COLORS["state_stroke"])
    _text(draw, 580, 171, "On-chip state", FONT_LABEL)
    _text(draw, 580, 189, "MXFP4 S_t in BRAM/URAM", FONT_TINY, COLORS["tiny"])

    _arrow(draw, 185, 93, 228, 93)
    _arrow(draw, 392, 93, 437, 93)
    _arrow(draw, 722, 93, 790, 93)
    _arrow(draw, 552, 147, 552, 153)
    _arrow(draw, 608, 153, 608, 148)

    _box(draw, 65, 250, 240, 52, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, 185, 272, "E2M1 LUT multiply", FONT_LABEL)
    _text(draw, 185, 292, "sign XOR, exponent add, mantissa multiply", FONT_TINY, COLORS["tiny"])

    _box(draw, 385, 250, 240, 52, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, 505, 272, "Block-scale alignment", FONT_LABEL)
    _text(draw, 505, 292, "combine E8M0 scales, shift partials", FONT_TINY, COLORS["tiny"])

    _box(draw, 705, 250, 240, 52, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, 825, 272, "Fixed-point accumulation", FONT_LABEL)
    _text(draw, 825, 292, "Q4.3 partials into INT24", FONT_TINY, COLORS["tiny"])

    _arrow(draw, 312, 276, 377, 276)
    _arrow(draw, 632, 276, 697, 276)

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
      .section {{ font: 700 18px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .label {{ font: 700 18px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .tiny {{ font: 400 12px Arial, sans-serif; fill: {COLORS["tiny"]}; }}
      .box {{ rx: 9; ry: 9; stroke-width: 3; }}
      .input {{ fill: {COLORS["input_fill"]}; stroke: {COLORS["input_stroke"]}; }}
      .compute {{ fill: {COLORS["compute_fill"]}; stroke: {COLORS["compute_stroke"]}; }}
      .state {{ fill: {COLORS["state_fill"]}; stroke: {COLORS["state_stroke"]}; }}
      .math {{ fill: {COLORS["math_fill"]}; stroke: {COLORS["math_stroke"]}; }}
      .result {{ fill: {COLORS["result_fill"]}; stroke: {COLORS["result_stroke"]}; }}
      .rule {{ stroke: {COLORS["rule"]}; stroke-width: 2; }}
      .arrow {{ stroke: {COLORS["arrow"]}; stroke-width: 3; fill: none; marker-end: url(#arrow); stroke-linecap: round; }}
    </style>
    <marker id="arrow" viewBox="0 0 9 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M 0 0 L 9 5 L 0 10 z" fill="{COLORS["arrow"]}"/>
    </marker>
  </defs>

  <rect class="bg" x="0" y="0" width="{WIDTH}" height="{HEIGHT}"/>
{_svg_text(36, 27, "Token-level persistent-state datapath", "section", "start")}
  <line class="rule" x1="36" y1="196" x2="964" y2="196"/>
{_svg_text(36, 224, "Native MXFP4 arithmetic path reused inside compute", "section", "start")}

{_svg_box(45, 57, 135, 72, "input")}
{_svg_text(112, 86, "Token inputs", "label")}
{_svg_text(112, 109, "q_t, k_t, v_t, beta, gate", "tiny")}

{_svg_box(235, 57, 150, 72, "input")}
{_svg_text(310, 85, "MXFP4 pack", "label")}
{_svg_text(310, 108, "E2M1 + E8M0 blocks", "tiny")}

{_svg_box(445, 43, 270, 100, "compute")}
{_svg_text(580, 70, "Stateful GDN compute", "label")}
{_svg_text(580, 95, "predict r_t = S k_t", "tiny")}
{_svg_text(580, 113, "update S_t = S - beta_t e_t k_t^T", "tiny")}
{_svg_text(580, 131, "output o_t = S_t q_t, then gate", "tiny")}

{_svg_box(798, 57, 150, 72, "result")}
{_svg_text(873, 86, "Packed output", "label")}
{_svg_text(873, 109, "FP16 boundary value", "tiny")}

{_svg_box(485, 154, 190, 42, "state")}
{_svg_text(580, 171, "On-chip state", "label")}
{_svg_text(580, 189, "MXFP4 S_t in BRAM/URAM", "tiny")}

  <path class="arrow" d="M 185 93 L 228 93"/>
  <path class="arrow" d="M 392 93 L 437 93"/>
  <path class="arrow" d="M 722 93 L 790 93"/>
  <path class="arrow" d="M 552 147 L 552 153"/>
  <path class="arrow" d="M 608 153 L 608 148"/>

{_svg_box(65, 250, 240, 52, "math")}
{_svg_text(185, 272, "E2M1 LUT multiply", "label")}
{_svg_text(185, 292, "sign XOR, exponent add, mantissa multiply", "tiny")}

{_svg_box(385, 250, 240, 52, "math")}
{_svg_text(505, 272, "Block-scale alignment", "label")}
{_svg_text(505, 292, "combine E8M0 scales, shift partials", "tiny")}

{_svg_box(705, 250, 240, 52, "math")}
{_svg_text(825, 272, "Fixed-point accumulation", "label")}
{_svg_text(825, 292, "Q4.3 partials into INT24", "tiny")}

  <path class="arrow" d="M 312 276 L 377 276"/>
  <path class="arrow" d="M 632 276 L 697 276"/>
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

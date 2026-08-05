from __future__ import annotations

import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "paper" / "figures"
SVG_PATH = FIGURES / "mxfp4_gdn_datapath_ieee_compact.svg"
PNG_PATH = FIGURES / "mxfp4_gdn_datapath_ieee_compact.png"
WIDTH = 720
HEIGHT = 560


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


FONT_SECTION = _font("bold", 22)
FONT_LABEL = _font("bold", 22)
FONT_TINY = _font("regular", 16)


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
    radius: int = 11,
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
    head_len = 12
    head_w = 7
    shaft_end = (x2 - ux * head_len, y2 - uy * head_len)
    draw.line((x1, y1, shaft_end[0], shaft_end[1]), fill=color, width=4)
    points = [
        (x2, y2),
        (shaft_end[0] - uy * head_w, shaft_end[1] + ux * head_w),
        (shaft_end[0] + uy * head_w, shaft_end[1] - ux * head_w),
    ]
    draw.polygon(points, fill=color)


def write_png(path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
    draw = ImageDraw.Draw(image)

    left_x = 42
    left_w = 312
    left_c = left_x + left_w // 2
    right_x = 394
    right_w = 284
    right_c = right_x + right_w // 2

    _text(draw, left_c, 32, "Token datapath", FONT_SECTION)
    _text(draw, right_c, 32, "MXFP4 arithmetic", FONT_SECTION)
    draw.line((374, 56, 374, 520), fill=COLORS["rule"], width=2)

    _box(draw, left_x, 58, left_w, 58, COLORS["input_fill"], COLORS["input_stroke"])
    _text(draw, left_c, 82, "Token inputs", FONT_LABEL)
    _text(draw, left_c, 104, "q, k, v, beta, gate", FONT_TINY, COLORS["tiny"])

    _arrow(draw, left_c, 122, left_c, 146)
    _box(draw, left_x, 152, left_w, 58, COLORS["input_fill"], COLORS["input_stroke"])
    _text(draw, left_c, 176, "MXFP4 pack", FONT_LABEL)
    _text(draw, left_c, 198, "E2M1 + E8M0 blocks", FONT_TINY, COLORS["tiny"])

    _arrow(draw, left_c, 216, left_c, 240)
    _box(draw, left_x, 246, left_w, 84, COLORS["compute_fill"], COLORS["compute_stroke"])
    _text(draw, left_c, 270, "GDN compute", FONT_LABEL)
    _text(draw, left_c, 294, "predict, update state", FONT_TINY, COLORS["tiny"])
    _text(draw, left_c, 316, "gate output", FONT_TINY, COLORS["tiny"])

    _arrow(draw, left_x + left_w - 58, 336, left_x + left_w - 58, 452)
    _box(draw, left_x, 366, 210, 56, COLORS["state_fill"], COLORS["state_stroke"])
    _text(draw, left_x + 105, 389, "On-chip state", FONT_LABEL)
    _text(draw, left_x + 105, 411, "MXFP4 BRAM/URAM", FONT_TINY, COLORS["tiny"])

    _box(draw, left_x, 458, left_w, 58, COLORS["result_fill"], COLORS["result_stroke"])
    _text(draw, left_c, 482, "Packed output", FONT_LABEL)
    _text(draw, left_c, 504, "FP16 boundary value", FONT_TINY, COLORS["tiny"])

    _arrow(draw, left_x + 70, 365, left_x + 70, 334)
    _arrow(draw, left_x + 155, 334, left_x + 155, 365)

    _box(draw, right_x, 92, right_w, 64, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, right_c, 117, "E2M1 LUT", FONT_LABEL)
    _text(draw, right_c, 141, "sign XOR, exp add, mantissa", FONT_TINY, COLORS["tiny"])

    _arrow(draw, right_c, 164, right_c, 206)
    _box(draw, right_x, 214, right_w, 64, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, right_c, 239, "Block scale", FONT_LABEL)
    _text(draw, right_c, 263, "align E8M0 partials", FONT_TINY, COLORS["tiny"])

    _arrow(draw, right_c, 286, right_c, 328)
    _box(draw, right_x, 336, right_w, 64, COLORS["math_fill"], COLORS["math_stroke"])
    _text(draw, right_c, 361, "INT24 accum.", FONT_LABEL)
    _text(draw, right_c, 385, "Q4.3 fixed partials", FONT_TINY, COLORS["tiny"])

    _arrow(draw, right_c, 408, right_c, 450)
    _box(draw, right_x, 458, right_w, 58, COLORS["result_fill"], COLORS["result_stroke"])
    _text(draw, right_c, 482, "FP16 output", FONT_LABEL)
    _text(draw, right_c, 504, "FP16 boundary", FONT_TINY, COLORS["tiny"])

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
      .section {{ font: 700 22px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .label {{ font: 700 22px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .tiny {{ font: 400 16px Arial, sans-serif; fill: {COLORS["tiny"]}; }}
      .box {{ rx: 11; ry: 11; stroke-width: 3; }}
      .input {{ fill: {COLORS["input_fill"]}; stroke: {COLORS["input_stroke"]}; }}
      .compute {{ fill: {COLORS["compute_fill"]}; stroke: {COLORS["compute_stroke"]}; }}
      .state {{ fill: {COLORS["state_fill"]}; stroke: {COLORS["state_stroke"]}; }}
      .math {{ fill: {COLORS["math_fill"]}; stroke: {COLORS["math_stroke"]}; }}
      .result {{ fill: {COLORS["result_fill"]}; stroke: {COLORS["result_stroke"]}; }}
      .rule {{ stroke: {COLORS["rule"]}; stroke-width: 2; }}
      .arrow {{ stroke: {COLORS["arrow"]}; stroke-width: 4; fill: none; marker-end: url(#arrow); stroke-linecap: round; }}
    </style>
    <marker id="arrow" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10" orient="auto">
      <path d="M 0 0 L 12 6 L 0 12 z" fill="{COLORS["arrow"]}"/>
    </marker>
  </defs>
  <rect class="bg" x="0" y="0" width="{WIDTH}" height="{HEIGHT}"/>
{_svg_text(198, 32, "Token datapath", "section")}
{_svg_text(536, 32, "MXFP4 arithmetic", "section")}
  <line class="rule" x1="374" y1="56" x2="374" y2="520"/>

{_svg_box(42, 58, 312, 58, "input")}
{_svg_text(198, 82, "Token inputs", "label")}
{_svg_text(198, 104, "q, k, v, beta, gate", "tiny")}
  <path class="arrow" d="M 198 122 L 198 146"/>
{_svg_box(42, 152, 312, 58, "input")}
{_svg_text(198, 176, "MXFP4 pack", "label")}
{_svg_text(198, 198, "E2M1 + E8M0 blocks", "tiny")}
  <path class="arrow" d="M 198 216 L 198 240"/>
{_svg_box(42, 246, 312, 84, "compute")}
{_svg_text(198, 270, "GDN compute", "label")}
{_svg_text(198, 294, "predict, update state", "tiny")}
{_svg_text(198, 316, "gate output", "tiny")}
  <path class="arrow" d="M 296 336 L 296 452"/>
{_svg_box(42, 366, 210, 56, "state")}
{_svg_text(147, 389, "On-chip state", "label")}
{_svg_text(147, 411, "MXFP4 BRAM/URAM", "tiny")}
{_svg_box(42, 458, 312, 58, "result")}
{_svg_text(198, 482, "Packed output", "label")}
{_svg_text(198, 504, "FP16 boundary value", "tiny")}
  <path class="arrow" d="M 112 365 L 112 334"/>
  <path class="arrow" d="M 197 334 L 197 365"/>

{_svg_box(394, 92, 284, 64, "math")}
{_svg_text(536, 117, "E2M1 LUT", "label")}
{_svg_text(536, 141, "sign XOR, exp add, mantissa", "tiny")}
  <path class="arrow" d="M 536 164 L 536 206"/>
{_svg_box(394, 214, 284, 64, "math")}
{_svg_text(536, 239, "Block scale", "label")}
{_svg_text(536, 263, "align E8M0 partials", "tiny")}
  <path class="arrow" d="M 536 286 L 536 328"/>
{_svg_box(394, 336, 284, 64, "math")}
{_svg_text(536, 361, "INT24 accum.", "label")}
{_svg_text(536, 385, "Q4.3 fixed partials", "tiny")}
  <path class="arrow" d="M 536 408 L 536 450"/>
{_svg_box(394, 458, 284, 58, "result")}
{_svg_text(536, 482, "FP16 output", "label")}
{_svg_text(536, 504, "FP16 boundary", "tiny")}
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

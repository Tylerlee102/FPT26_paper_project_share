from __future__ import annotations

import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "paper" / "figures"
SVG_PATH = FIGURES / "mxfp4_gdn_datapath_paper_fit.svg"
PNG_PATH = FIGURES / "mxfp4_gdn_datapath_paper_fit.png"
WIDTH = 1000
HEIGHT = 500


COLORS = {
    "bg": "#f7f9fb",
    "ink": "#111827",
    "small": "#1f2937",
    "tiny": "#334155",
    "soft": "#cbd5e1",
    "input_fill": "#eaf3ff",
    "input_stroke": "#1d4e89",
    "phase_fill": "#ffffff",
    "phase_stroke": "#475569",
    "state_fill": "#fff4d6",
    "state_stroke": "#a16207",
    "math_fill": "#ecfdf3",
    "math_stroke": "#15803d",
    "result_fill": "#f1f5f9",
    "result_stroke": "#334155",
    "arrow": "#475569",
}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    fonts = {
        "regular": Path("C:/Windows/Fonts/arial.ttf"),
        "bold": Path("C:/Windows/Fonts/arialbd.ttf"),
    }
    try:
        return ImageFont.truetype(str(fonts[name]), size=size)
    except OSError:
        return ImageFont.load_default()


FONT_TITLE = _font("bold", 27)
FONT_SECTION = _font("bold", 19)
FONT_LABEL = _font("bold", 17)
FONT_SMALL = _font("regular", 14)
FONT_TINY = _font("regular", 12)
FONT_SUB = _font("regular", 10)


def _text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    color: str = COLORS["ink"],
    anchor: str = "ls",
) -> None:
    draw.text((x, y), text, font=font, fill=color, anchor=anchor)


def _runs(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    runs: list[tuple[str, str]],
    font: ImageFont.ImageFont = FONT_SMALL,
    color: str = COLORS["small"],
    anchor_center: bool = False,
) -> None:
    widths: list[float] = []
    for text, mode in runs:
        widths.append(draw.textlength(text, font=FONT_SUB if mode in {"sub", "super"} else font))
    cursor = x - sum(widths) / 2 if anchor_center else float(x)
    for (text, mode), width in zip(runs, widths):
        if mode == "sub":
            draw.text((cursor, y + 4), text, font=FONT_SUB, fill=color, anchor="ls")
        elif mode == "super":
            draw.text((cursor, y - 7), text, font=FONT_SUB, fill=color, anchor="ls")
        else:
            draw.text((cursor, y), text, font=font, fill=color, anchor="ls")
        cursor += width


def _rect(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    fill: str | None,
    outline: str,
    width: int = 2,
    radius: int = 10,
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

    _text(draw, 34, 40, "Native MXFP4 Persistent-State Gated DeltaNet Decode Datapath", FONT_TITLE)

    _rect(draw, 28, 58, 944, 258, None, COLORS["soft"], width=2, radius=16)
    _text(draw, 48, 91, "Token-level datapath", FONT_SECTION)

    _rect(draw, 60, 125, 145, 88, COLORS["input_fill"], COLORS["input_stroke"], width=3, radius=9)
    _text(draw, 133, 154, "Token inputs", FONT_LABEL, anchor="mm")
    _runs(draw, 133, 185, [("q", ""), ("t", "sub"), (", k", ""), ("t", "sub"), (", v", ""), ("t", "sub")], anchor_center=True)
    _runs(draw, 133, 204, [("beta", ""), ("t", "sub"), (", gate", "")], anchor_center=True)

    _rect(draw, 245, 125, 155, 88, COLORS["input_fill"], COLORS["input_stroke"], width=3, radius=9)
    _text(draw, 323, 154, "MXFP4 pack", FONT_LABEL, anchor="mm")
    _text(draw, 323, 185, "E2M1 elements", FONT_SMALL, COLORS["small"], anchor="mm")
    _text(draw, 323, 204, "E8M0 block scale", FONT_SMALL, COLORS["small"], anchor="mm")

    _rect(draw, 440, 108, 292, 118, COLORS["phase_fill"], COLORS["phase_stroke"], width=3, radius=9)
    _text(draw, 586, 136, "Stateful GDN compute", FONT_LABEL, anchor="mm")
    _runs(draw, 586, 166, [("predict: r", ""), ("t", "sub"), (" = S", ""), ("t-1", "sub"), (" k", ""), ("t", "sub")], anchor_center=True)
    _runs(
        draw,
        586,
        187,
        [
            ("update: S", ""),
            ("t", "sub"),
            (" = S", ""),
            ("t-1", "sub"),
            (" - beta", ""),
            ("t", "sub"),
            (" e", ""),
            ("t", "sub"),
            (" k", ""),
            ("t", "sub"),
            ("T", "super"),
        ],
        anchor_center=True,
    )
    _runs(draw, 586, 208, [("output: o", ""), ("t", "sub"), (" = S", ""), ("t", "sub"), (" q", ""), ("t", "sub"), (", then gate", "")], anchor_center=True)

    _rect(draw, 500, 253, 195, 54, COLORS["state_fill"], COLORS["state_stroke"], width=3, radius=9)
    _text(draw, 598, 274, "On-chip state", FONT_LABEL, anchor="mm")
    _runs(draw, 598, 297, [("MXFP4 S", ""), ("t", "sub"), (" in BRAM/URAM", "")], anchor_center=True)

    _rect(draw, 770, 125, 170, 88, COLORS["result_fill"], COLORS["result_stroke"], width=3, radius=9)
    _text(draw, 855, 154, "Packed output", FONT_LABEL, anchor="mm")
    _text(draw, 855, 185, "FP16 boundary", FONT_SMALL, COLORS["small"], anchor="mm")
    _text(draw, 855, 204, "value", FONT_SMALL, COLORS["small"], anchor="mm")

    _arrow(draw, 213, 169, 237, 169)
    _arrow(draw, 408, 169, 432, 169)
    _arrow(draw, 740, 169, 762, 169)
    _arrow(draw, 563, 229, 563, 246)
    _arrow(draw, 620, 250, 620, 233)

    _rect(draw, 28, 342, 944, 128, None, COLORS["soft"], width=2, radius=16)
    _text(draw, 48, 374, "Native MXFP4 arithmetic reused by the compute block", FONT_SECTION)

    _rect(draw, 65, 400, 250, 55, COLORS["math_fill"], COLORS["math_stroke"], width=3, radius=9)
    _text(draw, 190, 423, "E2M1 LUT multiply", FONT_LABEL, anchor="mm")
    _text(draw, 190, 444, "sign XOR, exponent add, mantissa multiply", FONT_TINY, COLORS["tiny"], anchor="mm")

    _rect(draw, 375, 400, 250, 55, COLORS["math_fill"], COLORS["math_stroke"], width=3, radius=9)
    _text(draw, 500, 423, "Block-scale alignment", FONT_LABEL, anchor="mm")
    _text(draw, 500, 444, "combine E8M0 scales, shift partials", FONT_TINY, COLORS["tiny"], anchor="mm")

    _rect(draw, 685, 400, 255, 55, COLORS["math_fill"], COLORS["math_stroke"], width=3, radius=9)
    _text(draw, 813, 423, "Fixed-point accumulation", FONT_LABEL, anchor="mm")
    _text(draw, 813, 444, "Q4.3 partials into INT24 accumulator", FONT_TINY, COLORS["tiny"], anchor="mm")

    _arrow(draw, 323, 428, 367, 428)
    _arrow(draw, 633, 428, 677, 428)

    image.save(path)


def _svg_text(x: int, y: int, text: str, cls: str, anchor: str = "start") -> str:
    return f'  <text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{html.escape(text)}</text>'


def _svg_runs(x: int, y: int, runs: list[tuple[str, str]], cls: str = "small", anchor: str = "middle") -> str:
    parts = [f'  <text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">']
    for text, mode in runs:
        if mode == "sub":
            parts.append(f'<tspan baseline-shift="sub" font-size="10">{html.escape(text)}</tspan>')
        elif mode == "super":
            parts.append(f'<tspan baseline-shift="super" font-size="10">{html.escape(text)}</tspan>')
        else:
            parts.append(html.escape(text))
    parts.append("</text>")
    return "".join(parts)


def _svg_box(x: int, y: int, w: int, h: int, cls: str) -> str:
    return f'  <rect class="box {cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>'


def write_svg(path: Path) -> None:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <defs>
    <style>
      .bg {{ fill: {COLORS["bg"]}; }}
      .title {{ font: 700 27px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .section {{ font: 700 19px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .label {{ font: 700 17px Arial, sans-serif; fill: {COLORS["ink"]}; }}
      .small {{ font: 400 14px Arial, sans-serif; fill: {COLORS["small"]}; }}
      .tiny {{ font: 400 12px Arial, sans-serif; fill: {COLORS["tiny"]}; }}
      .box {{ rx: 10; ry: 10; stroke-width: 3; }}
      .input {{ fill: {COLORS["input_fill"]}; stroke: {COLORS["input_stroke"]}; }}
      .phase {{ fill: {COLORS["phase_fill"]}; stroke: {COLORS["phase_stroke"]}; }}
      .state {{ fill: {COLORS["state_fill"]}; stroke: {COLORS["state_stroke"]}; }}
      .math {{ fill: {COLORS["math_fill"]}; stroke: {COLORS["math_stroke"]}; }}
      .result {{ fill: {COLORS["result_fill"]}; stroke: {COLORS["result_stroke"]}; }}
      .soft {{ fill: none; stroke: {COLORS["soft"]}; stroke-width: 2; }}
      .arrow {{ stroke: {COLORS["arrow"]}; stroke-width: 3; fill: none; marker-end: url(#arrow); stroke-linecap: round; }}
    </style>
    <marker id="arrow" viewBox="0 0 9 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M 0 0 L 9 5 L 0 10 z" fill="{COLORS["arrow"]}"/>
    </marker>
  </defs>

  <rect class="bg" x="0" y="0" width="{WIDTH}" height="{HEIGHT}"/>
{_svg_text(34, 40, "Native MXFP4 Persistent-State Gated DeltaNet Decode Datapath", "title")}

  <rect class="soft" x="28" y="58" width="944" height="258" rx="16"/>
{_svg_text(48, 91, "Token-level datapath", "section")}
{_svg_box(60, 125, 145, 88, "input")}
{_svg_text(133, 154, "Token inputs", "label", "middle")}
{_svg_runs(133, 185, [("q", ""), ("t", "sub"), (", k", ""), ("t", "sub"), (", v", ""), ("t", "sub")])}
{_svg_runs(133, 204, [("beta", ""), ("t", "sub"), (", gate", "")])}
{_svg_box(245, 125, 155, 88, "input")}
{_svg_text(323, 154, "MXFP4 pack", "label", "middle")}
{_svg_text(323, 185, "E2M1 elements", "small", "middle")}
{_svg_text(323, 204, "E8M0 block scale", "small", "middle")}
{_svg_box(440, 108, 292, 118, "phase")}
{_svg_text(586, 136, "Stateful GDN compute", "label", "middle")}
{_svg_runs(586, 166, [("predict: r", ""), ("t", "sub"), (" = S", ""), ("t-1", "sub"), (" k", ""), ("t", "sub")])}
{_svg_runs(586, 187, [("update: S", ""), ("t", "sub"), (" = S", ""), ("t-1", "sub"), (" - beta", ""), ("t", "sub"), (" e", ""), ("t", "sub"), (" k", ""), ("t", "sub"), ("T", "super")])}
{_svg_runs(586, 208, [("output: o", ""), ("t", "sub"), (" = S", ""), ("t", "sub"), (" q", ""), ("t", "sub"), (", then gate", "")])}
{_svg_box(500, 253, 195, 54, "state")}
{_svg_text(598, 274, "On-chip state", "label", "middle")}
{_svg_runs(598, 297, [("MXFP4 S", ""), ("t", "sub"), (" in BRAM/URAM", "")])}
{_svg_box(770, 125, 170, 88, "result")}
{_svg_text(855, 154, "Packed output", "label", "middle")}
{_svg_text(855, 185, "FP16 boundary", "small", "middle")}
{_svg_text(855, 204, "value", "small", "middle")}
  <path class="arrow" d="M 213 169 L 237 169"/>
  <path class="arrow" d="M 408 169 L 432 169"/>
  <path class="arrow" d="M 740 169 L 762 169"/>
  <path class="arrow" d="M 563 229 L 563 246"/>
  <path class="arrow" d="M 620 250 L 620 233"/>

  <rect class="soft" x="28" y="342" width="944" height="128" rx="16"/>
{_svg_text(48, 374, "Native MXFP4 arithmetic reused by the compute block", "section")}
{_svg_box(65, 400, 250, 55, "math")}
{_svg_text(190, 423, "E2M1 LUT multiply", "label", "middle")}
{_svg_text(190, 444, "sign XOR, exponent add, mantissa multiply", "tiny", "middle")}
{_svg_box(375, 400, 250, 55, "math")}
{_svg_text(500, 423, "Block-scale alignment", "label", "middle")}
{_svg_text(500, 444, "combine E8M0 scales, shift partials", "tiny", "middle")}
{_svg_box(685, 400, 255, 55, "math")}
{_svg_text(813, 423, "Fixed-point accumulation", "label", "middle")}
{_svg_text(813, 444, "Q4.3 partials into INT24 accumulator", "tiny", "middle")}
  <path class="arrow" d="M 323 428 L 367 428"/>
  <path class="arrow" d="M 633 428 L 677 428"/>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    write_svg(SVG_PATH)
    write_png(PNG_PATH)
    print(SVG_PATH)
    print(PNG_PATH)


if __name__ == "__main__":
    main()

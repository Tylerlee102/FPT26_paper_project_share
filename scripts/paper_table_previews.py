from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from .paper_pack import require_release_gate


ROOT = Path(__file__).resolve().parents[1]
NUMBERS = ROOT / "paper" / "numbers.json"
SWEEP_CSV = ROOT / "reports" / "benchmark" / "sweep.csv"
OUT_DIR = ROOT / "paper" / "table_previews"
REPORT = ROOT / "reports" / "table_previews.md"


INK = "#15202b"
MUTED = "#5b6673"
GRID = "#d8dee8"
PAPER = "#ffffff"
SOFT = "#f4f7fb"
NAVY = "#1f3a5f"
TEAL = "#137c72"
GREEN = "#2d7d46"
AMBER = "#b86b18"
RED = "#b43d3d"
PLUM = "#5d4a7d"
BLUE_SOFT = "#e8f0fb"
TEAL_SOFT = "#e8f6f4"
GREEN_SOFT = "#eaf6ee"
AMBER_SOFT = "#fff3df"
RED_SOFT = "#fff0f0"
PLUM_SOFT = "#f1edf8"


@dataclass(frozen=True)
class CellStyle:
    fill: str = PAPER
    color: str = INK
    bold: bool = False
    align: str = "left"


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


def _v(numbers: dict[str, dict[str, object]], key: str) -> object:
    return numbers[key]["value"]


def _fmt_float(value: object, digits: int = 2) -> str:
    number = float(value)
    if digits == 0:
        return f"{number:.0f}"
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    text = str(text)
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    line = words[0]
    for word in words[1:]:
        candidate = f"{line} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    size: int = 28,
    color: str = INK,
    bold: bool = False,
    max_width: int | None = None,
    line_gap: int = 6,
    anchor: str | None = None,
) -> int:
    font = _font(size, bold=bold)
    if max_width is None:
        draw.text(xy, str(text), fill=color, font=font, anchor=anchor)
        bbox = draw.textbbox(xy, str(text), font=font, anchor=anchor)
        return bbox[3] - bbox[1]
    y = xy[1]
    height = 0
    for line in _wrap(draw, str(text), font, max_width):
        draw.text((xy[0], y), line, fill=color, font=font)
        bbox = draw.textbbox((xy[0], y), line, font=font)
        line_h = bbox[3] - bbox[1]
        y += line_h + line_gap
        height += line_h + line_gap
    return max(height - line_gap, 0)


def _card(draw: ImageDraw.ImageDraw, xyxy: tuple[int, int, int, int], *, fill: str = PAPER, outline: str = GRID) -> None:
    draw.rounded_rectangle(xyxy, radius=22, fill=fill, outline=outline, width=2)


def _badge(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, *, fill: str, color: str = PAPER) -> int:
    font = _font(22, bold=True)
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + 28
    draw.rounded_rectangle((x, y, x + width, y + 34), radius=17, fill=fill)
    draw.text((x + 14, y + 5), text, fill=color, font=font)
    return width


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


def _draw_table(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    widths: list[int],
    headers: list[str],
    rows: list[list[str]],
    row_styles: list[list[CellStyle]] | None = None,
    row_height: int = 88,
    header_height: int = 58,
) -> int:
    table_w = sum(widths)
    draw.rounded_rectangle((x, y, x + table_w, y + header_height), radius=16, fill=NAVY)
    cursor = x
    for width, header in zip(widths, headers):
        _text(draw, (cursor + 18, y + 16), header, size=22, color=PAPER, bold=True, max_width=width - 30)
        cursor += width
    y += header_height
    for row_idx, row in enumerate(rows):
        cursor = x
        default_fill = SOFT if row_idx % 2 == 0 else PAPER
        for col_idx, (width, value) in enumerate(zip(widths, row)):
            style = row_styles[row_idx][col_idx] if row_styles else CellStyle(fill=default_fill)
            fill = style.fill if style.fill != PAPER or row_idx % 2 != 0 else default_fill
            draw.rectangle((cursor, y, cursor + width, y + row_height), fill=fill)
            font_size = 22 if col_idx else 21
            text_x = cursor + 18
            max_width = width - 32
            if style.align == "right":
                font = _font(font_size, bold=style.bold)
                lines = _wrap(draw, value, font, max_width)
                line_y = y + 18
                for line in lines[:3]:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    draw.text((cursor + width - 18 - (bbox[2] - bbox[0]), line_y), line, fill=style.color, font=font)
                    line_y += 28
            else:
                _text(
                    draw,
                    (text_x, y + 16),
                    value,
                    size=font_size,
                    color=style.color,
                    bold=style.bold,
                    max_width=max_width,
                    line_gap=5,
                )
            cursor += width
        draw.line((x, y + row_height, x + table_w, y + row_height), fill=GRID, width=1)
        y += row_height
    draw.rounded_rectangle((x, y - len(rows) * row_height - header_height, x + table_w, y), radius=16, outline=GRID, width=2)
    return y


def main_claim(numbers: dict[str, dict[str, object]]) -> Path:
    image, draw = _base(
        "Table Concept A: Main Result Story",
        "Use this as the first results table: problem, baseline, measured win, and caveat in one place.",
    )
    rows = [
        [
            "H100 PCIe GPU baseline",
            "Batch-1 GPU decode is limited by recurrent-state HBM traffic.",
            f"{_fmt_float(_v(numbers, 'h100_baseline_latency_us'), 1)} us",
            f"{_fmt_float(_v(numbers, 'h100_baseline_power_w'), 0)} W TDP",
            "External cited baseline",
        ],
        [
            "USC persistent-state FPGA",
            "Keeps GDN state on chip to remove state round trips.",
            f"{_fmt_float(_v(numbers, 'usc_baseline_latency_us'), 1)} us",
            f"<= {_fmt_float(_v(numbers, 'usc_baseline_power_w'), 0)} W",
            "Architecture baseline",
        ],
        [
            "Ours: native MXFP4 GDN FPGA",
            "Adds block-scaled FP4 datapath and LUT-based E2M1 MAC fabric.",
            f"{_fmt_float(_v(numbers, 'ours_mxfp4_b32_latency_us'), 3)} us",
            f"{_fmt_float(_v(numbers, 'ours_mxfp4_b32_power_w'), 3)} W",
            f"{_fmt_float(_v(numbers, 'headline_speedup_vs_h100'), 3)}x vs H100 latency",
        ],
    ]
    styles = []
    for idx, row in enumerate(rows):
        fill = GREEN_SOFT if idx == 2 else SOFT if idx == 0 else PAPER
        styles.append([CellStyle(fill=fill, bold=(idx == 2 if c == 0 else False)) for c, _ in enumerate(row)])
    _draw_table(
        draw,
        x=86,
        y=238,
        widths=[300, 530, 190, 190, 360],
        headers=["System", "What it demonstrates", "Latency", "Power", "Paper claim"],
        rows=rows,
        row_styles=styles,
        row_height=146,
    )
    _card(draw, (86, 758, 1660, 1000), fill="#fbfcff")
    _badge(draw, (118, 794), "Headline", fill=GREEN)
    _text(
        draw,
        (118, 846),
        "Your table should not only say we are faster. It should say why: persistent state removes HBM transfer, and MXFP4 reduces datapath/memory cost.",
        size=30,
        color=INK,
        max_width=1420,
    )
    _text(
        draw,
        (118, 930),
        f"Current status: hardware numbers are measured; Qwen realistic capture is {_v(numbers, 'qwen_capture_status')}.",
        size=25,
        color=RED,
        bold=True,
        max_width=1400,
    )
    return _save(image, "table_a_main_result_story.png")


def source_synthesis() -> Path:
    image, draw = _base(
        "Table Concept B: How This Paper Combines the Two Prior Papers",
        "This table makes the novelty obvious instead of making the reader infer it.",
    )
    rows = [
        [
            "Persistent-state GDN FPGA paper",
            "Linear-attention decode is memory-bound at batch 1.",
            "Keep fixed recurrent state on FPGA BRAM and stream token inputs.",
            "Adopt persistent-state dataflow for Gated DeltaNet decode.",
        ],
        [
            "4-bit CNN LUT multiplier paper",
            "DSPs are scarce for low-bit neural arithmetic.",
            "Replace numerical 4-bit multiply with compact LUT logic.",
            "Adapt the idea to native E2M1/MXFP4 multiply instead of CNN INT4.",
        ],
        [
            "Your proposed paper",
            "Can GDN decode be both state-persistent and native low precision?",
            "MXFP4 block scales + LUT FP4 MAC + FPGA persistent state.",
            "Measure latency, timing, area, power, and quantization fidelity.",
        ],
    ]
    styles = []
    for idx, row in enumerate(rows):
        fill = GREEN_SOFT if idx == 2 else BLUE_SOFT if idx == 0 else AMBER_SOFT
        styles.append([CellStyle(fill=fill, bold=(idx == 2 and c == 0)) for c, _ in enumerate(row)])
    _draw_table(
        draw,
        x=86,
        y=236,
        widths=[360, 410, 410, 390],
        headers=["Source", "Question it answers", "Mechanism", "What your paper adds"],
        rows=rows,
        row_styles=styles,
        row_height=188,
    )
    _card(draw, (86, 870, 1660, 1000), fill="#fbfcff")
    _text(
        draw,
        (118, 905),
        "Research framing: not just combining papers, but testing whether native MXFP4 changes the dataflow accelerator's area/energy/accuracy tradeoff.",
        size=30,
        bold=True,
        color=INK,
        max_width=1450,
    )
    return _save(image, "table_b_source_synthesis.png")


def hardware_evidence(numbers: dict[str, dict[str, object]]) -> Path:
    image, draw = _base(
        "Table Concept C: Hardware Evidence Checklist",
        "A reviewer-friendly table that separates measured passes from the remaining data caveat.",
    )
    rows = [
        ["C-sim parity", f"{_v(numbers, 'hls_csim_vectors_passed')}/{_v(numbers, 'hls_csim_vectors_total')} vectors", "Pass", "Bit-exact software/HLS path"],
        [
            "C/RTL cosim",
            f"{int(_v(numbers, 'ours_mxfp4_b32_tokens_cosim'))} tokens",
            "Pass",
            "Authoritative RTL parity for default config",
        ],
        ["HLS synthesis", f"{_fmt_float(_v(numbers, 'ours_mxfp4_b32_csynth_fmax_mhz'), 2)} MHz", "Pass", "Above 200 MHz gate"],
        ["Vivado timing", f"{_fmt_float(_v(numbers, 'ours_mxfp4_b32_impl_wns_ns'), 3)} ns WNS", "Pass", "Post-implementation timing closed"],
        ["Vivado resource", f"LUT {_fmt_float(_v(numbers, 'ours_mxfp4_b32_lut_pct'), 2)}%, BRAM {_fmt_float(_v(numbers, 'ours_mxfp4_b32_bram_pct'), 2)}%", "Pass", "Below 80% gate"],
        ["Power", f"{_fmt_float(_v(numbers, 'ours_mxfp4_b32_power_w'), 3)} W", "Pass", "Under 10 W target"],
        ["Real Qwen capture", str(_v(numbers, "qwen_capture_status")), "Open", "Needs valid Qwen3-Next activation NPZ"],
    ]
    styles = []
    for row in rows:
        status = row[2]
        fill = RED_SOFT if status == "Open" else GREEN_SOFT
        styles.append(
            [
                CellStyle(fill=fill, bold=True),
                CellStyle(fill=fill, align="right", bold=True),
                CellStyle(fill=fill, color=RED if status == "Open" else GREEN, bold=True),
                CellStyle(fill=fill),
            ]
        )
    _draw_table(
        draw,
        x=86,
        y=230,
        widths=[360, 320, 160, 730],
        headers=["Evidence item", "Measured value", "Status", "Why it matters"],
        rows=rows,
        row_styles=styles,
        row_height=92,
    )
    return _save(image, "table_c_hardware_evidence.png")


def sweep_table(sweep_rows: list[dict[str, str]]) -> Path:
    image, draw = _base(
        "Table Concept D: Design-Space Sweep",
        "This version makes the default design choice defensible instead of listing raw configurations.",
    )
    labels = {
        "ours_mxfp4_b32_pk16_pv8": "Default: B32 Pk16 Pv8",
        "parallel_pk8_pv4_b32": "Small fabric: B32 Pk8 Pv4",
        "parallel_pk32_pv16_b32": "Wide fabric: B32 Pk32 Pv16",
        "block_b16_pk16_pv8": "B16 same parallelism",
        "block_b16_pk32_pv16": "B16 wide fabric",
    }
    rows: list[list[str]] = []
    for row in sweep_rows:
        rows.append(
            [
                labels.get(row["config"], row["config"]),
                f"{row['tokens']} token(s)",
                f"{float(row['latency_us']):.3f} us",
                f"{float(row['power_w']):.3f} W",
                f"{float(row['lut_pct']):.2f}%",
                "Best current measured point" if row["config"] == "ours_mxfp4_b32_pk16_pv8" else "Measured but not headline",
            ]
        )
    if not rows:
        rows = [["Default", "--", "--", "--", "--", "sweep.csv missing"]]
    styles = []
    for row in sweep_rows:
        fill = GREEN_SOFT if row["config"] == "ours_mxfp4_b32_pk16_pv8" else SOFT
        styles.append([CellStyle(fill=fill, bold=(row["config"] == "ours_mxfp4_b32_pk16_pv8" and c == 0)) for c in range(6)])
    _draw_table(
        draw,
        x=86,
        y=230,
        widths=[390, 180, 230, 180, 170, 420],
        headers=["Configuration", "Cosim size", "Latency", "Power", "LUT", "Interpretation"],
        rows=rows,
        row_styles=styles or None,
        row_height=108,
    )
    _text(
        draw,
        (104, 974),
        "Note for paper: this table reveals why the headline should use the default measured config, while sweep rows stay as design-space evidence.",
        size=24,
        color=MUTED,
        max_width=1500,
    )
    return _save(image, "table_d_design_sweep.png")


def accuracy_table(numbers: dict[str, dict[str, object]]) -> Path:
    image, draw = _base(
        "Table Concept E: Accuracy and Claim Boundary",
        "This protects the paper from overclaiming while still showing useful quantization evidence.",
    )
    rows = [
        [
            "Synthetic MXFP4 B32 state-MXFP4",
            f"{_fmt_float(_v(numbers, 'synthetic_mxfp4_b32_output_cosine'), 6)}",
            f"{_fmt_float(_v(numbers, 'synthetic_mxfp4_b32_output_rel_l2'), 6)}",
            "Use as bit-exact development evidence",
        ],
        [
            "Synthetic MXFP4 B16 state-MXFP4",
            f"{_fmt_float(_v(numbers, 'synthetic_mxfp4_b16_output_cosine'), 6)}",
            f"{_fmt_float(_v(numbers, 'synthetic_mxfp4_b16_output_rel_l2'), 6)}",
            "Block-size ablation",
        ],
        [
            "Synthetic INT4 fallback",
            f"{_fmt_float(_v(numbers, 'synthetic_int4_output_cosine'), 6)}",
            "--",
            "Fallback comparison only",
        ],
        [
            "Real Qwen3-Next activation capture",
            str(_v(numbers, "qwen_capture_status")),
            "--",
            "Do not claim PPL/accuracy until available",
        ],
    ]
    styles = []
    for idx, row in enumerate(rows):
        fill = RED_SOFT if idx == 3 else TEAL_SOFT if idx in (0, 1) else AMBER_SOFT
        styles.append([CellStyle(fill=fill, bold=(c == 0)) for c in range(4)])
    _draw_table(
        draw,
        x=86,
        y=236,
        widths=[470, 260, 250, 590],
        headers=["Evidence", "Output cosine", "Output rel L2", "Allowed claim"],
        rows=rows,
        row_styles=styles,
        row_height=138,
    )
    _card(draw, (86, 860, 1660, 1000), fill="#fbfcff")
    _text(
        draw,
        (118, 895),
        "Recommended wording: measured hardware results are ready; model-quality claims remain synthetic until the real Qwen capture validates them.",
        size=30,
        bold=True,
        color=INK,
        max_width=1450,
    )
    return _save(image, "table_e_accuracy_boundary.png")


def write_index(paths: Iterable[Path]) -> None:
    lines = [
        "# Table Preview Images",
        "",
        "Generated from `paper/numbers.json`, `reports/benchmark/sweep.csv`, and the two source-paper concepts.",
        "These are visual drafts only; generated LaTeX tables are intentionally unchanged for now.",
        "",
    ]
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        title = re.sub(r"[_-]+", " ", path.stem).title()
        lines.extend([f"## {title}", "", f"![{title}](../{rel})", ""])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    try:
        require_release_gate()
    except RuntimeError as exc:
        print(str(exc))
        return 1
    numbers = _load_numbers()
    sweep_rows = _read_sweep()
    paths = [
        main_claim(numbers),
        source_synthesis(),
        hardware_evidence(numbers),
        sweep_table(sweep_rows),
        accuracy_table(numbers),
    ]
    write_index(paths)
    print(f"Wrote {len(paths)} preview images to {OUT_DIR.relative_to(ROOT)}")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

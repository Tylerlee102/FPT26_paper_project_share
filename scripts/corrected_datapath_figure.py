"""Generate the corrected recurrence-core datapath figure from paper numbers."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from scripts.evidence_source_snapshot import describe_source_files
from scripts.reportlab_fonts import FONT_SOURCE, register_embedded_sans


register_embedded_sans()


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NUMBERS = ROOT / "paper" / "corrected" / "numbers.json"
DEFAULT_OUTPUT = (
    ROOT / "paper" / "figures" / "corrected" / "corrected_candidate_datapath.pdf"
)
DEFAULT_MANIFEST = (
    ROOT
    / "paper"
    / "figures"
    / "corrected"
    / "corrected_candidate_datapath_manifest.json"
)
HLS_TOP = ROOT / "hls" / "rs2" / "src" / "gdn_rs2_top.cpp"
HLS_HEADER = ROOT / "hls" / "rs2" / "include" / "gdn_rs2_kernel.hpp"

PAGE_WIDTH = 7.16 * 72
PAGE_HEIGHT = 3.50 * 72
INK = HexColor("#20252B")
MUTED = HexColor("#66707A")
LINE = HexColor("#77828D")
SCHEDULE = HexColor("#4B5563")
SCHEDULE_FILL = HexColor("#F1F3F5")
MX = HexColor("#C65D20")
MX_FILL = HexColor("#FFF1E7")
STATE = HexColor("#167A72")
STATE_FILL = HexColor("#E8F6F3")
LOG = HexColor("#2D62A3")
LOG_FILL = HexColor("#EAF1FA")
FOLD = HexColor("#A8323E")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _value(numbers: dict[str, dict[str, object]], key: str) -> object:
    if key not in numbers:
        raise KeyError(f"missing corrected paper number: {key}")
    return numbers[key]["value"]


def _text_lines(
    drawing: canvas.Canvas,
    lines: list[str],
    *,
    x: float,
    y: float,
    width: float,
    font: str = "Helvetica",
    size: float = 6.7,
    leading: float = 8.0,
    color=INK,
) -> None:
    drawing.setFont(font, size)
    drawing.setFillColor(color)
    cursor = y
    for line in lines:
        words = line.split()
        current = ""
        wrapped: list[str] = []
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if stringWidth(candidate, font, size) <= width:
                current = candidate
            else:
                if current:
                    wrapped.append(current)
                current = word
        if current:
            wrapped.append(current)
        for item in wrapped or [""]:
            drawing.drawString(x, cursor, item)
            cursor -= leading


def _box(
    drawing: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    lines: list[str],
    stroke,
    fill,
    header=None,
    title_size: float = 7.1,
    body_size: float = 6.4,
) -> None:
    header_color = header or stroke
    drawing.setStrokeColor(stroke)
    drawing.setFillColor(fill)
    drawing.setLineWidth(0.8)
    drawing.rect(x, y, width, height, fill=1, stroke=1)
    drawing.setFillColor(header_color)
    drawing.rect(x, y + height - 15, width, 15, fill=1, stroke=0)
    drawing.setFillColor(white)
    drawing.setFont("Helvetica-Bold", title_size)
    drawing.drawString(x + 5, y + height - 10.6, title)
    _text_lines(
        drawing,
        lines,
        x=x + 5,
        y=y + height - 24,
        width=width - 10,
        size=body_size,
        leading=body_size + 1.6,
    )


def _arrow(
    drawing: canvas.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color=LINE,
    dashed: bool = False,
    width: float = 1.0,
) -> None:
    drawing.saveState()
    drawing.setStrokeColor(color)
    drawing.setFillColor(color)
    drawing.setLineWidth(width)
    if dashed:
        drawing.setDash(4, 2)
    drawing.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    head_length = 4.5
    spread = 0.55
    drawing.line(
        x2,
        y2,
        x2 - head_length * math.cos(angle - spread),
        y2 - head_length * math.sin(angle - spread),
    )
    drawing.line(
        x2,
        y2,
        x2 - head_length * math.cos(angle + spread),
        y2 - head_length * math.sin(angle + spread),
    )
    drawing.restoreState()


def generate(numbers_path: Path, output: Path, manifest_path: Path) -> dict[str, object]:
    numbers = json.loads(numbers_path.read_text(encoding="utf-8"))
    keys = (
        "controlled_num_layers",
        "controlled_num_qk_heads",
        "controlled_num_value_heads",
        "controlled_key_dim",
        "controlled_value_dim",
        "controlled_p_k",
        "controlled_p_v",
        "controlled_block_size",
        "controlled_target_clock_ns",
        "corrected_log_capacity",
        "corrected_accumulator_bits",
        "corrected_alignment_guard_bits",
        "corrected_logical_state_bytes",
        "corrected_candidate_step_input_logical_bytes",
        "native_expanded_integer_output_logical_bytes",
    )
    used = {key: _value(numbers, key) for key in keys}
    layers = int(used["controlled_num_layers"])
    qk_heads = int(used["controlled_num_qk_heads"])
    value_heads = int(used["controlled_num_value_heads"])
    key_dim = int(used["controlled_key_dim"])
    value_dim = int(used["controlled_value_dim"])
    block = int(used["controlled_block_size"])
    log_capacity = int(used["corrected_log_capacity"])
    accum_bits = int(used["corrected_accumulator_bits"])
    guard_bits = int(used["corrected_alignment_guard_bits"])
    pk = int(used["controlled_p_k"])
    pv = int(used["controlled_p_v"])
    clock_ns = float(used["controlled_target_clock_ns"])
    logical_bytes = int(used["corrected_logical_state_bytes"])
    step_input_bytes = int(used["corrected_candidate_step_input_logical_bytes"])
    output_bytes = int(used["native_expanded_integer_output_logical_bytes"])

    output.parent.mkdir(parents=True, exist_ok=True)
    drawing = canvas.Canvas(str(output), pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    drawing.setTitle("Selected RS2/R3 Gated DeltaNet recurrence-core datapath")
    drawing.setAuthor("Anonymous artifact")
    drawing.setSubject("Evidence-backed MXFP4 recurrence-core architecture")
    drawing.setFillColor(INK)
    drawing.setFont("Helvetica-Bold", 8.3)
    drawing.drawString(8, PAGE_HEIGHT - 12, "One-token recurrence-core STEP (batch one)")
    drawing.setFont("Helvetica", 6.4)
    drawing.setFillColor(MUTED)
    drawing.drawRightString(
        PAGE_WIDTH - 8,
        PAGE_HEIGHT - 12,
        f"U55C target {clock_ns:.1f} ns | P_K={pk}, P_V={pv} | B{block}",
    )

    left_x = 8
    left_w = 84
    phase_y = 132
    phase_h = 91
    phase_x = 96
    gap = 5
    phase_w = (PAGE_WIDTH - phase_x - 8 - 4 * gap) / 5

    _box(
        drawing,
        x=left_x,
        y=181,
        width=left_w,
        height=42,
        title="Control",
        lines=[
            "RESET / LOAD / STEP / READBACK",
            f"sequence + layer 0-{layers - 1}",
        ],
        stroke=SCHEDULE,
        fill=SCHEDULE_FILL,
        body_size=6.0,
    )
    _box(
        drawing,
        x=left_x,
        y=82,
        width=left_w,
        height=91,
        title="Token inputs",
        lines=[
            f"q,k: {qk_heads} x {key_dim}",
            f"v: {value_heads} x {value_dim}",
            "residual-stacked E2M1",
            f"E8M0 scales per {block}",
            f"alpha,beta: Q1.15 x {value_heads}",
            f"logical STEP in: {step_input_bytes:,} B",
        ],
        stroke=SCHEDULE,
        fill=SCHEDULE_FILL,
        body_size=6.2,
    )
    _box(
        drawing,
        x=left_x,
        y=16,
        width=left_w,
        height=58,
        title="Native MX",
        lines=[
            "E2M1 LUT products",
            "E8M0 alignment + RNE",
            f"INT{accum_bits}, {guard_bits} guard bits",
        ],
        stroke=MX,
        fill=MX_FILL,
        body_size=6.0,
    )

    phases = [
        (
            "1  Prepare",
            ["validate codes", "select resident slot", "unpack token"],
        ),
        (
            "2  Decay/predict",
            ["gamma,lambda *= alpha", "k^T(base + log)", "aligned integer dots"],
        ),
        (
            "3  Delta",
            ["u = beta(v - pred)", "Q1.15 coefficient", "aligned residual"],
        ),
        (
            "4  Append write",
            ["encode k and u", "new rank-one entry", "no base rewrite"],
        ),
        (
            "5  Output",
            [
                "q^T(base + log)",
                "includes new write",
                "mantissa + exponent",
                f"logical out: {output_bytes:,} B",
            ],
        ),
    ]
    phase_positions: list[tuple[float, float]] = []
    for index, (title, lines) in enumerate(phases):
        x = phase_x + index * (phase_w + gap)
        phase_positions.append((x, x + phase_w))
        _box(
            drawing,
            x=x,
            y=phase_y,
            width=phase_w,
            height=phase_h,
            title=title,
            lines=lines,
            stroke=SCHEDULE,
            fill=SCHEDULE_FILL,
            body_size=6.2,
        )
        if index:
            _arrow(
                drawing,
                phase_positions[index - 1][1],
                phase_y + phase_h / 2,
                x,
                phase_y + phase_h / 2,
            )
    _arrow(drawing, left_x + left_w, 151, phase_x, 151)
    _arrow(drawing, left_x + left_w, 53, phase_positions[1][0], 53, color=MX)
    drawing.setStrokeColor(MX)
    drawing.line(phase_positions[1][0], 53, phase_positions[1][0], phase_y)

    state_y = 24
    state_h = 92
    state_x = phase_x
    state_w = 185
    log_x = state_x + state_w + 10
    log_w = PAGE_WIDTH - log_x - 8
    _box(
        drawing,
        x=state_x,
        y=state_y,
        width=state_w,
        height=state_h,
        title="Persistent RS2 base state",
        lines=[
            f"{value_heads} heads x {key_dim} x {value_dim} (K-by-V)",
            f"E2M1 primary + E2M1 residual, B{block}",
            "separate E8M0 scales; gamma in Q1.15",
            f"logical layer payload: {logical_bytes:,} bytes including log",
        ],
        stroke=STATE,
        fill=STATE_FILL,
        body_size=6.4,
    )
    _box(
        drawing,
        x=log_x,
        y=state_y,
        width=log_w,
        height=state_h,
        title=f"Recent-write log (R={log_capacity})",
        lines=[
            f"key: {qk_heads} x {key_dim}; update: {value_heads} x {value_dim}",
            f"residual-stacked E2M1/E8M0 B{block}",
            f"lambda: Q1.15 x {value_heads} per live entry",
            "append once per STEP; output sees newest entry",
        ],
        stroke=LOG,
        fill=LOG_FILL,
        body_size=6.4,
    )

    phase2_mid = sum(phase_positions[1]) / 2
    phase4_mid = sum(phase_positions[3]) / 2
    phase5_mid = sum(phase_positions[4]) / 2
    _arrow(drawing, phase2_mid, state_y + state_h, phase2_mid, phase_y, color=STATE)
    _arrow(drawing, phase4_mid, phase_y, phase4_mid, state_y + state_h, color=LOG)
    _arrow(drawing, phase5_mid, state_y + state_h, phase5_mid, phase_y, color=LOG)

    fold_y = state_y + 7
    _arrow(
        drawing,
        log_x + 25,
        fold_y,
        state_x + state_w - 25,
        fold_y,
        color=FOLD,
        dashed=True,
        width=1.2,
    )
    drawing.setFillColor(FOLD)
    drawing.setFont("Helvetica-Bold", 5.9)
    drawing.drawCentredString(
        (log_x + 25 + state_x + state_w - 25) / 2,
        fold_y + 3.5,
        f"atomic fold after output when {log_capacity} entries are live",
    )

    legend_y = 7
    drawing.setFont("Helvetica", 5.8)
    legend = (
        (SCHEDULE, "inherited five-phase schedule/control"),
        (MX, "native MX arithmetic"),
        (STATE, "persistent RS2 state"),
        (FOLD, "periodic fold"),
    )
    cursor = 96
    for color, label in legend:
        drawing.setFillColor(color)
        drawing.rect(cursor, legend_y, 7, 4, fill=1, stroke=0)
        drawing.setFillColor(MUTED)
        drawing.drawString(cursor + 10, legend_y - 0.3, label)
        cursor += 10 + stringWidth(label, "Helvetica", 5.8) + 14

    drawing.showPage()
    drawing.save()

    source_identity = describe_source_files(
        [Path(__file__), FONT_SOURCE, HLS_TOP, HLS_HEADER]
    )
    relative_output = (
        output.relative_to(ROOT).as_posix()
        if output.is_relative_to(ROOT)
        else str(output)
    )
    manifest = {
        "schema": 1,
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "selected RS2/R3 recurrence-core datapath figure",
        "source_identity": source_identity,
        "numbers": (
            numbers_path.relative_to(ROOT).as_posix()
            if numbers_path.is_relative_to(ROOT)
            else str(numbers_path)
        ),
        "used_number_values": used,
        "outputs": {relative_output: _sha256(output)},
        "verification": [
            "all displayed numeric widths, rates, dimensions, and capacities are read from corrected paper numbers",
            "phase ordering and fold timing are cross-checked against the selected RS2/R3 HLS source",
            "PDF rendering and visual inspection are separate evidence",
        ],
        "limitations": [
            "logical architecture figure, not placement or routing evidence",
            "the five-phase schedule is inherited; only the arithmetic and RS2/R3 state representation are modified",
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
    manifest = generate(
        _resolve(args.numbers), _resolve(args.output), _resolve(args.manifest)
    )
    print(json.dumps({"status": manifest["status"], "outputs": manifest["outputs"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

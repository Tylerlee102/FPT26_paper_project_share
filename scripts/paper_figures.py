from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
NUMBERS = ROOT / "paper" / "numbers.json"
FIGURES = ROOT / "paper" / "figures"


BLUE = (0.13, 0.27, 0.52)
TEAL = (0.05, 0.48, 0.45)
GREEN = (0.20, 0.55, 0.24)
ORANGE = (0.86, 0.42, 0.12)
RED = (0.74, 0.18, 0.18)
PURPLE = (0.38, 0.28, 0.58)
GRAY = (0.42, 0.45, 0.48)
LIGHT = (0.94, 0.96, 0.98)
WHITE = (1.0, 1.0, 1.0)
BLACK = (0.05, 0.06, 0.07)


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _fmt(value: object, digits: int = 2) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def _color(color: tuple[float, float, float]) -> str:
    return f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f}"


class PdfCanvas:
    def __init__(self, width: int = 360, height: int = 230) -> None:
        self.width = width
        self.height = height
        self.ops: list[str] = []

    def text(
        self,
        x: float,
        y: float,
        text: str,
        size: int = 9,
        color: tuple[float, float, float] = BLACK,
        bold: bool = False,
    ) -> None:
        font = "F2" if bold else "F1"
        self.ops.append(f"{_color(color)} rg")
        self.ops.append(f"BT /{font} {size} Tf {x:.2f} {y:.2f} Td ({_pdf_escape(text)}) Tj ET")

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill: tuple[float, float, float] = WHITE,
        stroke: tuple[float, float, float] = BLACK,
        line_width: float = 0.8,
    ) -> None:
        self.ops.append(f"{line_width:.2f} w")
        self.ops.append(f"{_color(stroke)} RG")
        self.ops.append(f"{_color(fill)} rg")
        self.ops.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re B")

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple[float, float, float] = BLACK,
        line_width: float = 0.8,
    ) -> None:
        self.ops.append(f"{line_width:.2f} w")
        self.ops.append(f"{_color(color)} RG")
        self.ops.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def arrow(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple[float, float, float] = BLACK,
        line_width: float = 0.9,
    ) -> None:
        self.line(x1, y1, x2, y2, color, line_width)
        angle = math.atan2(y2 - y1, x2 - x1)
        for offset in (2.55, -2.55):
            ax = x2 - 6.0 * math.cos(angle + offset)
            ay = y2 - 6.0 * math.sin(angle + offset)
            self.line(x2, y2, ax, ay, color, line_width)

    def box_label(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        title: str,
        subtitle: str = "",
        fill: tuple[float, float, float] = LIGHT,
        stroke: tuple[float, float, float] = BLUE,
    ) -> None:
        self.rect(x, y, width, height, fill=fill, stroke=stroke, line_width=0.9)
        self.text(x + 6, y + height - 13, title, size=8, bold=True, color=BLACK)
        if subtitle:
            self.text(x + 6, y + 7, subtitle, size=6, color=GRAY)

    def write(self, path: Path) -> None:
        stream = "\n".join(self.ops).encode("ascii", errors="replace")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width} {self.height}] "
                "/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>"
            ).encode("ascii"),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        ]
        pdf = bytearray(b"%PDF-1.4\n")
        offsets: list[int] = []
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{index} 0 obj\n".encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")
        xref = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
        )
        path.write_bytes(pdf)


def _bar_chart(path: Path, title: str, labels: list[str], values: list[float], unit: str, colors: list[tuple[float, float, float]]) -> None:
    canvas = PdfCanvas(350, 220)
    canvas.text(16, 198, title, size=12, bold=True, color=BLUE)
    x0, y0, chart_w, chart_h = 45, 45, 260, 125
    ymax = max(values) * 1.18 if values else 1.0
    canvas.line(x0, y0, x0 + chart_w, y0, GRAY)
    canvas.line(x0, y0, x0, y0 + chart_h, GRAY)
    bar_w = chart_w / max(len(values) * 1.7, 1)
    for i, value in enumerate(values):
        x = x0 + 18 + i * (chart_w / len(values))
        h = chart_h * value / ymax
        canvas.rect(x, y0, bar_w, h, fill=colors[i % len(colors)], stroke=colors[i % len(colors)])
        canvas.text(x - 4, y0 - 16, labels[i], size=7, color=BLACK)
        canvas.text(x - 4, y0 + h + 5, f"{_fmt(value, 2)} {unit}", size=7, color=BLACK)
    canvas.write(path)


def _horizontal_util(path: Path, numbers: dict[str, dict[str, object]]) -> None:
    labels = ["LUT", "DSP", "BRAM"]
    values = [
        float(numbers["ours_mxfp4_b32_lut_pct"]["value"]),
        float(numbers["ours_mxfp4_b32_dsp_pct"]["value"]),
        float(numbers["ours_mxfp4_b32_bram_pct"]["value"]),
    ]
    colors = [BLUE, ORANGE, TEAL]
    canvas = PdfCanvas(350, 200)
    canvas.text(16, 178, "Post-Implementation Resource Use", size=12, bold=True, color=BLUE)
    canvas.text(16, 162, "Default MXFP4 B=32, P_K=16, P_V=8", size=8, color=GRAY)
    x0, y = 80, 125
    for label, value, color in zip(labels, values, colors):
        canvas.text(18, y + 2, label, size=9, bold=True)
        canvas.rect(x0, y, 210, 12, fill=(0.90, 0.92, 0.94), stroke=(0.90, 0.92, 0.94))
        canvas.rect(x0, y, 210 * value / 100.0, 12, fill=color, stroke=color)
        canvas.text(x0 + 218, y + 2, f"{_fmt(value, 2)}%", size=8)
        y -= 32
    canvas.line(x0 + 210 * 0.8, 50, x0 + 210 * 0.8, 145, RED, 0.7)
    canvas.text(x0 + 210 * 0.8 - 12, 36, "80% gate", size=7, color=RED)
    canvas.write(path)


def _pareto(path: Path, rows: list[dict[str, str]], numbers: dict[str, dict[str, object]]) -> None:
    canvas = PdfCanvas(350, 230)
    canvas.text(16, 207, "Parallelism Sweep Pareto View", size=12, bold=True, color=BLUE)
    x0, y0, w, h = 48, 42, 250, 135
    canvas.line(x0, y0, x0 + w, y0, GRAY)
    canvas.line(x0, y0, x0, y0 + h, GRAY)
    canvas.text(x0 + 74, 20, "LUT utilization (%)", size=8, color=GRAY)
    canvas.text(8, y0 + 65, "log latency", size=8, color=GRAY)

    points: list[tuple[str, float, float, str]] = []
    for row in rows:
        try:
            points.append((row["config"], float(row["lut_pct"]), float(row["latency_us"]), row.get("impl_status", "")))
        except (KeyError, ValueError):
            continue
    if not points:
        points = [
            (
                "default",
                float(numbers["ours_mxfp4_b32_lut_pct"]["value"]),
                float(numbers["ours_mxfp4_b32_latency_us"]["value"]),
                "impl",
            )
        ]
    max_lut = max(p[1] for p in points) * 1.25
    logs = [math.log10(max(p[2], 1e-3)) for p in points]
    min_log, max_log = min(logs), max(logs)
    span = max(max_log - min_log, 0.1)
    for name, lut, latency, status in points:
        x = x0 + w * lut / max_lut
        y = y0 + h * (math.log10(max(latency, 1e-3)) - min_log) / span
        color = GREEN if "default" in name or "b32_pk16" in name else PURPLE
        canvas.rect(x - 3, y - 3, 6, 6, fill=color, stroke=color)
        short = name.replace("mxfp4_", "").replace("_", " ")
        canvas.text(x + 5, y + 3, short[:22], size=6, color=BLACK)
        if status:
            canvas.text(x + 5, y - 6, status[:18], size=5, color=GRAY)
    canvas.write(path)


def _block_accuracy(path: Path, numbers: dict[str, dict[str, object]]) -> None:
    labels = ["MX B32", "MX B16", "INT4"]
    values = [
        float(numbers["synthetic_mxfp4_b32_output_cosine"]["value"]),
        float(numbers.get("synthetic_mxfp4_b16_output_cosine", {"value": 0.0})["value"]),
        float(numbers["synthetic_int4_output_cosine"]["value"]),
    ]
    canvas = PdfCanvas(350, 220)
    canvas.text(16, 198, "Synthetic Output-Cosine Accuracy", size=12, bold=True, color=BLUE)
    x0, y0, w, h = 45, 45, 260, 125
    canvas.line(x0, y0, x0 + w, y0, GRAY)
    canvas.line(x0, y0, x0, y0 + h, GRAY)
    canvas.text(16, 172, "Higher is better. Real Qwen PPL remains pending.", size=7, color=RED)
    floor = min(values) - 0.01
    span = max(max(values) - floor, 0.01)
    colors = [BLUE, TEAL, ORANGE]
    for i, value in enumerate(values):
        x = x0 + 25 + i * 80
        height = h * (value - floor) / span
        canvas.rect(x, y0, 42, height, fill=colors[i], stroke=colors[i])
        canvas.text(x - 3, y0 - 16, labels[i], size=7)
        canvas.text(x - 1, y0 + height + 5, _fmt(value, 3), size=7)
    canvas.text(17, 35, f"axis floor={_fmt(floor, 3)}", size=6, color=GRAY)
    canvas.write(path)


def _roofline(path: Path, numbers: dict[str, dict[str, object]]) -> None:
    latency = float(numbers["ours_mxfp4_b32_latency_us"]["value"])
    power = float(numbers["ours_mxfp4_b32_power_w"]["value"])
    canvas = PdfCanvas(350, 220)
    canvas.text(16, 198, "Roofline-Style Positioning", size=12, bold=True, color=BLUE)
    x0, y0, w, h = 48, 42, 250, 130
    canvas.line(x0, y0, x0 + w, y0, GRAY)
    canvas.line(x0, y0, x0, y0 + h, GRAY)
    canvas.text(75, 20, "arithmetic intensity (conceptual)", size=8, color=GRAY)
    canvas.text(9, 110, "perf.", size=8, color=GRAY)
    canvas.line(x0 + 10, y0 + 15, x0 + 125, y0 + 96, TEAL, 1.3)
    canvas.line(x0 + 125, y0 + 96, x0 + 235, y0 + 96, TEAL, 1.3)
    px, py = x0 + 155, y0 + 62
    canvas.rect(px - 4, py - 4, 8, 8, fill=ORANGE, stroke=ORANGE)
    canvas.text(px + 8, py + 6, "Ours MXFP4", size=8, bold=True)
    canvas.text(px + 8, py - 7, f"{_fmt(latency, 2)} us/token, {_fmt(power, 2)} W", size=7, color=GRAY)
    canvas.text(x0 + 140, y0 + 104, "compute roof", size=7, color=TEAL)
    canvas.text(x0 + 36, y0 + 45, "memory slope", size=7, color=TEAL)
    canvas.write(path)


def _dataflow(path: Path) -> None:
    canvas = PdfCanvas(360, 235)
    canvas.text(16, 214, "Persistent-State GDN Decode Dataflow", size=12, bold=True, color=BLUE)
    canvas.box_label(16, 154, 72, 40, "Token inputs", "q, k, v, beta, gate", fill=(0.94, 0.98, 1.0), stroke=BLUE)
    canvas.box_label(108, 154, 72, 40, "MX prepare", "pack + block scales", fill=LIGHT, stroke=TEAL)
    canvas.box_label(200, 154, 72, 40, "MAC fabric", "native E2M1", fill=(0.96, 0.95, 1.0), stroke=PURPLE)
    canvas.box_label(288, 154, 54, 40, "Output", "packed lanes", fill=(0.96, 1.0, 0.95), stroke=GREEN)
    canvas.box_label(106, 58, 130, 46, "Resident recurrent state", "E2M1 banks + E8M0 scale banks", fill=(1.0, 0.97, 0.91), stroke=ORANGE)
    canvas.box_label(250, 58, 92, 46, "Delta update", "writeback in place", fill=(1.0, 0.94, 0.94), stroke=RED)
    canvas.arrow(88, 174, 108, 174, BLUE)
    canvas.arrow(180, 174, 200, 174, TEAL)
    canvas.arrow(272, 174, 288, 174, PURPLE)
    canvas.arrow(236, 81, 250, 81, ORANGE)
    canvas.arrow(296, 104, 238, 154, RED)
    canvas.arrow(172, 154, 172, 105, ORANGE)
    canvas.arrow(236, 154, 236, 105, PURPLE)
    canvas.text(42, 124, "state read", size=7, color=GRAY)
    canvas.arrow(106, 81, 76, 81, ORANGE)
    canvas.arrow(76, 81, 206, 154, ORANGE)
    canvas.write(path)


def _mxfp4_datapath(path: Path) -> None:
    canvas = PdfCanvas(360, 238)
    canvas.text(16, 216, "Native MXFP4 Multiply and Accumulate", size=12, bold=True, color=BLUE)
    canvas.box_label(16, 164, 72, 38, "MX block A", "E8M0 scale + E2M1", fill=(0.94, 0.98, 1.0), stroke=BLUE)
    canvas.box_label(16, 104, 72, 38, "MX block B", "E8M0 scale + E2M1", fill=(0.94, 0.98, 1.0), stroke=BLUE)
    canvas.box_label(112, 164, 66, 38, "Sign XOR", "1-bit sign", fill=LIGHT, stroke=TEAL)
    canvas.box_label(112, 104, 66, 38, "Exp add", "bias adjust", fill=LIGHT, stroke=TEAL)
    canvas.box_label(112, 44, 66, 38, "Mantissa", "implicit one", fill=LIGHT, stroke=TEAL)
    canvas.box_label(204, 104, 62, 58, "Normalize", "round to Q4.3", fill=(0.96, 0.95, 1.0), stroke=PURPLE)
    canvas.box_label(292, 118, 52, 44, "INT24", "block accum", fill=(0.96, 1.0, 0.95), stroke=GREEN)
    canvas.box_label(204, 34, 140, 38, "Block exponent align", "shift by shared E8M0 scale", fill=(1.0, 0.97, 0.91), stroke=ORANGE)
    canvas.arrow(88, 183, 112, 183, BLUE)
    canvas.arrow(88, 123, 112, 123, BLUE)
    canvas.arrow(178, 183, 204, 144, TEAL)
    canvas.arrow(178, 123, 204, 132, TEAL)
    canvas.arrow(178, 63, 204, 112, TEAL)
    canvas.arrow(266, 132, 292, 140, PURPLE)
    canvas.arrow(274, 53, 318, 118, ORANGE)
    canvas.text(18, 88, "No FP32/BF16 dequantize in inner loop", size=8, color=RED, bold=True)
    canvas.write(path)


def _pipeline(path: Path) -> None:
    canvas = PdfCanvas(360, 212)
    canvas.text(16, 192, "Machine-Traceable Paper Pipeline", size=12, bold=True, color=BLUE)
    canvas.box_label(16, 130, 78, 42, "Reports", "HLS, cosim, Vivado", fill=(0.94, 0.98, 1.0), stroke=BLUE)
    canvas.box_label(114, 130, 82, 42, "Extractors", "benchmark scripts", fill=LIGHT, stroke=TEAL)
    canvas.box_label(216, 130, 126, 42, "numbers.json + provenance", "value, source, line, SHA", fill=(1.0, 0.97, 0.91), stroke=ORANGE)
    canvas.box_label(66, 50, 96, 42, "Generated paper assets", "macros, tables, figures", fill=(0.96, 0.95, 1.0), stroke=PURPLE)
    canvas.box_label(202, 50, 94, 42, "Submission pack", "PDF + reproducibility", fill=(0.96, 1.0, 0.95), stroke=GREEN)
    canvas.arrow(94, 151, 114, 151, BLUE)
    canvas.arrow(196, 151, 216, 151, TEAL)
    canvas.arrow(278, 130, 150, 92, ORANGE)
    canvas.arrow(162, 71, 202, 71, PURPLE)
    canvas.text(16, 23, "Measured values are not typed into the manuscript by hand.", size=8, color=RED, bold=True)
    canvas.write(path)


def _state_precision(path: Path, numbers: dict[str, dict[str, object]]) -> None:
    canvas = PdfCanvas(360, 230)
    canvas.text(16, 207, "Recurrent-State Precision Stress", size=12, bold=True, color=BLUE)
    canvas.text(16, 191, "Higher output cosine is better; lower state rel. L2 is better.", size=7, color=GRAY)
    labels = ["Drift cos.", "Boundary cos.", "Stress worst cos."]
    mxfp4 = [
        float(numbers["synthetic_drift_mxfp4_final_output_cosine"]["value"]),
        float(numbers["synthetic_boundary_state_mxfp4_b16_output_cosine"]["value"]),
        float(numbers["synthetic_stress_combined_stress_state_mxfp4_b16_worst_output_cosine"]["value"]),
    ]
    mxfp8 = [
        float(numbers["synthetic_drift_mxfp8_final_output_cosine"]["value"]),
        float(numbers["synthetic_boundary_state_mxfp8_b16_output_cosine"]["value"]),
        float(numbers["synthetic_stress_combined_stress_state_mxfp8_b16_worst_output_cosine"]["value"]),
    ]
    x0, y0, w, h = 48, 55, 255, 115
    canvas.line(x0, y0, x0 + w, y0, GRAY)
    canvas.line(x0, y0, x0, y0 + h, GRAY)
    group_w = w / len(labels)
    for i, label in enumerate(labels):
        gx = x0 + 18 + i * group_w
        for j, (value, color) in enumerate(((mxfp4[i], ORANGE), (mxfp8[i], TEAL))):
            bar_w = 16
            x = gx + j * 20
            bar_h = h * value
            canvas.rect(x, y0, bar_w, bar_h, fill=color, stroke=color)
            canvas.text(x - 2, y0 + bar_h + 4, _fmt(value, 3), size=6)
        canvas.text(gx - 8, y0 - 16, label, size=6)
    canvas.rect(224, 183, 8, 8, fill=ORANGE, stroke=ORANGE)
    canvas.text(236, 184, "MXFP4 state", size=7)
    canvas.rect(224, 170, 8, 8, fill=TEAL, stroke=TEAL)
    canvas.text(236, 171, "MXFP8 state", size=7)
    canvas.text(
        16,
        27,
        f"1024-token state rel. L2: MXFP4={_fmt(float(numbers['synthetic_drift_mxfp4_final_state_rel_l2']['value']), 3)}, "
        f"MXFP8={_fmt(float(numbers['synthetic_drift_mxfp8_final_state_rel_l2']['value']), 3)}",
        size=7,
        color=RED,
        bold=True,
    )
    canvas.write(path)


def _state_traffic(path: Path, numbers: dict[str, dict[str, object]]) -> None:
    canvas = PdfCanvas(360, 220)
    canvas.text(16, 198, "Off-Chip Recurrent-State Traffic", size=12, bold=True, color=BLUE)
    canvas.text(16, 182, "MXFP4 B=32 recurrent state, bytes per token", size=8, color=GRAY)
    naive = float(numbers["offchip_mxfp4_b32_naive_three_pass_bytes_per_token"]["value"])
    persistent = float(numbers["offchip_mxfp4_b32_persistent_bytes_per_token"]["value"])
    x0, y0, w, h = 68, 58, 215, 105
    canvas.line(x0, y0, x0 + w, y0, GRAY)
    canvas.line(x0, y0, x0, y0 + h, GRAY)
    ymax = max(naive, 1.0) * 1.12
    values = [naive, persistent]
    labels = ["naive three-pass", "persistent"]
    colors = [RED, GREEN]
    for i, value in enumerate(values):
        x = x0 + 32 + i * 105
        bar_h = h * value / ymax
        canvas.rect(x, y0, 42, max(bar_h, 1.5 if value == 0 else bar_h), fill=colors[i], stroke=colors[i])
        canvas.text(x - 12, y0 - 16, labels[i], size=7)
        canvas.text(x - 2, y0 + bar_h + 5, f"{int(value):,}", size=8, bold=True)
    canvas.text(
        16,
        28,
        f"Stored MXFP4 B=32 state: {int(numbers['state_storage_mxfp4_b32_bytes']['value']):,} bytes",
        size=8,
        color=BLACK,
    )
    canvas.write(path)


def _write_stub(filename: str) -> None:
    (FIGURES / filename.replace(".pdf", ".py")).write_text(
        "\n".join(
            [
                '"""Source stub for the generated figure.',
                "",
                "Run `python -m scripts.paper_figures` from the repository root to regenerate this PDF.",
                '"""',
                "",
                "from scripts.paper_figures import main",
                "",
                "",
                "if __name__ == \"__main__\":",
                "    raise SystemExit(main())",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    numbers = json.loads(NUMBERS.read_text(encoding="utf-8"))
    FIGURES.mkdir(parents=True, exist_ok=True)

    sweep_rows: list[dict[str, str]] = []
    sweep_csv = ROOT / "reports" / "benchmark" / "sweep.csv"
    if sweep_csv.exists():
        with sweep_csv.open(newline="", encoding="utf-8") as handle:
            sweep_rows = list(csv.DictReader(handle))

    specs = [
        "latency_comparison.pdf",
        "area_breakdown.pdf",
        "parallelism_pareto.pdf",
        "block_size_accuracy.pdf",
        "roofline.pdf",
        "gdn_dataflow.pdf",
        "mxfp4_mac_datapath.pdf",
        "paper_pipeline.pdf",
        "state_precision_stress.pdf",
        "state_traffic.pdf",
    ]

    _bar_chart(
        FIGURES / "latency_comparison.pdf",
        "Decode Latency per Token",
        ["H100", "USC", "Ours"],
        [
            float(numbers["h100_baseline_latency_us"]["value"]),
            float(numbers["usc_baseline_latency_us"]["value"]),
            float(numbers["ours_mxfp4_b32_latency_us"]["value"]),
        ],
        "us",
        [GRAY, BLUE, GREEN],
    )
    _horizontal_util(FIGURES / "area_breakdown.pdf", numbers)
    _pareto(FIGURES / "parallelism_pareto.pdf", sweep_rows, numbers)
    _block_accuracy(FIGURES / "block_size_accuracy.pdf", numbers)
    _roofline(FIGURES / "roofline.pdf", numbers)
    _dataflow(FIGURES / "gdn_dataflow.pdf")
    _mxfp4_datapath(FIGURES / "mxfp4_mac_datapath.pdf")
    _pipeline(FIGURES / "paper_pipeline.pdf")
    _state_precision(FIGURES / "state_precision_stress.pdf", numbers)
    _state_traffic(FIGURES / "state_traffic.pdf", numbers)

    for filename in specs:
        _write_stub(filename)
    print("Wrote paper figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

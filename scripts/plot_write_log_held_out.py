"""Plot the frozen held-out write-log result with provenance checks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRICES = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "write_log_held_out_random"
    / "matrix_manifest.json",
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "write_log_held_out_zero"
    / "matrix_manifest.json",
)
DEFAULT_SELECTION = (
    ROOT / "reports" / "benchmark" / "corrected" / "write_log_selection.json"
)
DEFAULT_DATA = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "write_log_held_out_plot_data.csv"
)
DEFAULT_COSINE = (
    ROOT
    / "paper"
    / "figures"
    / "corrected"
    / "write_log_held_out_output_cosine.pdf"
)
DEFAULT_STATE = (
    ROOT
    / "paper"
    / "figures"
    / "corrected"
    / "write_log_held_out_state_rel_l2.pdf"
)
DEFAULT_MANIFEST = (
    ROOT
    / "paper"
    / "figures"
    / "corrected"
    / "write_log_held_out_plot_manifest.json"
)

PAGE_WIDTH = 7.16 * 72.0
PAGE_HEIGHT = 3.72 * 72.0
LEFT = 58.0
RIGHT = 18.0
BOTTOM = 48.0
TOP = 59.0
MEAN_COLOR = (0.00, 0.34, 0.38)
BAND_COLOR = (0.78, 0.89, 0.89)
EDGE_COLOR = (0.35, 0.61, 0.63)
GATE_COLOR = (0.73, 0.18, 0.16)
CHECKPOINTS = (64, 256, 1024, 4096, 8192)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _require_hash(path: Path, expected: str, label: str) -> None:
    observed = _sha256(path)
    if observed.lower() != expected.lower():
        raise ValueError(
            f"{label} hash mismatch for {path}: expected {expected}, got {observed}"
        )


def _find_token_csv(run_manifest: dict[str, object]) -> tuple[Path, str]:
    outputs = run_manifest.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("run manifest has no outputs object")
    matches = [
        (str(path), str(digest))
        for path, digest in outputs.items()
        if str(path).endswith("_tokens.csv")
    ]
    if len(matches) != 1:
        raise ValueError(f"run manifest must name one token CSV, found {len(matches)}")
    path, digest = matches[0]
    return _repo_path(path), digest


def _read_candidate_trace(
    token_csv: Path,
    *,
    variant: str,
    expected_tokens: int,
) -> list[dict[str, str]]:
    with token_csv.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["variant"] == variant]
    expected_indices = list(range(1, expected_tokens + 1))
    observed_indices = [int(row["token_index"]) for row in rows]
    if observed_indices != expected_indices:
        raise ValueError(
            f"{token_csv} does not contain one ordered candidate row per token"
        )
    if any(row["split"] != "held_out" for row in rows):
        raise ValueError(f"{token_csv} is not entirely held_out")
    if any(row["trace_family"] != "nominal" for row in rows):
        raise ValueError(f"{token_csv} is not entirely nominal")
    if any(int(row["dropped_entries"]) != 0 for row in rows):
        raise ValueError(f"{token_csv} contains dropped write-log entries")
    if any(row["event_metrics_status"] != "PASS" for row in rows):
        raise ValueError(f"{token_csv} contains incomplete event metrics")
    return rows


def _load_traces(
    matrix_paths: list[Path],
    selection_path: Path,
) -> tuple[str, list[dict[str, object]], list[list[dict[str, str]]]]:
    selection = _load_json(selection_path)
    if selection.get("status") != "PASS":
        raise ValueError("frozen selection status is not PASS")
    variant = str(selection["selected_variant"])
    selection_hash = _sha256(selection_path)
    traces: list[list[dict[str, str]]] = []
    trace_metadata: list[dict[str, object]] = []

    for matrix_path in matrix_paths:
        matrix = _load_json(matrix_path)
        if matrix.get("status") != "PASS":
            raise ValueError(f"matrix status is not PASS: {matrix_path}")
        if matrix.get("split") != "held_out" or matrix.get("families") != ["nominal"]:
            raise ValueError(f"matrix is not the held-out nominal protocol: {matrix_path}")
        _require_hash(
            selection_path,
            str(matrix["selection_sha256"]),
            "selection",
        )
        if str(matrix["selection_sha256"]).lower() != selection_hash.lower():
            raise ValueError("matrix selection differs from the current frozen selection")
        expected_tokens = int(matrix["tokens"])
        if expected_tokens != 8192:
            raise ValueError(f"held-out matrix length is {expected_tokens}, expected 8192")

        runs = matrix.get("runs")
        if not isinstance(runs, list):
            raise ValueError(f"matrix has no runs list: {matrix_path}")
        for run in runs:
            if not isinstance(run, dict):
                raise ValueError("matrix run is not an object")
            if run.get("status") != "PASS" or run.get("gate_pass") is not True:
                raise ValueError(f"matrix includes a non-PASS run: {run.get('stem')}")
            run_manifest_path = _repo_path(str(run["manifest"]))
            _require_hash(run_manifest_path, str(run["manifest_sha256"]), "run manifest")
            run_manifest = _load_json(run_manifest_path)
            token_csv, token_hash = _find_token_csv(run_manifest)
            _require_hash(token_csv, token_hash, "token CSV")
            rows = _read_candidate_trace(
                token_csv,
                variant=variant,
                expected_tokens=expected_tokens,
            )
            traces.append(rows)
            trace_metadata.append(
                {
                    "stem": run["stem"],
                    "seed": int(rows[0]["seed"]),
                    "initial_state": run_manifest["initial_state_mode"],
                    "input_stream_sha256": run["input_stream_sha256"],
                    "run_manifest": str(run["manifest"]),
                    "run_manifest_sha256": str(run["manifest_sha256"]),
                    "token_csv": token_csv.relative_to(ROOT).as_posix(),
                    "token_csv_sha256": token_hash,
                }
            )

    if len(traces) != 6:
        raise ValueError(f"expected six held-out traces, found {len(traces)}")
    if {str(item["initial_state"]) for item in trace_metadata} != {"random", "zero"}:
        raise ValueError("held-out traces do not cover random and zero initial state")
    if len({int(item["seed"]) for item in trace_metadata}) != 3:
        raise ValueError("held-out traces do not cover exactly three seeds")
    return variant, trace_metadata, traces


def _aggregate_traces(
    traces: list[list[dict[str, str]]],
) -> list[dict[str, float | int]]:
    if not traces:
        raise ValueError("no traces to aggregate")
    length = len(traces[0])
    if any(len(trace) != length for trace in traces):
        raise ValueError("trace lengths differ")
    aggregated: list[dict[str, float | int]] = []
    for index in range(length):
        token = int(traces[0][index]["token_index"])
        if any(int(trace[index]["token_index"]) != token for trace in traces):
            raise ValueError(f"trace token mismatch at row {index}")
        cosine = [float(trace[index]["output_cosine_fp32"]) for trace in traces]
        state = [float(trace[index]["state_rel_l2"]) for trace in traces]
        aggregated.append(
            {
                "token_index": token,
                "trace_count": len(traces),
                "output_cosine_mean": statistics.fmean(cosine),
                "output_cosine_min": min(cosine),
                "output_cosine_max": max(cosine),
                "state_rel_l2_mean": statistics.fmean(state),
                "state_rel_l2_min": min(state),
                "state_rel_l2_max": max(state),
            }
        )
    return aggregated


def _write_aggregate(path: Path, rows: list[dict[str, float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _draw_legend(pdf: canvas.Canvas, y: float) -> None:
    items = (
        ("band", "Six-trace min-max envelope"),
        ("mean", "Six-trace mean"),
        ("gate", "Preregistered engineering gate"),
    )
    x = LEFT
    pdf.setFont("Helvetica", 7.1)
    for kind, label in items:
        item_width = stringWidth(label, "Helvetica", 7.1) + 31.0
        if kind == "band":
            pdf.setFillColorRGB(*BAND_COLOR)
            pdf.setStrokeColorRGB(*EDGE_COLOR)
            pdf.rect(x, y - 1.5, 14, 6, fill=1, stroke=1)
        else:
            pdf.setStrokeColorRGB(*(MEAN_COLOR if kind == "mean" else GATE_COLOR))
            pdf.setLineWidth(1.8 if kind == "mean" else 1.0)
            if kind == "gate":
                pdf.setDash(3, 2)
            pdf.line(x, y + 1.5, x + 14, y + 1.5)
            pdf.setDash()
        pdf.setFillColorRGB(0.12, 0.12, 0.12)
        pdf.drawString(x + 18, y - 1, label)
        x += item_width


def _draw_plot(
    output: Path,
    rows: list[dict[str, float | int]],
    *,
    title: str,
    y_label: str,
    mean_field: str,
    min_field: str,
    max_field: str,
    y_low: float,
    y_high: float,
    y_ticks: tuple[float, ...],
    gate: float,
    gate_note: str,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), invariant=1)
    pdf.setTitle(title)
    pdf.setAuthor("FPT26_data_review evidence pipeline")
    plot_width = PAGE_WIDTH - LEFT - RIGHT
    plot_height = PAGE_HEIGHT - BOTTOM - TOP
    x_low = 0.0
    x_high = math.log10(8192)

    def x_position(token: int) -> float:
        return LEFT + math.log10(max(token, 1)) / x_high * plot_width

    def y_position(value: float) -> float:
        return BOTTOM + (value - y_low) / (y_high - y_low) * plot_height

    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    pdf.setFillColorRGB(0.08, 0.08, 0.08)
    pdf.setFont("Helvetica-Bold", 10.5)
    pdf.drawString(LEFT, PAGE_HEIGHT - 17, title)
    _draw_legend(pdf, PAGE_HEIGHT - 34)
    pdf.setFillColorRGB(0.28, 0.28, 0.28)
    pdf.setFont("Helvetica", 6.7)
    pdf.drawString(
        LEFT,
        PAGE_HEIGHT - 47,
        "Selected: MXFP4 RS2 activation/base + sparse residual + MXFP8-E4M3 log, R=7",
    )

    for tick in y_ticks:
        y = y_position(tick)
        pdf.setStrokeColorRGB(0.87, 0.88, 0.89)
        pdf.setLineWidth(0.45)
        pdf.line(LEFT, y, LEFT + plot_width, y)
        pdf.setFillColorRGB(0.25, 0.25, 0.25)
        pdf.setFont("Helvetica", 7.3)
        pdf.drawRightString(LEFT - 6, y - 2.4, f"{tick:.3f}")

    x_ticks = (1, 4, 16, 64, 256, 1024, 4096, 8192)
    for tick in x_ticks:
        x = x_position(tick)
        pdf.setStrokeColorRGB(0.91, 0.92, 0.93)
        pdf.setLineWidth(0.4)
        pdf.line(x, BOTTOM, x, BOTTOM + plot_height)
        pdf.setFillColorRGB(0.25, 0.25, 0.25)
        pdf.setFont("Helvetica", 7.2)
        if tick == 1:
            pdf.drawString(x, BOTTOM - 11, str(tick))
        elif tick == 8192:
            pdf.drawRightString(x, BOTTOM - 11, str(tick))
        else:
            pdf.drawCentredString(x, BOTTOM - 11, str(tick))

    band = pdf.beginPath()
    for index, row in enumerate(rows):
        x = x_position(int(row["token_index"]))
        y = y_position(float(row[max_field]))
        (band.moveTo if index == 0 else band.lineTo)(x, y)
    for row in reversed(rows):
        band.lineTo(
            x_position(int(row["token_index"])),
            y_position(float(row[min_field])),
        )
    band.close()
    pdf.setFillColorRGB(*BAND_COLOR)
    pdf.setStrokeColorRGB(*EDGE_COLOR)
    pdf.setLineWidth(0.35)
    pdf.drawPath(band, fill=1, stroke=1)

    mean = pdf.beginPath()
    for index, row in enumerate(rows):
        x = x_position(int(row["token_index"]))
        y = y_position(float(row[mean_field]))
        (mean.moveTo if index == 0 else mean.lineTo)(x, y)
    pdf.setStrokeColorRGB(*MEAN_COLOR)
    pdf.setLineWidth(1.45)
    pdf.drawPath(mean, fill=0, stroke=1)

    gate_y = y_position(gate)
    pdf.setStrokeColorRGB(*GATE_COLOR)
    pdf.setLineWidth(0.9)
    pdf.setDash(3, 2)
    pdf.line(LEFT, gate_y, LEFT + plot_width, gate_y)
    pdf.setDash()
    pdf.setFillColorRGB(*GATE_COLOR)
    pdf.setFont("Helvetica", 6.8)
    pdf.drawRightString(LEFT + plot_width - 3, gate_y + 3, gate_note)

    pdf.setStrokeColorRGB(0.12, 0.12, 0.12)
    pdf.setLineWidth(0.75)
    pdf.rect(LEFT, BOTTOM, plot_width, plot_height, fill=0, stroke=1)
    pdf.setFillColorRGB(0.12, 0.12, 0.12)
    pdf.setFont("Helvetica", 8.2)
    pdf.drawCentredString(LEFT + plot_width / 2, 15, "Decode token index (log scale)")
    pdf.saveState()
    pdf.translate(13, BOTTOM + plot_height / 2)
    pdf.rotate(90)
    pdf.drawCentredString(0, 0, y_label)
    pdf.restoreState()
    pdf.setFillColorRGB(0.33, 0.33, 0.33)
    pdf.setFont("Helvetica", 6.3)
    pdf.drawRightString(
        PAGE_WIDTH - RIGHT,
        4.5,
        "Held-out nominal synthetic Q/DQ; 3 seeds x {random,zero} S0; S is KxV; rel-L2 floor=1e-12",
    )
    pdf.showPage()
    pdf.save()


def generate_plots(
    matrix_paths: list[Path],
    selection_path: Path,
    aggregate_path: Path,
    cosine_path: Path,
    state_path: Path,
    manifest_path: Path,
) -> None:
    variant, trace_metadata, traces = _load_traces(matrix_paths, selection_path)
    rows = _aggregate_traces(traces)
    _write_aggregate(aggregate_path, rows)

    _draw_plot(
        cosine_path,
        rows,
        title="Held-out synthetic output similarity",
        y_label="Cosine similarity versus FP32",
        mean_field="output_cosine_mean",
        min_field="output_cosine_min",
        max_field="output_cosine_max",
        y_low=0.99,
        y_high=1.0,
        y_ticks=(0.990, 0.992, 0.994, 0.996, 0.998, 1.000),
        gate=0.99,
        gate_note="cosine >= 0.99 at required checkpoints",
    )
    _draw_plot(
        state_path,
        rows,
        title="Held-out synthetic recurrent-state drift",
        y_label="State relative L2 error versus FP32",
        mean_field="state_rel_l2_mean",
        min_field="state_rel_l2_min",
        max_field="state_rel_l2_max",
        y_low=0.0,
        y_high=0.11,
        y_ticks=(0.000, 0.020, 0.040, 0.060, 0.080, 0.100),
        gate=0.10,
        gate_note="state rel L2 <= 0.10 at token 8192",
    )

    checkpoint_rows = {
        int(row["token_index"]): row
        for row in rows
        if int(row["token_index"]) in CHECKPOINTS
    }
    final_rows = [trace[-1] for trace in traces]
    gate_pass = all(
        float(trace[checkpoint - 1]["output_cosine_fp32"]) >= 0.99
        for trace in traces
        for checkpoint in CHECKPOINTS
    ) and all(float(row["state_rel_l2"]) <= 0.10 for row in final_rows)
    if not gate_pass:
        raise ValueError("held-out data no longer pass the preregistered synthetic gate")

    manifest = {
        "schema": 1,
        "status": "PASS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": "held-out nominal synthetic Q/DQ visualization",
        "selected_variant": variant,
        "trace_count": len(traces),
        "seeds": sorted({int(item["seed"]) for item in trace_metadata}),
        "initial_states": sorted(
            {str(item["initial_state"]) for item in trace_metadata}
        ),
        "required_checkpoints": list(CHECKPOINTS),
        "synthetic_gate": "PASS",
        "physical_evidence": "NOT_RUN",
        "closed_loop_qwen_evidence": "BLOCKED_EXTERNAL",
        "inputs": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in matrix_paths
        },
        "selection": {
            "path": selection_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(selection_path),
        },
        "traces": trace_metadata,
        "aggregate": {
            "path": aggregate_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(aggregate_path),
            "all_token_min_output_cosine": min(
                float(row["output_cosine_min"]) for row in rows
            ),
            "all_token_max_state_rel_l2": max(
                float(row["state_rel_l2_max"]) for row in rows
            ),
            "checkpoint_min_output_cosine": min(
                float(row["output_cosine_min"]) for row in checkpoint_rows.values()
            ),
            "token_8192_max_state_rel_l2": max(
                float(row["state_rel_l2"]) for row in final_rows
            ),
        },
        "outputs": {
            cosine_path.relative_to(ROOT).as_posix(): _sha256(cosine_path),
            state_path.relative_to(ROOT).as_posix(): _sha256(state_path),
        },
        "source_hashes": {
            "scripts/plot_write_log_held_out.py": _sha256(Path(__file__)),
        },
        "limitations": [
            "synthetic nominal traces only",
            "floating Q/DQ candidate rather than encoded-integer or RTL execution",
            "not closed-loop Qwen quality evidence",
            "logical state bytes are not physical BRAM/URAM allocation",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-manifest", action="append", type=Path)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--aggregate", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-cosine", type=Path, default=DEFAULT_COSINE)
    parser.add_argument("--output-state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    matrix_paths = (
        [_resolve(path) for path in args.matrix_manifest]
        if args.matrix_manifest
        else list(DEFAULT_MATRICES)
    )
    generate_plots(
        matrix_paths,
        _resolve(args.selection),
        _resolve(args.aggregate),
        _resolve(args.output_cosine),
        _resolve(args.output_state),
        _resolve(args.manifest),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

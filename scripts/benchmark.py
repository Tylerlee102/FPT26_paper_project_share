from __future__ import annotations

import csv
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reports.report_parsers import parse_total_power, parse_utilization, parse_wns
from .paper_pack import require_release_gate


ROOT = Path(__file__).resolve().parents[1]
NUMBERS = ROOT / "paper" / "numbers.json"
PROVENANCE = ROOT / "paper" / "provenance.json"
BENCHMARK_DIR = ROOT / "reports" / "benchmark"
SWEEP_CSV = BENCHMARK_DIR / "sweep.csv"
BLOCK_SIZE_ACCURACY_CSV = BENCHMARK_DIR / "block_size_accuracy.csv"
SWEEP_DIR = BENCHMARK_DIR / "sweeps"
NOTES = BENCHMARK_DIR / "notes.md"
EXTRACTOR = "scripts/benchmark.py"
FALLBACK_SHA = "0" * 40


@dataclass(frozen=True)
class SourceRef:
    source: str
    line: int | None = None


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _git_sha() -> tuple[str, str | None]:
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        sha = result.stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}", sha):
            return sha, None
    except Exception:
        pass
    return FALLBACK_SHA, "No git commit is available in this workspace; using an all-zero placeholder SHA."


def _find_line(path: Path, pattern: str) -> int | None:
    if not path.exists():
        return None
    for index, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if pattern in line:
            return index
    return None


def _number(
    out: dict[str, dict[str, Any]],
    provenance: dict[str, dict[str, Any]],
    *,
    key: str,
    value: int | float | str | list[Any],
    units: str,
    source: SourceRef,
    git_sha: str,
    timestamp: str,
    notes: str = "",
) -> None:
    record: dict[str, Any] = {
        "value": value,
        "units": units,
        "source": source.source,
        "source_line": source.line,
        "extractor": EXTRACTOR,
        "git_sha": git_sha,
        "timestamp": timestamp,
    }
    if notes:
        record["notes"] = notes
    out[key] = record
    provenance[key] = {
        "git_sha": git_sha,
        "timestamp": timestamp,
        "source": source.source,
        "source_line": source.line,
        "extractor": EXTRACTOR,
        "notes": notes,
    }


def _latency_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No latency rows in {path}")
    return rows[0]


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _find_csv_line(path: Path, predicate) -> int | None:
    for index, row in enumerate(_csv_rows(path), start=2):
        if predicate(row):
            return index
    return None


def _latest_hls_source_mtime() -> float:
    patterns = ("hls/include/*.hpp", "hls/src/*.cpp", "hls/tb/*.cpp")
    sources: list[Path] = []
    for pattern in patterns:
        sources.extend(ROOT.glob(pattern))
    return max(path.stat().st_mtime for path in sources)


def _cosim_is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    return path.stat().st_mtime + 1.0 >= _latest_hls_source_mtime()


def _parse_hls_util(path: Path) -> dict[str, float | int]:
    text = _read(path)
    fmax_match = re.search(r"Estimated Fmax:\s*([0-9.]+)\s*MHz", text)
    latency_match = re.search(r"Latency:\s*(\d+)\s*cycles", text)
    bram_match = re.search(r"BRAM utilization:\s*([0-9.]+)%", text)
    dsp_match = re.search(r"DSP utilization:\s*([0-9.]+)%", text)
    lut_match = re.search(r"LUT utilization:\s*([0-9.]+)%", text)
    ii_match = re.search(r"Inner-loop II:\s*(\d+)", text)
    if not all((fmax_match, latency_match, bram_match, dsp_match, lut_match, ii_match)):
        raise ValueError(f"Missing HLS util field in {path}")
    return {
        "fmax_mhz": float(fmax_match.group(1)),
        "latency_cycles": int(latency_match.group(1)),
        "latency_us": int(latency_match.group(1)) * 4.0 / 1000.0,
        "bram_pct": float(bram_match.group(1)),
        "dsp_pct": float(dsp_match.group(1)),
        "lut_pct": float(lut_match.group(1)),
        "ii": int(ii_match.group(1)),
    }


def _sweep_cosim_metrics(config_dir: Path) -> tuple[int, int, float, SourceRef, str] | None:
    latency_path = config_dir / "cosim" / "latency.csv"
    if not latency_path.exists():
        return None
    row = _latency_row(latency_path)
    tokens = int(row["tokens"])
    latency_cycles = int(row["latency_avg_cycles"])
    latency_us = latency_cycles * 4.0 / 1000.0
    return tokens, latency_cycles, latency_us, SourceRef(_rel(latency_path), 2), "cosim"


def _metric_from_markdown_table(path: Path, row_name: str, column_name: str) -> tuple[float, int]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header: list[str] | None = None
    for index, line in enumerate(lines, start=1):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None and column_name in cells:
            header = cells
            continue
        if header and cells and cells[0] == row_name:
            col = header.index(column_name)
            return float(cells[col]), index
    raise ValueError(f"Could not find {row_name}/{column_name} in {path}")


def _write_sweep_csv(rows: list[dict[str, float | int | str]]) -> None:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "config",
        "format",
        "block_size",
        "p_k",
        "p_v",
        "tokens",
        "latency_cycles_avg",
        "latency_us",
        "power_w",
        "energy_mj",
        "lut_pct",
        "bram_pct",
        "dsp_pct",
        "source_latency",
        "source_power",
        "source_util",
        "latency_source_kind",
        "impl_status",
    ]
    with SWEEP_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_block_size_accuracy_csv(rows: list[dict[str, float | int | str]]) -> None:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "config",
        "format",
        "block_size",
        "state_format",
        "state_block_size",
        "output_rel_l2",
        "output_cosine",
        "state_rel_l2",
        "source",
    ]
    with BLOCK_SIZE_ACCURACY_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    try:
        require_release_gate()
    except RuntimeError as exc:
        print(str(exc))
        return 1
    timestamp = datetime.now(timezone.utc).isoformat()
    git_sha, git_note = _git_sha()
    numbers: dict[str, dict[str, Any]] = {}
    provenance: dict[str, dict[str, Any]] = {}

    latency_path = ROOT / "reports" / "cosim" / "latency.csv"
    impl_power_path = ROOT / "reports" / "vivado" / "impl_power.rpt"
    impl_util_path = ROOT / "reports" / "vivado" / "impl_util.rpt"
    impl_timing_path = ROOT / "reports" / "vivado" / "impl_timing.rpt"
    synth_timing_path = ROOT / "reports" / "vivado" / "synth_timing.rpt"
    csynth_util_path = ROOT / "reports" / "csynth" / "util.md"
    quant_path = ROOT / "reports" / "golden" / "quantization.md"
    quant_b16_path = ROOT / "reports" / "golden" / "quantization_b16.md"
    ablation_path = ROOT / "reports" / "golden" / "quantization_ablation.md"
    csim_path = ROOT / "reports" / "csim" / "results.md"
    qwen_status_path = ROOT / "reports" / "golden" / "qwen_capture_status.md"
    state_drift_path = ROOT / "reports" / "benchmark" / "state_drift.csv"
    state_boundary_path = ROOT / "reports" / "benchmark" / "state_boundary.csv"
    stress_accuracy_path = ROOT / "reports" / "benchmark" / "stress_accuracy.csv"
    storage_overhead_path = ROOT / "reports" / "benchmark" / "storage_overhead.csv"
    offchip_traffic_path = ROOT / "reports" / "benchmark" / "offchip_state_traffic.csv"

    cosim_fresh = _cosim_is_fresh(latency_path)
    cosim_row = _latency_row(latency_path) if latency_path.exists() else {}
    csynth_metrics = _parse_hls_util(csynth_util_path)
    if cosim_fresh:
        latency_cycles = int(cosim_row["latency_avg_cycles"])
        tokens = int(cosim_row["tokens"])
        latency_us = latency_cycles * 4.0 / 1000.0
        latency_source = SourceRef(_rel(latency_path), 2)
        latency_source_kind = "cosim"
        latency_note = ""
    else:
        latency_cycles = int(csynth_metrics["latency_cycles"])
        tokens = int(cosim_row.get("tokens", "0") or 0)
        latency_us = float(csynth_metrics["latency_us"])
        latency_source = SourceRef(_rel(csynth_util_path), _find_line(csynth_util_path, "Latency:"))
        latency_source_kind = "csynth_estimate"
        latency_note = "Current RTL cosim is unavailable or stale; using HLS csynth latency until cosim is rerun."
    power = parse_total_power(_read(impl_power_path)).total_w
    energy_mj = power * latency_us / 1000.0
    impl_util = parse_utilization(_read(impl_util_path))
    impl_timing = parse_wns(_read(impl_timing_path))
    synth_timing = parse_wns(_read(synth_timing_path))
    csynth_fmax = float(csynth_metrics["fmax_mhz"])
    csynth_latency = int(csynth_metrics["latency_cycles"])

    sweep_rows: list[dict[str, float | int | str]] = [
        {
            "config": "ours_mxfp4_b32_pk16_pv8",
            "format": "MXFP4",
            "block_size": 32,
            "p_k": 16,
            "p_v": 8,
            "tokens": tokens,
            "latency_cycles_avg": latency_cycles,
            "latency_us": f"{latency_us:.3f}",
            "power_w": f"{power:.3f}",
            "energy_mj": f"{energy_mj:.3f}",
            "lut_pct": f"{impl_util.lut_pct:.2f}",
            "bram_pct": f"{impl_util.bram_pct:.2f}",
            "dsp_pct": f"{impl_util.dsp_pct:.2f}",
            "source_latency": latency_source.source,
            "source_power": _rel(impl_power_path),
            "source_util": _rel(impl_util_path),
            "latency_source_kind": latency_source_kind,
            "impl_status": "post_impl",
        }
    ]

    for sweep_util in sorted(SWEEP_DIR.glob("*/util.md")):
        config = sweep_util.parent.name
        if config == "parallel_pk16_pv8_b32":
            continue
        metrics = _parse_hls_util(sweep_util)
        parts = {
            "parallel_pk8_pv4_b32": (32, 8, 4),
            "parallel_pk32_pv16_b32": (32, 32, 16),
            "block_b16_pk16_pv8": (16, 16, 8),
            "block_b16_pk32_pv16": (16, 32, 16),
        }
        if config not in parts:
            continue
        block_size, p_k, p_v = parts[config]
        sweep_tokens = 0
        sweep_latency_cycles = int(metrics["latency_cycles"])
        sweep_latency_us = float(metrics["latency_us"])
        sweep_latency_source = _rel(sweep_util)
        sweep_latency_source_kind = "csynth_estimate"
        cosim_metrics = _sweep_cosim_metrics(sweep_util.parent)
        if cosim_metrics is not None:
            sweep_tokens, sweep_latency_cycles, sweep_latency_us, cosim_source, sweep_latency_source_kind = cosim_metrics
            sweep_latency_source = cosim_source.source
        vivado_dir = sweep_util.parent / "vivado"
        sweep_power: float | str = ""
        sweep_energy: float | str = ""
        sweep_lut_pct = float(metrics["lut_pct"])
        sweep_bram_pct = float(metrics["bram_pct"])
        sweep_dsp_pct = float(metrics["dsp_pct"])
        source_power = ""
        source_util = _rel(sweep_util)
        impl_status = "csynth_only"
        if (vivado_dir / "impl_util.rpt").exists() and (vivado_dir / "impl_power.rpt").exists():
            sweep_impl_util = parse_utilization(_read(vivado_dir / "impl_util.rpt"))
            sweep_impl_power = parse_total_power(_read(vivado_dir / "impl_power.rpt"))
            sweep_lut_pct = sweep_impl_util.lut_pct
            sweep_bram_pct = sweep_impl_util.bram_pct
            sweep_dsp_pct = sweep_impl_util.dsp_pct
            sweep_power = sweep_impl_power.total_w
            sweep_energy = sweep_impl_power.total_w * sweep_latency_us / 1000.0
            source_power = _rel(vivado_dir / "impl_power.rpt")
            source_util = _rel(vivado_dir / "impl_util.rpt")
            impl_status = "post_impl"
        sweep_rows.append(
            {
                "config": config,
                "format": "MXFP4",
                "block_size": block_size,
                "p_k": p_k,
                "p_v": p_v,
                "tokens": sweep_tokens,
                "latency_cycles_avg": sweep_latency_cycles,
                "latency_us": f"{sweep_latency_us:.3f}",
                "power_w": "" if sweep_power == "" else f"{float(sweep_power):.3f}",
                "energy_mj": "" if sweep_energy == "" else f"{float(sweep_energy):.3f}",
                "lut_pct": f"{sweep_lut_pct:.2f}",
                "bram_pct": f"{sweep_bram_pct:.2f}",
                "dsp_pct": f"{sweep_dsp_pct:.2f}",
                "source_latency": sweep_latency_source,
                "source_power": source_power,
                "source_util": source_util,
                "latency_source_kind": sweep_latency_source_kind,
                "impl_status": impl_status,
            }
        )
    _write_sweep_csv(sweep_rows)

    external_note = "Cited from Gupta et al., arXiv:2603.05931v1, Tables IV-V."
    _number(
        numbers,
        provenance,
        key="h100_baseline_latency_us",
        value=285.0,
        units="us_per_token",
        source=SourceRef("external", None),
        git_sha=git_sha,
        timestamp=timestamp,
        notes=external_note,
    )
    _number(
        numbers,
        provenance,
        key="h100_baseline_power_w",
        value=350.0,
        units="watts_tdp",
        source=SourceRef("external", None),
        git_sha=git_sha,
        timestamp=timestamp,
        notes=external_note,
    )
    _number(
        numbers,
        provenance,
        key="h100_baseline_energy_mj",
        value=99.8,
        units="mj_per_token",
        source=SourceRef("external", None),
        git_sha=git_sha,
        timestamp=timestamp,
        notes=external_note,
    )
    _number(
        numbers,
        provenance,
        key="usc_baseline_latency_us",
        value=63.2,
        units="us_per_token",
        source=SourceRef("external", None),
        git_sha=git_sha,
        timestamp=timestamp,
        notes="Cited from Gupta et al., arXiv:2603.05931v1, Table IV, Hiter=8 @300 MHz.",
    )
    _number(
        numbers,
        provenance,
        key="usc_baseline_energy_mj",
        value=9.5,
        units="mj_per_token_upper_bound",
        source=SourceRef("external", None),
        git_sha=git_sha,
        timestamp=timestamp,
        notes="Cited from Gupta et al., arXiv:2603.05931v1, Table V, Hiter=8 board-TDP upper bound.",
    )
    _number(
        numbers,
        provenance,
        key="usc_baseline_power_w",
        value=150.0,
        units="watts_tdp_upper_bound",
        source=SourceRef("external", None),
        git_sha=git_sha,
        timestamp=timestamp,
        notes="Cited from Gupta et al., arXiv:2603.05931v1, Table V board-level TDP upper bound.",
    )

    sweep_source = SourceRef(_rel(SWEEP_CSV), 2)
    if latency_path.exists():
        _number(numbers, provenance, key="ours_mxfp4_b32_tokens_cosim", value=tokens, units="tokens", source=SourceRef(_rel(latency_path), 2), git_sha=git_sha, timestamp=timestamp, notes="0 means no fresh cosim token count is available." if tokens == 0 else "")
    _number(numbers, provenance, key="ours_mxfp4_b32_latency_cycles", value=latency_cycles, units="cycles", source=latency_source, git_sha=git_sha, timestamp=timestamp, notes=latency_note)
    _number(numbers, provenance, key="ours_mxfp4_b32_latency_us", value=round(latency_us, 3), units="us_per_token", source=sweep_source, git_sha=git_sha, timestamp=timestamp, notes=latency_note)
    _number(numbers, provenance, key="ours_mxfp4_b32_latency_source_kind", value=latency_source_kind, units="status", source=sweep_source, git_sha=git_sha, timestamp=timestamp, notes=latency_note)
    _number(numbers, provenance, key="ours_mxfp4_b32_power_w", value=round(power, 3), units="watts", source=SourceRef(_rel(impl_power_path), _find_line(impl_power_path, "Total On-Chip Power")), git_sha=git_sha, timestamp=timestamp)
    _number(numbers, provenance, key="ours_mxfp4_b32_energy_mj", value=round(energy_mj, 3), units="mj_per_token", source=sweep_source, git_sha=git_sha, timestamp=timestamp)
    _number(numbers, provenance, key="ours_mxfp4_b32_lut_pct", value=impl_util.lut_pct, units="percent", source=SourceRef(_rel(impl_util_path), _find_line(impl_util_path, "CLB LUTs")), git_sha=git_sha, timestamp=timestamp)
    _number(numbers, provenance, key="ours_mxfp4_b32_bram_pct", value=impl_util.bram_pct, units="percent", source=SourceRef(_rel(impl_util_path), _find_line(impl_util_path, "Block RAM Tile")), git_sha=git_sha, timestamp=timestamp)
    _number(numbers, provenance, key="ours_mxfp4_b32_dsp_pct", value=impl_util.dsp_pct, units="percent", source=SourceRef(_rel(impl_util_path), _find_line(impl_util_path, "DSPs")), git_sha=git_sha, timestamp=timestamp)
    _number(numbers, provenance, key="ours_mxfp4_b32_impl_wns_ns", value=impl_timing.wns_ns, units="ns", source=SourceRef(_rel(impl_timing_path), _find_line(impl_timing_path, "Worst Slack")), git_sha=git_sha, timestamp=timestamp)
    _number(numbers, provenance, key="ours_mxfp4_b32_synth_wns_ns", value=synth_timing.wns_ns, units="ns", source=SourceRef(_rel(synth_timing_path), _find_line(synth_timing_path, "Worst Slack")), git_sha=git_sha, timestamp=timestamp)
    _number(numbers, provenance, key="ours_mxfp4_b32_csynth_fmax_mhz", value=csynth_fmax, units="mhz", source=SourceRef(_rel(csynth_util_path), _find_line(csynth_util_path, "Estimated Fmax")), git_sha=git_sha, timestamp=timestamp)
    _number(numbers, provenance, key="ours_mxfp4_b32_csynth_latency_cycles", value=csynth_latency, units="cycles", source=SourceRef(_rel(csynth_util_path), _find_line(csynth_util_path, "Latency:")), git_sha=git_sha, timestamp=timestamp)

    for row_index, sweep_row in enumerate(sweep_rows, start=2):
        config = str(sweep_row["config"])
        if config == "ours_mxfp4_b32_pk16_pv8":
            continue
        prefix = config.replace("parallel_", "ours_mxfp4_").replace("block_", "ours_mxfp4_")
        source = SourceRef(_rel(SWEEP_CSV), row_index)
        has_impl = sweep_row["impl_status"] == "post_impl"
        latency_notes = (
            "RTL cosim latency for this sweep point."
            if sweep_row["latency_source_kind"] == "cosim"
            else "HLS csynth latency estimate for this sweep point."
        )
        area_notes = (
            "Vivado post-implementation area for this sweep point."
            if has_impl
            else "HLS csynth estimate; Vivado implementation for this sweep point is pending."
        )
        _number(numbers, provenance, key=f"{prefix}_latency_us", value=float(sweep_row["latency_us"]), units="us_per_token", source=source, git_sha=git_sha, timestamp=timestamp, notes=latency_notes)
        _number(numbers, provenance, key=f"{prefix}_lut_pct", value=float(sweep_row["lut_pct"]), units="percent", source=source, git_sha=git_sha, timestamp=timestamp, notes=area_notes)
        _number(numbers, provenance, key=f"{prefix}_bram_pct", value=float(sweep_row["bram_pct"]), units="percent", source=source, git_sha=git_sha, timestamp=timestamp, notes=area_notes)
        _number(numbers, provenance, key=f"{prefix}_dsp_pct", value=float(sweep_row["dsp_pct"]), units="percent", source=source, git_sha=git_sha, timestamp=timestamp, notes=area_notes)
        if str(sweep_row["power_w"]):
            _number(numbers, provenance, key=f"{prefix}_power_w", value=float(sweep_row["power_w"]), units="watts", source=source, git_sha=git_sha, timestamp=timestamp, notes="Vivado implementation power for this sweep point.")

    speedup_vs_h100 = 285.0 / latency_us
    speedup_vs_usc = 63.2 / latency_us
    energy_eff_vs_h100 = 99.8 / energy_mj
    energy_eff_vs_usc = 9.5 / energy_mj
    _number(numbers, provenance, key="headline_speedup_vs_h100", value=round(speedup_vs_h100, 3), units="x", source=sweep_source, git_sha=git_sha, timestamp=timestamp, notes="Derived from h100_baseline_latency_us and ours_mxfp4_b32_latency_us.")
    _number(numbers, provenance, key="headline_speedup_vs_usc", value=round(speedup_vs_usc, 3), units="x", source=sweep_source, git_sha=git_sha, timestamp=timestamp, notes="Derived from usc_baseline_latency_us and ours_mxfp4_b32_latency_us.")
    _number(numbers, provenance, key="headline_energy_efficiency_vs_h100", value=round(energy_eff_vs_h100, 3), units="x", source=sweep_source, git_sha=git_sha, timestamp=timestamp, notes="Derived from h100_baseline_energy_mj and ours_mxfp4_b32_energy_mj.")
    _number(numbers, provenance, key="headline_energy_efficiency_vs_usc", value=round(energy_eff_vs_usc, 3), units="x", source=sweep_source, git_sha=git_sha, timestamp=timestamp, notes="Derived from usc_baseline_energy_mj upper bound and ours_mxfp4_b32_energy_mj.")

    quant_rows = {
        "synthetic_mxfp4_b32_output_rel_l2": ("MXFP4 B=32, state MXFP4 B=16", "Output rel L2"),
        "synthetic_mxfp4_b32_output_cosine": ("MXFP4 B=32, state MXFP4 B=16", "Output cosine"),
        "synthetic_mxfp4_b32_state_rel_l2": ("MXFP4 B=32, state MXFP4 B=16", "State rel L2"),
        "synthetic_mxfp4_b32_state_mxfp8_output_cosine": ("MXFP4 B=32, state MXFP8 B=16", "Output cosine"),
        "synthetic_int4_output_cosine": ("INT4 fallback", "Output cosine"),
    }
    for key, (row_name, column) in quant_rows.items():
        value, line = _metric_from_markdown_table(quant_path, row_name, column)
        _number(numbers, provenance, key=key, value=value, units="synthetic_metric", source=SourceRef(_rel(quant_path), line), git_sha=git_sha, timestamp=timestamp)

    block_accuracy_rows: list[dict[str, float | int | str]] = [
        {
            "config": "mxfp4_b32_state_mxfp4_b16",
            "format": "MXFP4",
            "block_size": 32,
            "state_format": "MXFP4",
            "state_block_size": 16,
            "output_rel_l2": numbers["synthetic_mxfp4_b32_output_rel_l2"]["value"],
            "output_cosine": numbers["synthetic_mxfp4_b32_output_cosine"]["value"],
            "state_rel_l2": numbers["synthetic_mxfp4_b32_state_rel_l2"]["value"],
            "source": _rel(quant_path),
        }
    ]
    if quant_b16_path.exists():
        quant_b16_rows = {
            "synthetic_mxfp4_b16_output_rel_l2": ("MXFP4 B=16, state MXFP4 B=16", "Output rel L2"),
            "synthetic_mxfp4_b16_output_cosine": ("MXFP4 B=16, state MXFP4 B=16", "Output cosine"),
            "synthetic_mxfp4_b16_state_rel_l2": ("MXFP4 B=16, state MXFP4 B=16", "State rel L2"),
            "synthetic_mxfp4_b16_state_mxfp8_output_cosine": ("MXFP4 B=16, state MXFP8 B=16", "Output cosine"),
        }
        for key, (row_name, column) in quant_b16_rows.items():
            value, line = _metric_from_markdown_table(quant_b16_path, row_name, column)
            _number(numbers, provenance, key=key, value=value, units="synthetic_metric", source=SourceRef(_rel(quant_b16_path), line), git_sha=git_sha, timestamp=timestamp)
        block_accuracy_rows.append(
            {
                "config": "mxfp4_b16_state_mxfp4_b16",
                "format": "MXFP4",
                "block_size": 16,
                "state_format": "MXFP4",
                "state_block_size": 16,
                "output_rel_l2": numbers["synthetic_mxfp4_b16_output_rel_l2"]["value"],
                "output_cosine": numbers["synthetic_mxfp4_b16_output_cosine"]["value"],
                "state_rel_l2": numbers["synthetic_mxfp4_b16_state_rel_l2"]["value"],
                "source": _rel(quant_b16_path),
            }
        )
    _write_block_size_accuracy_csv(block_accuracy_rows)

    for tensor in ("q", "k", "v", "gate", "state"):
        value, line = _metric_from_markdown_table(ablation_path, tensor, "Output cosine")
        _number(numbers, provenance, key=f"ablation_{tensor}_output_cosine", value=value, units="synthetic_metric", source=SourceRef(_rel(ablation_path), line), git_sha=git_sha, timestamp=timestamp)

    csim_text = _read(csim_path)
    match = re.search(r"vectors=(\d+)/(\d+)", csim_text)
    if match:
        passed, total = int(match.group(1)), int(match.group(2))
        csim_stale = "Status: stale" in csim_text
        csim_note = "Last C-sim log predates current HLS sources; rerun required." if csim_stale else ""
        _number(numbers, provenance, key="hls_csim_vectors_passed", value=passed, units="vectors", source=SourceRef(_rel(csim_path), _find_line(csim_path, "vectors=")), git_sha=git_sha, timestamp=timestamp, notes=csim_note)
        _number(numbers, provenance, key="hls_csim_vectors_total", value=total, units="vectors", source=SourceRef(_rel(csim_path), _find_line(csim_path, "vectors=")), git_sha=git_sha, timestamp=timestamp, notes=csim_note)
        _number(
            numbers,
            provenance,
            key="hls_csim_freshness_status",
            value="stale" if csim_stale else "current",
            units="status",
            source=SourceRef(_rel(csim_path), _find_line(csim_path, "Status:")),
            git_sha=git_sha,
            timestamp=timestamp,
            notes=csim_note,
        )

    if qwen_status_path.exists():
        qwen_status_text = _read(qwen_status_path)
        status_match = re.search(r"Status:\s*([a-z_]+)", qwen_status_text)
        qwen_status = status_match.group(1) if status_match else "unknown"
        _number(
            numbers,
            provenance,
            key="qwen_capture_status",
            value=qwen_status,
            units="status",
            source=SourceRef(_rel(qwen_status_path), _find_line(qwen_status_path, "Status:")),
            git_sha=git_sha,
            timestamp=timestamp,
            notes="Realistic Qwen accuracy/PPL is paper-ready only when this value is `available`.",
        )

    if state_drift_path.exists():
        drift_rows = _csv_rows(state_drift_path)
        if drift_rows:
            final_row = drift_rows[-1]
            final_line = len(drift_rows) + 1
            drift_source = SourceRef(_rel(state_drift_path), final_line)
            _number(numbers, provenance, key="synthetic_drift_tokens", value=int(float(final_row["token"])), units="tokens", source=drift_source, git_sha=git_sha, timestamp=timestamp)
            _number(numbers, provenance, key="synthetic_drift_mxfp4_final_output_cosine", value=round(float(final_row["mxfp4_output_cosine"]), 6), units="cosine", source=drift_source, git_sha=git_sha, timestamp=timestamp)
            _number(numbers, provenance, key="synthetic_drift_mxfp4_final_state_rel_l2", value=round(float(final_row["mxfp4_state_rel_l2"]), 6), units="rel_l2", source=drift_source, git_sha=git_sha, timestamp=timestamp)
            _number(numbers, provenance, key="synthetic_drift_mxfp8_final_output_cosine", value=round(float(final_row["mxfp8_output_cosine"]), 6), units="cosine", source=drift_source, git_sha=git_sha, timestamp=timestamp)
            _number(numbers, provenance, key="synthetic_drift_mxfp8_final_state_rel_l2", value=round(float(final_row["mxfp8_state_rel_l2"]), 6), units="rel_l2", source=drift_source, git_sha=git_sha, timestamp=timestamp)

    if state_boundary_path.exists():
        boundary_rows = _csv_rows(state_boundary_path)
        for config in ("state_mxfp4_b16", "state_mxfp4_b32", "state_mxfp8_b16", "state_mxfp8_b32"):
            matching = [
                row
                for row in boundary_rows
                if row["state_config"] == config
            ]
            if not matching:
                continue
            row = max(matching, key=lambda item: int(item["checkpoint_token"]))
            line = _find_csv_line(
                state_boundary_path,
                lambda item, config=config, token=row["checkpoint_token"]: item["state_config"] == config
                and item["checkpoint_token"] == token,
            )
            source = SourceRef(_rel(state_boundary_path), line)
            key_prefix = f"synthetic_boundary_{config}"
            _number(numbers, provenance, key=f"{key_prefix}_checkpoint_token", value=int(row["checkpoint_token"]), units="tokens", source=source, git_sha=git_sha, timestamp=timestamp)
            _number(numbers, provenance, key=f"{key_prefix}_output_cosine", value=round(float(row["output_cosine"]), 6), units="cosine", source=source, git_sha=git_sha, timestamp=timestamp)
            _number(numbers, provenance, key=f"{key_prefix}_state_rel_l2", value=round(float(row["state_rel_l2"]), 6), units="rel_l2", source=source, git_sha=git_sha, timestamp=timestamp)

    if stress_accuracy_path.exists():
        for distribution, config in (
            ("combined_stress", "state_mxfp4_b16"),
            ("combined_stress", "state_mxfp8_b16"),
            ("outlier", "state_mxfp4_b16"),
            ("outlier", "state_mxfp8_b16"),
        ):
            line = _find_csv_line(
                stress_accuracy_path,
                lambda row, distribution=distribution, config=config: row["distribution"] == distribution
                and row["state_config"] == config,
            )
            rows = [
                row
                for row in _csv_rows(stress_accuracy_path)
                if row["distribution"] == distribution and row["state_config"] == config
            ]
            if not rows:
                continue
            worst_output_cosine = min(float(row["output_cosine_worst"]) for row in rows)
            worst_state_rel_l2 = max(float(row["state_rel_l2_worst"]) for row in rows)
            mean_output_cosine = sum(float(row["output_cosine_mean"]) for row in rows) / len(rows)
            source = SourceRef(_rel(stress_accuracy_path), line)
            stress_note = (
                "Aggregated across all matching rows for this distribution/state configuration "
                "in stress_accuracy.csv; see the CSV for per-seed inputs."
            )
            key_prefix = f"synthetic_stress_{distribution}_{config}"
            _number(numbers, provenance, key=f"{key_prefix}_mean_output_cosine", value=round(mean_output_cosine, 6), units="cosine", source=source, git_sha=git_sha, timestamp=timestamp, notes=stress_note)
            _number(numbers, provenance, key=f"{key_prefix}_worst_output_cosine", value=round(worst_output_cosine, 6), units="cosine", source=source, git_sha=git_sha, timestamp=timestamp, notes=stress_note)
            _number(numbers, provenance, key=f"{key_prefix}_worst_state_rel_l2", value=round(worst_state_rel_l2, 6), units="rel_l2", source=source, git_sha=git_sha, timestamp=timestamp, notes=stress_note)

    if storage_overhead_path.exists():
        storage_rows = _csv_rows(storage_overhead_path)
        for row in storage_rows:
            if row["format"] == "MXFP4" and row["block_size"] == "32":
                line = _find_csv_line(
                    storage_overhead_path,
                    lambda item: item["format"] == "MXFP4" and item["block_size"] == "32",
                )
                source = SourceRef(_rel(storage_overhead_path), line)
                _number(numbers, provenance, key="state_storage_mxfp4_b32_bytes", value=int(row["total_bytes"]), units="bytes", source=source, git_sha=git_sha, timestamp=timestamp)
                _number(numbers, provenance, key="state_storage_mxfp4_b32_reduction_vs_fp32_pct", value=round(float(row["reduction_vs_fp32_pct"]), 3), units="percent", source=source, git_sha=git_sha, timestamp=timestamp)
                _number(numbers, provenance, key="state_storage_mxfp4_b32_reduction_vs_bf16_pct", value=round(float(row["reduction_vs_bf16_pct"]), 3), units="percent", source=source, git_sha=git_sha, timestamp=timestamp)
                break

    if offchip_traffic_path.exists():
        traffic_rows = _csv_rows(offchip_traffic_path)
        for row in traffic_rows:
            if row["format"] == "MXFP4" and row["block_size"] == "32":
                line = _find_csv_line(
                    offchip_traffic_path,
                    lambda item: item["format"] == "MXFP4" and item["block_size"] == "32",
                )
                source = SourceRef(_rel(offchip_traffic_path), line)
                _number(numbers, provenance, key="offchip_mxfp4_b32_state_bytes", value=int(row["state_bytes"]), units="bytes", source=source, git_sha=git_sha, timestamp=timestamp)
                _number(numbers, provenance, key="offchip_mxfp4_b32_naive_three_pass_bytes_per_token", value=int(row["naive_three_pass_bytes"]), units="bytes_per_token", source=source, git_sha=git_sha, timestamp=timestamp)
                _number(numbers, provenance, key="offchip_mxfp4_b32_persistent_bytes_per_token", value=int(row["persistent_steady_state_bytes"]), units="bytes_per_token", source=source, git_sha=git_sha, timestamp=timestamp)
                break

    NUMBERS.parent.mkdir(parents=True, exist_ok=True)
    NUMBERS.write_text(json.dumps(numbers, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PROVENANCE.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    target_checks = [
        ("Fmax target", csynth_fmax >= 300.0, csynth_fmax >= 200.0, f"{csynth_fmax:.2f} MHz", "target >= 300 MHz, hard floor >= 200 MHz"),
        ("Latency target", latency_us <= 50.0, latency_us <= 100.0, f"{latency_us:.3f} us/token", "target <= 50 us, hard floor <= 100 us"),
        ("BRAM target", impl_util.bram_pct <= 50.0, impl_util.bram_pct <= 80.0, f"{impl_util.bram_pct:.2f}%", "target <= 50%, hard floor <= 80%"),
        ("DSP target", impl_util.dsp_pct <= 30.0, impl_util.dsp_pct <= 80.0, f"{impl_util.dsp_pct:.2f}%", "target <= 30%, hard floor <= 80%"),
        ("LUT target", impl_util.lut_pct <= 70.0, impl_util.lut_pct <= 90.0, f"{impl_util.lut_pct:.2f}%", "target <= 70%, hard floor <= 90%"),
        ("Power target", power <= 10.0, power <= 18.0, f"{power:.3f} W", "target <= 10 W, hard floor <= 18 W"),
        ("Speedup vs USC target", speedup_vs_usc >= 2.0, speedup_vs_usc >= 1.0, f"{speedup_vs_usc:.3f}x", "target >= 2x, hard floor >= 1x"),
        ("Speedup vs H100 target", speedup_vs_h100 >= 6.0, speedup_vs_h100 >= 4.5, f"{speedup_vs_h100:.3f}x", "target >= 6x, hard floor >= 4.5x"),
    ]
    target_lines = [
        f"- {name}: {'target met' if target_pass else 'hard floor met' if floor_pass else 'below hard floor'} ({current}; {requirement})."
        for name, target_pass, floor_pass, current, requirement in target_checks
    ]

    non_default_rows = [row for row in sweep_rows if row["config"] != "ours_mxfp4_b32_pk16_pv8"]
    non_default_cosim_done = all(row["latency_source_kind"] == "cosim" for row in non_default_rows)
    non_default_cosim_count = sum(1 for row in non_default_rows if row["latency_source_kind"] == "cosim")

    notes = [
        "# Benchmark Notes",
        "",
        "Generated Phase 6 benchmark extraction from currently available reports.",
        "",
        "## Completed",
        "",
        "- Extracted current MXFP4 B=32, P_K=16, P_V=8 latency, power, area, and synthetic quantization metrics.",
        "- Added B=16 synthetic block-size accuracy metrics from the deterministic calibration run.",
        "- Added external H100 and USC FPGA baselines with citation notes.",
        "- Wrote a Phase 6 sweep plan; non-default rows now include Vivado post-implementation area/power when available.",
        f"- Non-default RTL cosim latency is available for {non_default_cosim_count}/{len(non_default_rows)} sweep rows.",
        f"- Extracted the final default {tokens}-token RTL cosim result and used it for default latency extraction." if cosim_fresh and tokens >= 64 else "- Default RTL cosim is unavailable or stale; default latency falls back to HLS csynth.",
        "- HLS C-sim report is fresh for the current HLS sources." if "Status: stale" not in csim_text else "- HLS C-sim report is stale and must be rerun.",
        "- Added long-token state drift, stress-distribution, state-boundary, storage-overhead, and off-chip traffic metrics when their reports are present.",
        "- Git SHA resolved from repository HEAD." if not git_note else "- Git SHA currently uses the all-zero fallback because no repository commit is available.",
        "",
        "## Remaining Phase 6 Gaps",
        "",
        "- Non-default sweep latency values are still partly HLS csynth estimates; post-implementation latency requires completed RTL cosim per configuration." if not non_default_cosim_done else None,
        "- Rerun 64-token RTL cosim for the final tile-streamed RTL; current default latency uses csynth because cosim is stale or unavailable." if not (cosim_fresh and tokens >= 64) else None,
        "- Rerun `make hls-csim` after the Phase 6 loop-tiling edits; the last available C-sim log predates those source changes." if "Status: stale" in csim_text else None,
        "- Add Qwen-captured realistic accuracy/PPL numbers; current metrics are synthetic only. See `reports/golden/qwen_capture_status.md`.",
        "",
        "## Headline Target Check",
        "",
        *target_lines,
        "",
    ]
    NOTES.write_text("\n".join(line for line in notes if line is not None), encoding="utf-8")
    print(f"Wrote {_rel(NUMBERS)}, {_rel(PROVENANCE)}, and {_rel(SWEEP_CSV)}")
    if git_note:
        print(git_note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Summarize a completed XSim throughput benchmark and bound trace runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "reports" / "cosim" / "corrected" / "rs2_current" / "xsim_runtime"
)
DEFAULT_XSIM_LOG = DEFAULT_OUTPUT / "raw" / "xsim_token0.log"
DEFAULT_DIRECT_LOG = (
    ROOT
    / "reports"
    / "cosim"
    / "corrected"
    / "rs2_fast_direct_rtl_trace64"
    / "raw"
    / "verilator_run.log"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _single(pattern: str, text: str, label: str) -> re.Match[str]:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if match is None:
        raise ValueError(f"missing {label}")
    return match


def _elapsed_seconds(value: str) -> int:
    hours, minutes, seconds = (int(part) for part in value.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def _archive(source: Path, target: Path) -> dict[str, object]:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return {
        "path": _relative(target),
        "bytes": target.stat().st_size,
        "sha256": _sha256(target),
        "source": _relative(source),
        "source_sha256": _sha256(source),
    }


def build(xsim_log: Path, direct_log: Path, output_dir: Path) -> dict[str, object]:
    for path in (xsim_log, direct_log):
        if not path.is_file():
            raise FileNotFoundError(path)

    xsim_text = xsim_log.read_text(encoding="utf-8", errors="replace")
    direct_text = direct_log.read_text(encoding="utf-8", errors="replace")
    benchmark = _single(
        r"RS2_DIRECT_RTL command=1 cycles=(\d+) status=(\d+) generation=(\d+)",
        xsim_text,
        "XSim LOAD result",
    )
    pass_row = _single(
        r"RS2_DIRECT_RTL_BENCHMARK PASS tokens=(\d+)",
        xsim_text,
        "XSim benchmark PASS marker",
    )
    elapsed = _single(
        r"elapsed = (\d{2}:\d{2}:\d{2})",
        xsim_text,
        "XSim elapsed time",
    )
    cpu = _single(
        r"Simulation CPU Usage: (\d+) ms",
        xsim_text,
        "XSim CPU usage",
    )

    xsim_cycles = int(benchmark.group(1))
    elapsed_seconds = _elapsed_seconds(elapsed.group(1))
    if elapsed_seconds <= 0:
        raise ValueError("XSim elapsed time must be positive")
    cycles_per_second = xsim_cycles / elapsed_seconds
    direct_cycles = [
        int(value)
        for value in re.findall(r"RS2_DIRECT_RTL command=\d+ cycles=(\d+)", direct_text)
    ]
    if len(direct_cycles) != 66:
        raise ValueError(f"expected 66 direct-RTL commands, found {len(direct_cycles)}")
    full_trace_cycles = sum(direct_cycles)
    projected_seconds = full_trace_cycles / cycles_per_second

    raw_dir = output_dir / "raw"
    xsim_artifact = _archive(xsim_log, raw_dir / "xsim_token0.log")
    direct_artifact = _archive(direct_log, raw_dir / "verilator_trace64.log")
    payload: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "scope": "official XSim random-state LOAD throughput benchmark",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": {
            "tokens": int(pass_row.group(1)),
            "command": "LOAD",
            "cycles": xsim_cycles,
            "status_code": int(benchmark.group(2)),
            "generation": int(benchmark.group(3)),
            "elapsed_seconds": elapsed_seconds,
            "cpu_milliseconds": int(cpu.group(1)),
            "cycles_per_second": cycles_per_second,
        },
        "full_trace_projection": {
            "commands": len(direct_cycles),
            "tokens": 64,
            "cycles": full_trace_cycles,
            "projected_seconds": projected_seconds,
            "projected_hours": projected_seconds / 3600.0,
            "official_xsim_64_token_status": "NOT_RUN",
        },
        "claim_boundary": [
            "The random-state LOAD completed successfully in official XSim.",
            "The projection applies the measured LOAD throughput to the known full-trace cycle count.",
            "This benchmark is runtime evidence, not 64-token official-XSim parity evidence.",
        ],
        "raw_artifacts": {
            "xsim_token0": xsim_artifact,
            "verilator_trace64": direct_artifact,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rs2_xsim_runtime.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xsim-log", type=Path, default=DEFAULT_XSIM_LOG)
    parser.add_argument("--direct-log", type=Path, default=DEFAULT_DIRECT_LOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = build(
        _resolve(args.xsim_log),
        _resolve(args.direct_log),
        _resolve(args.output),
    )
    print(json.dumps(result["full_trace_projection"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

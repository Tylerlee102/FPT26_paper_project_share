"""Extract the bounded corrected-kernel RTL co-simulation smoke result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SMOKE = ROOT / "reports" / "cosim" / "corrected" / "smoke_1token"
SOURCE_GLOBS = (
    "hls/include/*.hpp",
    "hls/src/*.cpp",
    "hls/tb/*.cpp",
    "hls/tcl/run_cosim.tcl",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _source_hashes() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): _sha256(path)
        for pattern in SOURCE_GLOBS
        for path in sorted(ROOT.glob(pattern))
    }


def _parse_hms(value: str) -> int:
    hours, minutes, seconds = (int(field) for field in value.split(":"))
    return 3600 * hours + 60 * minutes + seconds


def _parse_progress(log: str) -> tuple[int, int, int]:
    matches = re.findall(
        r"RTL Simulation\s*:\s*(\d+)\s*/\s*(\d+).*?@\s*\"(\d+)\"",
        log,
    )
    if not matches:
        raise ValueError("XSIM log has no inter-transaction progress")
    completed, total, simulation_time = matches[-1]
    return int(completed), int(total), int(simulation_time)


def _parse_c_tb(log: str) -> tuple[int, int]:
    match = re.search(
        r"tb_gdn_top PASS hand_commands=(\d+) oracle_steps=(\d+)", log
    )
    if match is None:
        raise ValueError("C testbench PASS marker is absent")
    return int(match.group(1)), int(match.group(2))


def generate_report(smoke: Path) -> dict[str, object]:
    raw = smoke / "raw"
    trace_path = smoke / "trace.bin"
    trace_manifest_path = smoke / "trace_manifest.json"
    xsim_path = raw / "xsim.log"
    solution_path = raw / "u55c_250mhz.log"
    cosim_report_path = raw / "gdn_top_cosim.rpt"
    c_tb_path = raw / "c_tb.log"
    frozen_extraction_path = raw / "extraction_at_run.json"
    required = (
        trace_path,
        trace_manifest_path,
        xsim_path,
        solution_path,
        cosim_report_path,
        c_tb_path,
    )
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)

    trace_manifest = json.loads(trace_manifest_path.read_text(encoding="utf-8"))
    xsim_log = xsim_path.read_text(encoding="utf-8", errors="replace")
    solution_log = solution_path.read_text(encoding="utf-8", errors="replace")
    cosim_report = cosim_report_path.read_text(encoding="utf-8", errors="replace")
    c_tb_log = c_tb_path.read_text(encoding="utf-8", errors="replace")

    hand_commands, oracle_steps = _parse_c_tb(c_tb_log)
    completed, total, simulation_time = _parse_progress(xsim_log)
    elapsed_match = re.search(
        r"Finished Command cosim_design Elapsed time:\s*(\d\d:\d\d:\d\d)",
        solution_log,
    )
    oom_match = re.search(
        r"Out of memory on request for a fresh (\d+) bytes", xsim_log
    )
    consumed_match = re.search(
        r"Total memory consumed so far\s*:(\d+) bytes", xsim_log
    )
    if elapsed_match is None or oom_match is None or consumed_match is None:
        raise ValueError("co-simulation log is missing elapsed-time or OOM evidence")

    rtl_failed = (
        re.search(r"\|\s*Verilog\s*\|\s*Fail\s*\|", cosim_report) is not None
        and "*** C/RTL co-simulation finished: FAIL ***" in solution_log
    )
    first_valid_step_index = 4
    failed_on_first_valid_step = completed == first_valid_step_index - 1
    raw_hashes = {
        path.relative_to(ROOT).as_posix(): _sha256(path)
        for path in sorted(raw.glob("*"))
        if path.is_file()
    }
    current_sources = _source_hashes()
    if frozen_extraction_path.exists():
        frozen_extraction = json.loads(
            frozen_extraction_path.read_text(encoding="utf-8")
        )
        run_sources = frozen_extraction["source_sha256"]
    else:
        run_sources = current_sources
    source_paths = sorted(set(run_sources) | set(current_sources))
    source_mismatches = {
        path: {
            "smoke": run_sources.get(path),
            "current": current_sources.get(path),
        }
        for path in source_paths
        if run_sources.get(path) != current_sources.get(path)
    }

    if not rtl_failed:
        raise ValueError("co-simulation report does not contain a Verilog FAIL")
    status = "FAIL"
    manifest: dict[str, object] = {
        "schema": 1,
        "status": status,
        "scope": "one-token corrected uniform-MXFP4 RTL co-simulation smoke before transport-pipeline cleanup",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": "bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe",
        "trace": {
            "path": trace_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(trace_path),
            "tokens": trace_manifest["tokens"],
            "status": trace_manifest["status"],
        },
        "source_sha256": run_sources,
        "current_source_sha256": current_sources,
        "current_source_matches_smoke": not source_mismatches,
        "source_mismatches": source_mismatches,
        "raw_artifact_sha256": raw_hashes,
        "c_testbench": {
            "status": "PASS",
            "hand_commands": hand_commands,
            "oracle_steps": oracle_steps,
        },
        "rtl_simulation": {
            "status": "FAIL",
            "tool": "XSIM",
            "failure": "out of memory",
            "failed_on_first_valid_step": failed_on_first_valid_step,
            "completed_transactions": completed,
            "total_transactions": total,
            "last_simulation_time": simulation_time,
            "hls_elapsed_seconds": _parse_hms(elapsed_match.group(1)),
            "failed_allocation_bytes": int(oom_match.group(1)),
            "simulator_reported_memory_consumed_bytes": int(
                consumed_match.group(1)
            ),
        },
        "required_64_token_rtl_parity": "NOT_RUN",
        "required_64_token_transaction_count": 141,
        "feasibility_decision": {
            "status": "FAIL",
            "decision": (
                "Do not launch the required 64-token XSIM run on this host: "
                "the bounded one-token smoke exhausted memory before the first "
                "valid recurrent STEP completed."
            ),
        },
        "limitations": [
            "The C testbench PASS does not establish RTL parity.",
            "No complete recurrent STEP reached the RTL post-check.",
            "The selected residual-stack/write-log candidate is not implemented in this RTL.",
            "The simulator-reported memory counter is copied verbatim and is not host peak working set.",
            "The later transport-pipeline cleanup changed HLS source, so current RTL still requires a new parity run.",
        ],
    }

    json_path = smoke / "cosim_smoke_summary.json"
    md_path = smoke / "cosim_smoke_summary.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rtl = manifest["rtl_simulation"]
    md_path.write_text(
        "\n".join(
            [
                "# Corrected RTL Co-simulation Smoke",
                "",
                f"Generated: `{manifest['timestamp']}`",
                "",
                "- Smoke status: `FAIL`",
                "- C testbench: `PASS` (12 hand commands, 1 oracle step)",
                "- Verilog RTL simulation: `FAIL` (XSIM out of memory)",
                f"- Progress: `{rtl['completed_transactions']} / {rtl['total_transactions']}` transactions",
                f"- HLS-reported elapsed time: `{rtl['hls_elapsed_seconds']}` seconds",
                f"- Failed allocation request: `{rtl['failed_allocation_bytes']}` bytes",
                "- First valid recurrent STEP completed: `no`",
                "- Required 64-token RTL parity: `NOT_RUN`",
                f"- Current HLS source matches smoke source: `{'yes' if not source_mismatches else 'no'}`",
                "",
                "The bounded smoke failed during transaction 4, the first valid full",
                "STEP after three early control-path transactions. A 64-token testbench",
                "would issue 141 top-level transactions. It was not launched because the",
                "smoke exhausted simulator memory before completing one recurrent update.",
                "A later transport-pipeline cleanup changed synthesis directives and",
                "validation-loop pragmas; this frozen smoke is retained as a failed attempt",
                "and does not establish parity for current source.",
                "",
                "This result is not evidence of RTL correctness, selected-candidate",
                "physical feasibility, timing closure, or FPGA energy.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", type=Path, default=DEFAULT_SMOKE)
    args = parser.parse_args(argv)
    smoke = args.smoke if args.smoke.is_absolute() else ROOT / args.smoke
    manifest = generate_report(smoke)
    print(json.dumps({"status": manifest["status"], "scope": manifest["scope"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

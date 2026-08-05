"""Archive and validate the corrected candidate's 64-token HLS RTL trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.e2m0_control_cosim_report import parse_cosim_report
from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
SOLUTION = ROOT / "gdn_e2m0_trace_cosim_hls" / "u55c_250mhz"
TRACE = ROOT / "data" / "vectors" / "e2m0_resident_trace64.bin"
TRACE_MANIFEST = TRACE.with_name("e2m0_resident_trace64_manifest.json")
DEFAULT_OUTPUT = ROOT / "reports" / "cosim" / "corrected" / "e2m0_trace64"
PASS_MARKER = (
    "PASS: 64 encoded random-state tokens, exact outputs/counters, and final snapshot"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _git_revision() -> tuple[str, bool]:
    base = ["git", "-c", f"safe.directory={ROOT.as_posix()}"]
    revision = subprocess.check_output(
        [*base, "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            [*base, "status", "--porcelain"], cwd=ROOT, text=True
        ).strip()
    )
    return revision, dirty


def parse_progress(text: str) -> dict[str, int]:
    rows = [
        tuple(map(int, match))
        for match in re.findall(
            r"RTL Simulation\s*:\s*(\d+)\s*/\s*(\d+).*?@\s*\"(\d+)\"",
            text,
        )
    ]
    if not rows:
        raise ValueError("XSIM progress is absent")
    totals = {row[1] for row in rows}
    if totals != {66}:
        raise ValueError("XSIM trace does not contain 66 total transactions")
    return {
        "first_completed": rows[0][0],
        "completed_transactions": rows[-1][0],
        "total_transactions": rows[-1][1],
        "last_simulation_time": rows[-1][2],
        "progress_records": len(rows),
    }


def parse_oom(text: str) -> dict[str, int] | None:
    allocation = re.search(r"Out of memory on request for a fresh (\d+) bytes", text)
    consumed = re.search(r"Total memory consumed so far\s*:(\d+) bytes", text)
    if allocation is None and consumed is None:
        return None
    if allocation is None or consumed is None:
        raise ValueError("incomplete XSIM out-of-memory evidence")
    return {
        "failed_allocation_bytes": int(allocation.group(1)),
        "simulator_reported_memory_consumed_bytes": int(consumed.group(1)),
    }


def _source_paths() -> list[Path]:
    return [
        ROOT / "hls" / "e2m0" / "tb" / "tb_gdn_e2m0_trace.cpp",
        ROOT / "hls" / "e2m0" / "tcl" / "run_trace_cosim.tcl",
        *sorted((ROOT / "hls" / "e2m0" / "include").glob("*.hpp")),
        *sorted((ROOT / "hls" / "e2m0" / "src").glob("*.cpp")),
    ]


def generate_report(output: Path = DEFAULT_OUTPUT) -> dict[str, object]:
    paths = {
        "cosim_report": SOLUTION / "sim" / "report" / "gdn_e2m0_top_cosim.rpt",
        "xsim_log": SOLUTION / "sim" / "verilog" / "xsim.log",
        "solution_log": SOLUTION / "u55c_250mhz.log",
        "c_precheck": SOLUTION / "sim" / "wrapc" / "tmp.log",
    }
    for path in (*paths.values(), TRACE, TRACE_MANIFEST, *_source_paths()):
        if not path.is_file():
            raise FileNotFoundError(path)

    cosim_text = paths["cosim_report"].read_text(encoding="utf-8", errors="replace")
    xsim_text = paths["xsim_log"].read_text(encoding="utf-8", errors="replace")
    solution_text = paths["solution_log"].read_text(encoding="utf-8", errors="replace")
    precheck = paths["c_precheck"].read_text(encoding="utf-8", errors="replace").strip()
    if precheck != PASS_MARKER:
        raise ValueError("64-token C pre-check PASS marker is absent")
    progress = parse_progress(xsim_text)
    oom = parse_oom(xsim_text)
    verilog_pass = re.search(r"\|\s*Verilog\s*\|\s*Pass\s*\|", cosim_text) is not None
    verilog_fail = re.search(r"\|\s*Verilog\s*\|\s*Fail\s*\|", cosim_text) is not None
    solution_pass = "*** C/RTL co-simulation finished: PASS ***" in solution_text
    solution_fail = "*** C/RTL co-simulation finished: FAIL ***" in solution_text

    postcheck_path = SOLUTION / "sim" / "wrapc_pc" / "tmp.log"
    postcheck = (
        postcheck_path.read_text(encoding="utf-8", errors="replace").strip()
        if postcheck_path.is_file()
        else None
    )
    passed = (
        verilog_pass
        and not verilog_fail
        and solution_pass
        and not solution_fail
        and progress["completed_transactions"] == 66
        and postcheck == PASS_MARKER
        and oom is None
    )
    failed = verilog_fail and solution_fail and oom is not None
    if not passed and not failed:
        raise ValueError("co-simulation artifacts are neither a complete PASS nor a recorded OOM failure")

    output.mkdir(parents=True, exist_ok=True)
    raw = output / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = dict(paths)
    if postcheck_path.is_file():
        archive["c_postcheck"] = postcheck_path
    for name, source in archive.items():
        shutil.copy2(source, raw / f"{name}{source.suffix}")
    shutil.copy2(TRACE_MANIFEST, raw / TRACE_MANIFEST.name)

    trace_manifest = json.loads(TRACE_MANIFEST.read_text(encoding="utf-8"))
    if trace_manifest.get("status") != "PASS" or trace_manifest.get("configuration", {}).get("tokens") != 64:
        raise ValueError("encoded trace manifest is not the frozen 64-token PASS artifact")
    if _sha256(TRACE) != str(trace_manifest["trace_sha256"]).upper():
        raise ValueError("encoded trace hash does not match its manifest")
    revision, dirty = _git_revision()
    source_identity = describe_source_files(_source_paths())

    report: dict[str, object] = {
        "schema": 1,
        "status": "PASS" if passed else "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "official Vitis HLS/XSIM 64-token generated-RTL parity for the corrected E2M0 residual/write-log candidate",
        "source_revision": revision,
        "working_tree_dirty": dirty,
        "source_identity": source_identity,
        "tool": {
            "hls": "AMD Vitis HLS 2025.2",
            "rtl_simulator": "AMD XSIM 2025.2",
            "target_part": "xcu55c-fsvh2892-2L-e",
            "target_period_ns": 4.0,
        },
        "trace": {
            "path": TRACE.relative_to(ROOT).as_posix(),
            "sha256": _sha256(TRACE),
            "tokens": 64,
            "manifest_sha256": _sha256(TRACE_MANIFEST),
        },
        "c_precheck": {"status": "PASS", "marker": precheck},
        "rtl_simulation": {
            "status": "PASS" if passed else "FAIL",
            **progress,
            **({"failure": "host out of memory", **oom} if oom else {}),
        },
        "required_64_token_rtl_parity": "PASS" if passed else "NOT_ESTABLISHED",
        "raw_artifact_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path)
            for path in sorted(raw.glob("*"))
        },
        "limitations": [
            "This is generated-RTL co-simulation, not post-route or board execution.",
            "The trace is deterministic, synthetic, and limited to 64 sequential recurrent updates.",
        ],
    }
    if passed:
        report["official_hls_cosim"] = parse_cosim_report(cosim_text)
        report["c_postcheck"] = {"status": "PASS", "marker": postcheck}
        report["parity"] = {
            "ordered_tokens": 64,
            "output_values_compared": 64 * 32 * 128,
            "command_counters_compared": 64 * 8,
            "cumulative_counters_compared": 64 * 8,
            "final_primary_state_elements_compared": 32 * 128 * 128,
            "final_residual_state_elements_compared": 32 * 128 * 128,
            "final_snapshot_includes_write_log_and_coefficients": True,
        }
    else:
        report["interpretation"] = (
            "The C oracle completed exactly, but XSIM exhausted host memory before "
            "the first of 66 RTL transactions. This attempt is not parity evidence."
        )

    json_path = output / "e2m0_trace64_cosim_summary.json"
    md_path = output / "e2m0_trace64_cosim_summary.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# Corrected Candidate 64-Token RTL Co-simulation",
                "",
                f"- Status: `{report['status']}`",
                "- C pre-check: `PASS`",
                f"- RTL progress: `{progress['completed_transactions']} / 66`",
                f"- Required 64-token RTL parity: `{report['required_64_token_rtl_parity']}`",
                *(
                    ["- Exact outputs, counters, and final snapshot: `PASS`"]
                    if passed
                    else ["- Failure: host out of memory before transaction 1"]
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report = generate_report(output)
    print(json.dumps({"status": report["status"], "rtl": report["required_64_token_rtl_parity"]}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

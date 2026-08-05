"""Archive and validate the corrected E2M0 generated-RTL control smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOLUTION = ROOT / "gdn_e2m0_hls" / "u55c_250mhz"
DEFAULT_OUTPUT = ROOT / "reports" / "cosim" / "corrected" / "e2m0_control_smoke"
PASS_MARKER = (
    "PASS: corrected E2M0 generated-RTL control smoke, two exact commands"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _git_revision() -> tuple[str, bool]:
    revision = subprocess.check_output(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "rev-parse",
            "HEAD",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    dirty = bool(
        subprocess.check_output(
            [
                "git",
                "-c",
                f"safe.directory={ROOT.as_posix()}",
                "status",
                "--porcelain",
            ],
            cwd=ROOT,
            text=True,
        ).strip()
    )
    return revision, dirty


def parse_cosim_report(text: str) -> dict[str, int | str]:
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == "Verilog":
            if len(cells) != 9:
                raise ValueError("unexpected Verilog co-simulation row shape")
            if cells[1] != "Pass":
                raise ValueError("official Verilog co-simulation status is not Pass")
            values = [int(cell) for cell in cells[2:]]
            return {
                "status": "PASS",
                "latency_min_cycles": values[0],
                "latency_avg_cycles": values[1],
                "latency_max_cycles": values[2],
                "interval_min_cycles": values[3],
                "interval_avg_cycles": values[4],
                "interval_max_cycles": values[5],
                "total_execution_cycles": values[6],
            }
    raise ValueError("official report has no Verilog result row")


def parse_xsim_log(text: str) -> dict[str, int | str]:
    matches = re.findall(
        r"RTL Simulation\s*:\s*(\d+)\s*/\s*(\d+).*?@\s*\"(\d+)\"",
        text,
    )
    if [(int(done), int(total)) for done, total, _time in matches] != [
        (0, 2),
        (1, 2),
        (2, 2),
    ]:
        raise ValueError("XSIM did not complete the expected two transactions")
    finish = re.search(r"\$finish called at time\s*:\s*(\d+)\s+ns", text)
    kernel = re.search(
        r"xsimkernel Simulation Memory Usage: (\d+) KB \(Peak: (\d+) KB\), "
        r"Simulation CPU Usage: (\d+) ms",
        text,
    )
    if finish is None or kernel is None:
        raise ValueError("XSIM finish or kernel statistics are absent")
    if re.search(r"^UVM_(?:ERROR|FATAL)\b", text, re.MULTILINE):
        raise ValueError("XSIM emitted a UVM error or fatal message")
    return {
        "status": "PASS",
        "completed_transactions": 2,
        "total_transactions": 2,
        "final_progress_time": int(matches[-1][2]),
        "finish_time_ns": int(finish.group(1)),
        "current_memory_kb": int(kernel.group(1)),
        "peak_memory_kb": int(kernel.group(2)),
        "cpu_ms": int(kernel.group(3)),
    }


def _latest_cosim_block(text: str) -> str:
    start = text.rfind("Running: cosim_design")
    if start < 0:
        raise ValueError("solution log has no co-simulation invocation")
    block = text[start:]
    if "*** C/RTL co-simulation finished: PASS ***" not in block:
        raise ValueError("latest solution-log co-simulation did not pass")
    if "*** C/RTL co-simulation finished: FAIL ***" in block:
        raise ValueError("latest solution-log block also contains a failure")
    return block


def _tree_digest(paths: list[Path], base: Path) -> str:
    records = [
        f"{path.relative_to(base).as_posix()}:{_sha256(path)}" for path in paths
    ]
    return hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest().upper()


def _hash_paths(paths: list[Path]) -> dict[str, dict[str, int | str]]:
    return {
        _relative(path): {"sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in paths
    }


def generate_report(output: Path = DEFAULT_OUTPUT) -> dict[str, object]:
    cosim_report = SOLUTION / "sim" / "report" / "gdn_e2m0_top_cosim.rpt"
    xsim_log = SOLUTION / "sim" / "verilog" / "xsim.log"
    solution_log = SOLUTION / "u55c_250mhz.log"
    precheck_log = SOLUTION / "sim" / "wrapc" / "tmp.log"
    postcheck_log = SOLUTION / "sim" / "wrapc_pc" / "tmp.log"
    generated_rtl_dir = SOLUTION / "sim" / "verilog"
    generated_rtl = sorted(generated_rtl_dir.glob("*.v"))
    source_paths = [
        ROOT / "hls" / "e2m0" / "tb" / "tb_gdn_e2m0_rtl_control.cpp",
        ROOT / "hls" / "e2m0" / "tcl" / "run_control_cosim.tcl",
        *sorted((ROOT / "hls" / "e2m0" / "include").glob("*.hpp")),
        *sorted((ROOT / "hls" / "e2m0" / "src").glob("*.cpp")),
    ]
    required = (
        cosim_report,
        xsim_log,
        solution_log,
        precheck_log,
        postcheck_log,
        *source_paths,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if not generated_rtl:
        raise FileNotFoundError(generated_rtl_dir / "*.v")

    cosim = parse_cosim_report(
        cosim_report.read_text(encoding="utf-8", errors="replace")
    )
    xsim = parse_xsim_log(xsim_log.read_text(encoding="utf-8", errors="replace"))
    latest_solution = _latest_cosim_block(
        solution_log.read_text(encoding="utf-8", errors="replace")
    )
    precheck = precheck_log.read_text(encoding="utf-8", errors="replace").strip()
    postcheck = postcheck_log.read_text(encoding="utf-8", errors="replace").strip()
    if precheck != PASS_MARKER or postcheck != PASS_MARKER:
        raise ValueError("C pre-check or post-check PASS marker is absent")
    if "*** C/RTL co-simulation finished: PASS ***" not in latest_solution:
        raise ValueError("latest solution log lacks the vendor PASS marker")

    output.mkdir(parents=True, exist_ok=True)
    raw = output / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive_map = {
        cosim_report: raw / "gdn_e2m0_top_cosim.rpt",
        xsim_log: raw / "xsim.log",
        solution_log: raw / "u55c_250mhz.log",
        precheck_log: raw / "c_precheck.log",
        postcheck_log: raw / "c_postcheck.log",
    }
    for source, destination in archive_map.items():
        shutil.copy2(source, destination)

    revision, dirty = _git_revision()
    report: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Official Vitis HLS 2025.2 C/RTL co-simulation of two exact "
            "early-return control commands for the corrected E2M0 candidate."
        ),
        "source_revision": revision,
        "working_tree_dirty": dirty,
        "tool": {
            "hls": "AMD Vitis HLS 2025.2",
            "rtl_simulator": "AMD XSIM 2025.2",
            "target_part": "xcu55c-fsvh2892-2L-e",
            "target_period_ns": 4.0,
        },
        "official_hls_cosim": cosim,
        "rtl_simulation": xsim,
        "c_precheck": {"status": "PASS", "marker": precheck},
        "c_postcheck": {"status": "PASS", "marker": postcheck},
        "commands": [
            {
                "command": "RESET",
                "condition": "invalid layer identifier",
                "expected_status": "STATUS_INVALID_LAYER_ID",
            },
            {
                "command": "STEP",
                "condition": "uninitialized resident state",
                "expected_status": "STATUS_UNINITIALIZED_STATE",
            },
        ],
        "recurrent_transition_covered": False,
        "required_64_token_rtl_parity": "NOT_RUN",
        "required_64_token_c_sim_parity": "PASS_SEPARATE_EVIDENCE",
        "runtime_staging": {
            "classification": "host tool-runtime dependency",
            "design_behavior_changed": False,
            "dlls": ["libstdc++-6.dll", "libwinpthread-1.dll"],
            "note": (
                "The Vitis-generated Windows harnesses require MinGW runtime DLLs. "
                "Copies were staged beside the generated pre-check and post-check "
                "executables so the vendor launcher could resolve them."
            ),
        },
        "source_files": _hash_paths(source_paths),
        "generated_rtl": {
            "file_count": len(generated_rtl),
            "tree_sha256": _tree_digest(generated_rtl, generated_rtl_dir),
            "top": _hash_paths([generated_rtl_dir / "gdn_e2m0_top.v"]),
        },
        "archived_logs": _hash_paths(list(archive_map.values())),
        "claim_boundary": {
            "generated_rtl_control_path_parity": "SUPPORTED",
            "generated_rtl_recurrent_step_parity": "NOT_RUN",
            "generated_rtl_64_token_parity": "NOT_RUN",
            "hls_c_sim_64_token_parity": "SUPPORTED_BY_SEPARATE_REPORT",
            "board_execution": "NOT_RUN",
        },
        "interpretation": (
            "The official vendor flow establishes generated-RTL parity for two "
            "early-return control paths. It does not execute a recurrent state "
            "transition and is not the required 64-token RTL parity test."
        ),
    }
    json_path = output / "e2m0_control_smoke_summary.json"
    md_path = output / "e2m0_control_smoke_summary.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_path.write_text(
        "\n".join(
            [
                "# Corrected E2M0 Generated-RTL Control Smoke",
                "",
                "- Official Vitis HLS C/RTL co-simulation: `PASS`",
                "- Simulator: `XSIM 2025.2`",
                "- Completed transactions: `2 / 2`",
                f"- Per-command latency: `{cosim['latency_avg_cycles']}` cycles",
                f"- Reported interval: `{cosim['interval_avg_cycles']}` cycles",
                f"- Total execution: `{cosim['total_execution_cycles']}` cycles",
                "- Recurrent state transition covered: `no`",
                "- Required 64-token candidate RTL parity: `NOT_RUN`",
                "- Separate 64-token candidate C-sim parity: `PASS`",
                "",
                str(report["interpretation"]),
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
    print(
        json.dumps(
            {
                "status": report["status"],
                "transactions": report["rtl_simulation"]["completed_transactions"],
                "recurrent_transition_covered": report[
                    "recurrent_transition_covered"
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

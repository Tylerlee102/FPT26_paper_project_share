"""Summarize completed and blocked corrected-candidate generated-RTL checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
DIRECT = ROOT / "reports" / "cosim" / "corrected" / "e2m0_direct_rtl_trace64"
XSIM_ISOLATED = (
    ROOT
    / "reports"
    / "cosim"
    / "corrected"
    / "e2m0_trace64_attempt_oom_isolated"
    / "e2m0_trace64_cosim_summary.json"
)
XSIM_PARENTLESS = (
    ROOT
    / "reports"
    / "cosim"
    / "corrected"
    / "e2m0_trace64_attempt_oom_parentless"
    / "e2m0_trace64_cosim_summary.json"
)
HLS = ROOT / "reports" / "csynth" / "corrected" / "e2m0_hls_summary.json"
OUTPUT = ROOT / "reports" / "cosim" / "corrected" / "e2m0_trace64"
LOAD_PATTERN = re.compile(
    r"E2M0_DIRECT_RTL command=1 cycles=(\d+) status=0 generation=1"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


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


def _time_value(text: str, label: str, pattern: str) -> float:
    match = re.search(pattern, text)
    if match is None:
        raise ValueError(f"{label} is absent from Verilator timing record")
    return float(match.group(1))


def generate_report(output: Path = OUTPUT) -> dict[str, object]:
    direct_paths = {
        "benchmark": DIRECT / "benchmark_t1_0token.json",
        "execution": DIRECT / "raw" / "execution.json",
        "run_log": DIRECT / "raw" / "verilator_run.log",
        "run_time": DIRECT / "raw" / "verilator_run_time.log",
        "compile_log": DIRECT / "raw" / "verilator_compile.log",
        "compile_time": DIRECT / "raw" / "verilator_compile_time.log",
        "assets": DIRECT / "assets" / "manifest.json",
    }
    for path in (*direct_paths.values(), XSIM_ISOLATED, XSIM_PARENTLESS, HLS):
        if not path.is_file():
            raise FileNotFoundError(path)
    benchmark = json.loads(direct_paths["benchmark"].read_text(encoding="utf-8"))
    execution = json.loads(direct_paths["execution"].read_text(encoding="utf-8"))
    assets = json.loads(direct_paths["assets"].read_text(encoding="utf-8"))
    isolated = json.loads(XSIM_ISOLATED.read_text(encoding="utf-8"))
    parentless = json.loads(XSIM_PARENTLESS.read_text(encoding="utf-8"))
    hls = json.loads(HLS.read_text(encoding="utf-8"))
    if (
        benchmark.get("status") != "PASS"
        or benchmark.get("tokens") != 0
        or execution.get("simulation_exit_code") != 0
        or execution.get("token_limit") != 0
        or assets.get("status") != "PASS"
    ):
        raise ValueError("bounded direct generated-RTL LOAD evidence is not PASS")
    for attempt in (isolated, parentless):
        if (
            attempt.get("status") != "FAIL"
            or attempt.get("c_precheck", {}).get("status") != "PASS"
            or attempt.get("required_64_token_rtl_parity") != "NOT_ESTABLISHED"
            or attempt.get("rtl_simulation", {}).get("completed_transactions") != 0
        ):
            raise ValueError("official XSIM attempt no longer matches its OOM boundary")
    if hls.get("csim", {}).get("required_64_token_csim") != "PASS":
        raise ValueError("corrected candidate 64-token HLS C-sim is not PASS")

    run_text = direct_paths["run_log"].read_text(encoding="utf-8", errors="replace")
    load_match = LOAD_PATTERN.search(run_text)
    if load_match is None or "E2M0_DIRECT_RTL_BENCHMARK PASS tokens=0" not in run_text:
        raise ValueError("exact generated-RTL LOAD markers are absent")
    load_cycles = int(load_match.group(1))
    time_text = direct_paths["run_time"].read_text(encoding="utf-8", errors="replace")
    elapsed_match = re.search(
        r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\d+):(\d+(?:\.\d+)?)",
        time_text,
    )
    if elapsed_match is None:
        raise ValueError("elapsed wall time is absent from Verilator timing record")
    elapsed_seconds = 60.0 * int(elapsed_match.group(1)) + float(elapsed_match.group(2))
    maximum_resident_kb = int(
        _time_value(
            time_text,
            "maximum resident set",
            r"Maximum resident set size \(kbytes\):\s*(\d+)",
        )
    )
    simulated_cycles_per_second = load_cycles / elapsed_seconds
    steady = hls["csynth"]["steady_state_amortized_cycles_per_token"]
    projected_min_hours = 64.0 * float(steady["minimum"]) / simulated_cycles_per_second / 3600.0
    projected_max_hours = 64.0 * float(steady["maximum"]) / simulated_cycles_per_second / 3600.0

    source_paths = [
        ROOT / "hls" / "rtl_tb" / "axi_memory_model.sv",
        ROOT / "hls" / "rtl_tb" / "tb_gdn_e2m0_top_direct.sv",
        ROOT / "scripts" / "generate_e2m0_direct_rtl_trace_assets.py",
        ROOT / "scripts" / "e2m0_direct_rtl_flow.py",
        ROOT / "scripts" / "e2m0_rtl_completion_report.py",
    ]
    revision, dirty = _git_revision()
    source_identity = describe_source_files(source_paths)
    if source_identity["git_revision"] != revision:
        raise ValueError("source revision changed while generating RTL completion report")
    inputs = [*direct_paths.values(), XSIM_ISOLATED, XSIM_PARENTLESS, HLS]
    report: dict[str, object] = {
        "schema": 1,
        "status": "PARTIAL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "corrected E2M0 candidate 64-token generated-RTL completion audit",
        "source_revision": revision,
        "working_tree_dirty": dirty,
        "source_identity": source_identity,
        "trace": {
            "tokens": 64,
            "sha256": assets["source_trace"]["sha256"],
            "path": assets["source_trace"]["path"],
        },
        "hls_c_simulation": {
            "status": "PASS",
            "tokens": 64,
            "outputs_counters_and_final_snapshot": "PASS",
        },
        "official_hls_xsim": {
            "status": "FAIL",
            "completed_transactions": 0,
            "requested_transactions": 66,
            "failure": "host out of memory before transaction one",
            "independent_attempts": 2,
        },
        "direct_generated_rtl_load": {
            "status": "PASS",
            "simulator": execution["verilator_version"],
            "command": "LOAD",
            "completed_transactions": 1,
            "cycles": load_cycles,
            "status_code": 0,
            "generation": 1,
            "elapsed_seconds": elapsed_seconds,
            "maximum_resident_kb": maximum_resident_kb,
        },
        "rtl_simulation": {
            "status": "PARTIAL",
            "completed_transactions": 1,
            "completed_recurrent_steps": 0,
            "requested_transactions": 66,
        },
        "parity": {
            "status": "NOT_ESTABLISHED",
            "ordered_tokens": 0,
            "output_values_compared": 0,
            "final_snapshot_compared": False,
        },
        "host_runtime_projection": {
            "status": "DIAGNOSTIC_ONLY",
            "measured_load_cycles_per_second": simulated_cycles_per_second,
            "projected_64_token_hours_minimum": projected_min_hours,
            "projected_64_token_hours_maximum": projected_max_hours,
            "qualification": "Projection combines LOAD throughput with HLS steady-state cycle bounds and is not FPGA performance evidence.",
        },
        "required_64_token_rtl_parity": "NOT_ESTABLISHED",
        "input_sha256": {
            _relative(path): _sha256(path)
            for path in inputs
        },
        "limitations": [
            "The corrected candidate has exact 64-token HLS C parity but not 64-token generated-RTL parity.",
            "Both official XSIM attempts exhausted host memory before transaction one.",
            "Verilator 5.050 completes exact candidate LOAD, but the scheduled recurrent STEP is too slow for a practical full trace in this study.",
            "Uniform-MXFP4, not the corrected candidate, retains the complete 64-token sequential generated-RTL parity result.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "e2m0_trace64_cosim_summary.json"
    md_path = output / "e2m0_trace64_cosim_summary.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_path.write_text(
        "\n".join(
            [
                "# Corrected Candidate 64-Token RTL Completion",
                "",
                "- HLS C simulation, 64 tokens: `PASS`",
                "- Vitis/XSIM RTL transactions: `0 / 66` (host OOM in two isolated attempts)",
                f"- Verilator direct RTL LOAD: `PASS` in `{load_cycles}` cycles",
                "- Corrected recurrent STEP transactions completed in RTL: `0`",
                "- Required corrected-candidate 64-token RTL parity: `NOT_ESTABLISHED`",
                f"- Diagnostic projected host runtime: `{projected_min_hours:.1f}` to `{projected_max_hours:.1f}` hours",
                "",
                "The host-runtime projection is a simulator feasibility diagnostic, not FPGA latency or energy evidence.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report = generate_report(output)
    print(
        json.dumps(
            {
                "status": report["status"],
                "hls_csim": report["hls_c_simulation"]["status"],
                "rtl_64_token": report["required_64_token_rtl_parity"],
                "direct_load": report["direct_generated_rtl_load"]["status"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

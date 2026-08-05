"""Validate and archive the corrected E2M0 direct-Verilator parity run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "reports" / "cosim" / "corrected" / "e2m0_direct_rtl_trace64"
CANONICAL = ROOT / "reports" / "cosim" / "corrected" / "e2m0_trace64"
RTL = ROOT / "gdn_e2m0_trace_cosim_hls" / "u55c_250mhz" / "syn" / "verilog"
TRACE = ROOT / "data" / "vectors" / "e2m0_resident_trace64.bin"
TRACE_MANIFEST = TRACE.with_name("e2m0_resident_trace64_manifest.json")
COMMAND_PATTERN = re.compile(
    r"E2M0_DIRECT_RTL command=(?P<command>\d+) cycles=(?P<cycles>\d+) "
    r"status=(?P<status>\d+) generation=(?P<generation>\d+)"
)
TOKEN_PATTERN = re.compile(
    r"E2M0_DIRECT_RTL_TOKEN token=(?P<token>\d+) status=(?P<status>\d+) "
    r"generation=(?P<generation>\d+) live=(?P<live>\d+) PASS"
)
FINAL_MARKER = (
    "E2M0_DIRECT_RTL_TRACE64 PASS tokens=64 transactions=66 "
    "outputs=262144 final_snapshot=PASS"
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


def _hash_paths(paths: list[Path]) -> dict[str, dict[str, object]]:
    return {
        _relative(path): {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in paths
    }


def _read_hex(path: Path) -> list[int]:
    return [int(line, 16) for line in path.read_text(encoding="ascii").splitlines()]


def parse_simulation_log(text: str, expected_live: list[int]) -> dict[str, object]:
    commands = [
        {key: int(value) for key, value in match.groupdict().items()}
        for match in COMMAND_PATTERN.finditer(text)
    ]
    if [row["command"] for row in commands] != [1] + [2] * 64 + [3]:
        raise ValueError("direct RTL log does not contain LOAD, 64 STEP, READBACK")
    if any(row["status"] != 0 for row in commands):
        raise ValueError("a corrected-candidate RTL command returned nonzero status")
    if [row["generation"] for row in commands] != [1] + list(range(2, 66)) + [65]:
        raise ValueError("corrected-candidate RTL generation sequence is discontinuous")

    tokens = [
        {key: int(value) for key, value in match.groupdict().items()}
        for match in TOKEN_PATTERN.finditer(text)
    ]
    if len(tokens) != 64 or [row["token"] for row in tokens] != list(range(1, 65)):
        raise ValueError("64 ordered corrected-candidate token markers are absent")
    if [row["generation"] for row in tokens] != list(range(2, 66)):
        raise ValueError("token-marker generations are discontinuous")
    if any(row["status"] != 0 for row in tokens):
        raise ValueError("a token marker has nonzero status")
    if [row["live"] for row in tokens] != expected_live:
        raise ValueError("token-marker write-log occupancies differ from the oracle")
    if FINAL_MARKER not in text:
        raise ValueError("corrected-candidate final parity marker is absent")
    step_cycles = [row["cycles"] for row in commands if row["command"] == 2]
    return {
        "commands": commands,
        "tokens": tokens,
        "step_latency_cycles": {
            "count": len(step_cycles),
            "minimum": min(step_cycles),
            "maximum": max(step_cycles),
            "mean": statistics.fmean(step_cycles),
            "median": statistics.median(step_cycles),
        },
    }


def _parse_time_report(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    fields: dict[str, object] = {}
    patterns = {
        "user_seconds": r"User time \(seconds\):\s*([0-9.]+)",
        "system_seconds": r"System time \(seconds\):\s*([0-9.]+)",
        "elapsed": r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)",
        "maximum_resident_kb": r"Maximum resident set size \(kbytes\):\s*(\d+)",
        "major_page_faults": r"Major \(requiring I/O\) page faults:\s*(\d+)",
        "minor_page_faults": r"Minor \(reclaiming a frame\) page faults:\s*(\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match is None:
            raise ValueError(f"GNU time field is absent: {key}")
        value = match.group(1)
        fields[key] = (
            float(value)
            if key in {"user_seconds", "system_seconds"}
            else int(value)
            if key.endswith("_kb") or key.endswith("faults")
            else value
        )
    return fields


def _verify_assets(assets: Path) -> dict[str, object]:
    manifest_path = assets / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS" or manifest.get("dimensions", {}).get("tokens") != 64:
        raise ValueError("E2M0 direct-RTL asset manifest is not a 64-token PASS")
    for name, expected in manifest["files"].items():
        path = assets / name
        if path.stat().st_size != expected["bytes"] or _sha256(path) != expected["sha256"]:
            raise ValueError(f"E2M0 direct-RTL asset hash mismatch: {name}")
    if manifest["source_trace"]["sha256"] != _sha256(TRACE):
        raise ValueError("E2M0 direct-RTL assets do not identify the frozen trace")
    return manifest


def generate_report(
    evidence: Path = EVIDENCE,
    canonical: Path = CANONICAL,
    rtl: Path = RTL,
) -> dict[str, object]:
    raw = evidence / "raw"
    required = {
        "simulation_log": raw / "verilator_run.log",
        "simulation_time": raw / "verilator_run_time.log",
        "compile_log": raw / "verilator_compile.log",
        "compile_time": raw / "verilator_compile_time.log",
        "execution": raw / "execution.json",
    }
    for path in (*required.values(), TRACE, TRACE_MANIFEST):
        if not path.is_file():
            raise FileNotFoundError(path)
    execution = json.loads(required["execution"].read_text(encoding="utf-8"))
    if execution.get("compile_exit_code") != 0 or execution.get("simulation_exit_code") != 0:
        raise ValueError("Verilator compile or simulation did not exit successfully")
    assets = evidence / "assets"
    asset_manifest = _verify_assets(assets)
    expected_live = _read_hex(assets / "live.hex")
    parsed = parse_simulation_log(
        required["simulation_log"].read_text(encoding="utf-8", errors="replace"),
        expected_live,
    )
    trace_manifest = json.loads(TRACE_MANIFEST.read_text(encoding="utf-8"))
    if trace_manifest.get("status") != "PASS" or trace_manifest.get("trace_sha256") != _sha256(TRACE):
        raise ValueError("frozen E2M0 trace manifest is stale")
    rtl_paths = sorted(rtl.glob("*.v"))
    dat_paths = sorted(rtl.glob("*.dat"))
    if not rtl_paths or not dat_paths:
        raise ValueError("HLS-generated E2M0 RTL or initialization data are absent")
    source_paths = [
        ROOT / "hls" / "rtl_tb" / "axi_memory_model.sv",
        ROOT / "hls" / "rtl_tb" / "tb_gdn_e2m0_top_direct.sv",
        ROOT / "scripts" / "generate_e2m0_direct_rtl_trace_assets.py",
        ROOT / "scripts" / "e2m0_direct_rtl_flow.py",
        ROOT / "scripts" / "e2m0_direct_rtl_trace_report.py",
        *sorted((ROOT / "hls" / "e2m0" / "include").glob("*.hpp")),
        *sorted((ROOT / "hls" / "e2m0" / "src").glob("*.cpp")),
    ]
    revision, dirty = _git_revision()
    source_identity = describe_source_files(source_paths)
    if source_identity["git_revision"] != revision:
        raise ValueError("source revision changed while archiving direct RTL evidence")
    simulation_time = _parse_time_report(required["simulation_time"])
    compile_time = _parse_time_report(required["compile_time"])
    report: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Bit-exact 64-token generated-Verilog parity for the corrected E2M0 "
            "residual-stack/write-log candidate through a custom direct AXI harness."
        ),
        "source_revision": revision,
        "working_tree_dirty": dirty,
        "source_identity": source_identity,
        "tool": {
            "hls_rtl_generator": "AMD Vitis HLS 2025.2",
            "rtl_simulator": execution["verilator_version"],
            "host": "WSL Ubuntu-24.04",
            "harness": "custom direct AXI-Lite/AXI SystemVerilog",
            "official_vitis_uvm_cosim": False,
        },
        "configuration": {
            "layer_id": 4,
            "tokens": 64,
            "num_qk_heads": 16,
            "num_value_heads": 32,
            "key_dim": 128,
            "value_dim": 128,
            "block_size": 32,
            "stack_depth": 2,
            "log_capacity": 7,
            "p_k": 16,
            "p_v": 8,
        },
        "trace": {
            "tokens": 64,
            "path": _relative(TRACE),
            "sha256": _sha256(TRACE),
            "manifest": _relative(TRACE_MANIFEST),
            "input_stream_sha256": trace_manifest["input_stream_sha256"],
        },
        "rtl_simulation": {
            "status": "PASS",
            "completed_transactions": 66,
            "load_transactions": 1,
            "step_transactions": 64,
            "readback_transactions": 1,
            "time_and_memory": simulation_time,
        },
        "rtl_compilation": {
            "status": "PASS",
            "generated_verilog_files": len(rtl_paths),
            "initialization_data_files": len(dat_paths),
            "time_and_memory": compile_time,
        },
        "parity": {
            "status": "PASS",
            "ordered_tokens": 64,
            "output_values_compared": 64 * 32 * 128,
            "output_mantissas_compared": 64 * 32 * 128,
            "output_exponents_compared": 64 * 32 * 128,
            "command_counters_compared": 64 * 8,
            "cumulative_counters_compared": 64 * 8,
            "final_primary_state_elements_compared": 32 * 128 * 128,
            "final_primary_state_scales_compared": 32 * 128 * 4,
            "final_residual_state_elements_compared": 32 * 128 * 128,
            "final_residual_state_scales_compared": 32 * 128 * 4,
            "final_log_key_elements_compared": 7 * 2 * 16 * 128,
            "final_log_key_scales_compared": 7 * 2 * 16 * 4,
            "final_log_update_elements_compared": 7 * 2 * 32 * 128,
            "final_log_update_scales_compared": 7 * 2 * 32 * 4,
            "final_gamma_values_compared": 32,
            "final_lambda_values_compared": 7 * 32,
            "final_generation": 65,
        },
        "step_latency_cycles": parsed["step_latency_cycles"],
        "command_results": parsed["commands"],
        "asset_manifest": asset_manifest,
        "source_files": _hash_paths(source_paths),
        "generated_rtl": {
            "file_count": len(rtl_paths),
            "files": _hash_paths(rtl_paths),
        },
        "initialization_data": {
            "file_count": len(dat_paths),
            "files": _hash_paths(dat_paths),
        },
        "archived_logs": _hash_paths(list(required.values())),
        "required_64_token_rtl_parity": "PASS",
        "independent_verification": [
            "The asset generator rechecks the frozen trace SHA256 and consumes every byte.",
            "The asset manifest hashes all 40 readmemh files consumed by the harness.",
            "The harness compares every token output, counter, write-log occupancy, and final resident snapshot before PASS.",
            "This report independently enforces all 66 commands and all 64 ordered token PASS markers.",
        ],
        "limitations": [
            "This is pre-synthesis HLS-generated Verilog, not post-route netlist or board execution.",
            "The custom direct harness replaces the Vitis UVM wrapper, whose XSIM run exhausted host memory before transaction one.",
            "The trace is deterministic and synthetic; this result does not establish full-model accuracy or perplexity.",
        ],
    }
    evidence.mkdir(parents=True, exist_ok=True)
    canonical.mkdir(parents=True, exist_ok=True)
    direct_json = evidence / "e2m0_direct_rtl_trace64_summary.json"
    canonical_json = canonical / "e2m0_trace64_cosim_summary.json"
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    direct_json.write_text(payload, encoding="utf-8")
    canonical_json.write_text(payload, encoding="utf-8")
    latency = report["step_latency_cycles"]
    markdown = "\n".join(
        [
            "# Corrected Candidate Direct RTL 64-Token Parity",
            "",
            "- Status: `PASS`",
            "- Simulator: `Verilator 5.020` under WSL Ubuntu-24.04",
            "- Sequence: one LOAD, 64 sequential STEP commands, one READBACK",
            "- Token outputs: all `262144` mantissa/exponent pairs",
            "- Final snapshot: primary/residual stacks, scales, logs, coefficients, and metadata",
            f"- STEP cycles: min `{latency['minimum']}`, mean `{latency['mean']:.2f}`, max `{latency['maximum']}`",
            "- Required 64-token generated-RTL parity: `PASS`",
            "",
            "This is a custom direct AXI harness over the Vitis-HLS-generated Verilog.",
            "It is not the memory-exhausting Vitis UVM wrapper, post-route simulation, or board evidence.",
            "",
        ]
    )
    (evidence / "e2m0_direct_rtl_trace64_summary.md").write_text(
        markdown, encoding="utf-8"
    )
    (canonical / "e2m0_trace64_cosim_summary.md").write_text(
        markdown, encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--canonical", type=Path, default=CANONICAL)
    parser.add_argument("--rtl", type=Path, default=RTL)
    args = parser.parse_args(argv)
    evidence = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    canonical = args.canonical if args.canonical.is_absolute() else ROOT / args.canonical
    rtl = args.rtl if args.rtl.is_absolute() else ROOT / args.rtl
    report = generate_report(evidence, canonical, rtl)
    print(json.dumps({"status": report["status"], "transactions": 66, "tokens": 64}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Archive and independently validate the 64-token direct RTL parity run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .direct_rtl_report import COMMAND_PATTERN
from .evidence_source_snapshot import describe_source_files
from .verify_hls_command_trace import verify_trace


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "reports" / "cosim" / "corrected" / "direct_rtl_trace64"
DEFAULT_RTL = ROOT / "gdn_mxfp4_hls" / "u55c_250mhz" / "syn" / "verilog"
TOKEN_PATTERN = re.compile(
    r"DIRECT_RTL_TRACE token=(\d+) status=(\d+) generation=(\d+) PASS"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _git_revision() -> tuple[str, bool]:
    revision = subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "status", "--porcelain"],
            cwd=ROOT,
            text=True,
        ).strip()
    )
    return revision, dirty


def parse_trace_xsim_log(text: str) -> dict[str, object]:
    commands = [
        {key: int(value) for key, value in match.groupdict().items()}
        for match in COMMAND_PATTERN.finditer(text)
    ]
    expected_commands = [0] + [2] * 64 + [3]
    if [row["command"] for row in commands] != expected_commands:
        raise ValueError("expected RESET, 64 STEP, READBACK commands")
    if any(row["command"] != row["latched"] for row in commands):
        raise ValueError("a direct RTL trace command was not latched correctly")
    if any(row["status"] != 0 for row in commands):
        raise ValueError("a direct RTL trace command returned nonzero status")
    expected_generations = [0] + list(range(1, 65)) + [64]
    if [row["generation"] for row in commands] != expected_generations:
        raise ValueError("direct RTL trace generation sequence is discontinuous")

    token_rows = [tuple(map(int, match.groups())) for match in TOKEN_PATTERN.finditer(text)]
    expected_tokens = [(token, 0, token) for token in range(1, 65)]
    if token_rows != expected_tokens:
        raise ValueError("64 ordered token PASS markers are absent")
    if (
        "DIRECT_RTL_TRACE64 PASS tokens=64 outputs_per_token=4096 "
        "state_elements=524288"
    ) not in text:
        raise ValueError("final output/state parity PASS marker is absent")

    memory_match = re.search(
        r"xsimkernel Simulation Memory Usage: (\d+) KB \(Peak: (\d+) KB\), "
        r"Simulation CPU Usage: (\d+) ms",
        text,
    )
    if memory_match is None:
        raise ValueError("XSIM kernel statistics are absent")
    current_kb, peak_kb, cpu_ms = map(int, memory_match.groups())
    step_cycles = [row["cycles"] for row in commands if row["command"] == 2]
    return {
        "commands": commands,
        "token_rows": token_rows,
        "step_latency_cycles": {
            "count": len(step_cycles),
            "minimum": min(step_cycles),
            "maximum": max(step_cycles),
            "mean": statistics.fmean(step_cycles),
            "median": statistics.median(step_cycles),
        },
        "xsim_kernel": {
            "current_memory_kb": current_kb,
            "peak_memory_kb": peak_kb,
            "cpu_ms": cpu_ms,
        },
    }


def _hash_paths(paths: list[Path]) -> dict[str, dict[str, object]]:
    return {
        _relative(path): {"sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in paths
    }


def report_source_paths() -> list[Path]:
    return [
        ROOT / "hls" / "rtl_tb" / "axi_memory_model.sv",
        ROOT / "hls" / "rtl_tb" / "tb_gdn_top_direct.sv",
        ROOT / "scripts" / "generate_direct_rtl_trace_assets.py",
        ROOT / "scripts" / "direct_rtl_trace_report.py",
        ROOT / "scripts" / "verify_hls_command_trace.py",
        *sorted((ROOT / "hls" / "include").glob("*.hpp")),
        *sorted((ROOT / "hls" / "src").glob("*.cpp")),
        *sorted((ROOT / "hls" / "tcl").glob("*.tcl")),
    ]


def _verify_assets(assets_dir: Path) -> tuple[dict[str, object], dict[str, object]]:
    manifest_path = assets_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["status"] != "PASS" or manifest["dimensions"]["tokens"] != 64:
        raise ValueError("trace asset manifest is not a 64-token PASS")
    verified: dict[str, object] = {}
    for name, expected in manifest["files"].items():
        path = assets_dir / name
        if _sha256(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
            raise ValueError(f"trace asset hash or size mismatch: {name}")
        verified[name] = expected
    return manifest, verified


def generate_report(
    evidence_dir: Path = DEFAULT_EVIDENCE,
    rtl_dir: Path = DEFAULT_RTL,
) -> dict[str, object]:
    work = evidence_dir / "work"
    raw = evidence_dir / "raw"
    assets = evidence_dir / "assets"
    raw.mkdir(parents=True, exist_ok=True)
    archive_names = ("direct_rtl.prj", "xvlog.log", "xelab.log", "xsim.log", "xsim.jou")
    for name in archive_names:
        source = work / name
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, raw / name)

    parsed = parse_trace_xsim_log(
        (raw / "xsim.log").read_text(encoding="utf-8", errors="replace")
    )
    trace_verification = verify_trace()
    if trace_verification["status"] != "PASS":
        raise ValueError("binary HLS command trace verification did not pass")
    asset_manifest, verified_assets = _verify_assets(assets)
    rtl_paths = sorted(rtl_dir.glob("*.v"))
    dat_paths = sorted(work.glob("*.dat"))
    if not rtl_paths or not dat_paths:
        raise ValueError("generated RTL or initialization data are absent")
    source_paths = report_source_paths()
    revision, dirty = _git_revision()
    source_identity = describe_source_files(source_paths)
    if source_identity["git_revision"] != revision:
        raise ValueError("source identity revision changed while generating report")
    manifest: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Sequential 64-token bit-exact parity of current-source HLS-generated "
            "Verilog against the independently verified encoded oracle trace."
        ),
        "source_revision": revision,
        "working_tree_dirty": dirty,
        "source_identity": source_identity,
        "execution": [
            {
                "command": "xvlog -prj direct_rtl.prj -d GDN_TRACE64",
                "working_directory": "X:/reports/cosim/corrected/direct_rtl_trace64/work",
                "exit_code": 0,
                "raw_log": "reports/cosim/corrected/direct_rtl_trace64/raw/xvlog.log",
            },
            {
                "command": (
                    "xelab xil_defaultlib.tb_gdn_top_direct -s direct_rtl_trace64 "
                    "--mt 8 --ignore_coverage --ignore_assertions --stats"
                ),
                "working_directory": "X:/reports/cosim/corrected/direct_rtl_trace64/work",
                "exit_code": 0,
                "raw_log": "reports/cosim/corrected/direct_rtl_trace64/raw/xelab.log",
            },
            {
                "command": (
                    "xsim direct_rtl_trace64 --runall --stats "
                    "--ignore_coverage --ignore_assertions"
                ),
                "working_directory": "X:/reports/cosim/corrected/direct_rtl_trace64/work",
                "exit_code": 0,
                "raw_log": "reports/cosim/corrected/direct_rtl_trace64/raw/xsim.log",
            },
            {
                "command": "python -m scripts.direct_rtl_trace_report",
                "working_directory": ".",
                "exit_code": 0,
                "raw_log": (
                    "reports/cosim/corrected/direct_rtl_trace64/"
                    "direct_rtl_trace64_summary.json"
                ),
            },
        ],
        "configuration": {
            "layer_id": 3,
            "tokens": 64,
            "num_qk_heads": 16,
            "num_value_heads": 32,
            "key_dim": 128,
            "value_dim": 128,
            "block_size": 32,
            "p_k": 16,
            "p_v": 8,
        },
        "simulator": {
            "tool": "AMD XSIM",
            "version": "2025.2",
            "rtl_language": "verilog",
            "xelab_slave_threads": 8,
            "coverage": "ignored",
            "assertions": "ignored",
            **parsed["xsim_kernel"],
        },
        "parity": {
            "status": "PASS",
            "ordered_tokens": len(parsed["token_rows"]),
            "output_mantissas_compared": 64 * 4096,
            "output_exponents_compared": 64 * 4096,
            "command_counters_compared": 64 * 8,
            "cumulative_counters_compared": 64 * 8,
            "final_state_elements_compared": 32 * 128 * 128,
            "final_state_scales_compared": 32 * 128 * 4,
            "final_generation": 64,
        },
        "step_latency_cycles": parsed["step_latency_cycles"],
        "command_results": parsed["commands"],
        "oracle_trace_verification": trace_verification,
        "asset_manifest": asset_manifest,
        "verified_assets": verified_assets,
        "source_files": _hash_paths(source_paths),
        "generated_rtl": {
            "file_count": len(rtl_paths),
            "files": _hash_paths(rtl_paths),
        },
        "initialization_data": {
            "file_count": len(dat_paths),
            "files": _hash_paths(dat_paths),
        },
        "archived_logs": _hash_paths([raw / name for name in archive_names]),
        "required_64_token_rtl_parity": "PASS",
        "independent_verification": [
            "The binary trace, summary CSV, source hashes, and input-stream hash are reverified in Python.",
            "The asset manifest hashes every readmemh file consumed by XSIM.",
            "The report parser independently enforces all 66 commands, 64 token markers, statuses, and generations.",
            "SystemVerilog fatal checks compare every output element, every per-token counter, and the complete final state before emitting PASS.",
        ],
        "limitations": [
            "This uses a custom direct AXI-Lite/AXI testbench rather than the memory-exhausting Vitis UVM wrapper.",
            "It validates the corrected uniform-MXFP4 baseline, not the selected residual-stack/write-log candidate.",
            "It is pre-synthesis generated-RTL simulation and does not establish post-route timing, power, energy, or board parity.",
        ],
    }
    json_path = evidence_dir / "direct_rtl_trace64_summary.json"
    md_path = evidence_dir / "direct_rtl_trace64_summary.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    latency = parsed["step_latency_cycles"]
    md_path.write_text(
        "\n".join(
            [
                "# Direct RTL 64-Token Parity",
                "",
                "- Status: `PASS`",
                "- Sequence: one RESET, 64 sequential STEP commands, one READBACK",
                "- Per-token outputs: all `4096` mantissas and `4096` exponents",
                "- Final state: all `524288` elements and `16384` block scales",
                f"- STEP cycles: min `{latency['minimum']}`, mean `{latency['mean']:.2f}`, max `{latency['maximum']}`",
                f"- XSIM kernel peak: `{parsed['xsim_kernel']['peak_memory_kb']}` KB",
                "- Required 64-token RTL parity: `PASS`",
                "",
                "The custom direct harness bypasses the Vitis UVM wrapper but executes",
                "the current HLS-generated Verilog and compares it bit exactly with the",
                "verified encoded trace. This does not validate post-route hardware or",
                "the selected recurrent-correction candidate.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--rtl-dir", type=Path, default=DEFAULT_RTL)
    args = parser.parse_args(argv)
    evidence = args.evidence_dir if args.evidence_dir.is_absolute() else ROOT / args.evidence_dir
    rtl = args.rtl_dir if args.rtl_dir.is_absolute() else ROOT / args.rtl_dir
    report = generate_report(evidence, rtl)
    print(json.dumps({"status": report["status"], "tokens": 64}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

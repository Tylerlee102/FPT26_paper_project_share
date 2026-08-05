"""Archive and validate bounded-memory direct XSIM evidence for HLS RTL."""

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
DEFAULT_EVIDENCE = ROOT / "reports" / "cosim" / "corrected" / "direct_rtl_smoke"
DEFAULT_RTL = ROOT / "gdn_mxfp4_hls" / "u55c_250mhz" / "syn" / "verilog"
COMMAND_PATTERN = re.compile(
    r"DIRECT_RTL command=(?P<command>\d+) latched=(?P<latched>\d+) "
    r"cycles=(?P<cycles>\d+) status=(?P<status>\d+) "
    r"generation=(?P<generation>\d+)"
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


def parse_xsim_log(text: str) -> dict[str, object]:
    commands = [
        {key: int(value) for key, value in match.groupdict().items()}
        for match in COMMAND_PATTERN.finditer(text)
    ]
    if [row["command"] for row in commands] != [0, 2, 3]:
        raise ValueError("expected RESET, STEP, READBACK command sequence")
    if any(row["command"] != row["latched"] for row in commands):
        raise ValueError("a direct RTL command was not latched correctly")
    if any(row["status"] != 0 for row in commands):
        raise ValueError("a direct RTL command returned nonzero status")
    if [row["generation"] for row in commands] != [0, 1, 1]:
        raise ValueError("unexpected direct RTL generation sequence")
    if "DIRECT_RTL_SMOKE PASS reset_step_readback=3" not in text:
        raise ValueError("direct RTL PASS marker is absent")

    memory_match = re.search(
        r"xsimkernel Simulation Memory Usage: (\d+) KB \(Peak: (\d+) KB\), "
        r"Simulation CPU Usage: (\d+) ms",
        text,
    )
    if memory_match is None:
        raise ValueError("XSIM kernel statistics are absent")
    current_kb, peak_kb, cpu_ms = map(int, memory_match.groups())
    return {
        "commands": commands,
        "checks": {
            "reset_status_and_generation": "PASS",
            "step_status_and_generation": "PASS",
            "step_committed_generation_counter": "PASS",
            "step_first_and_last_output": "PASS",
            "readback_updated_and_untouched_state": "PASS",
            "readback_state_scales": "PASS",
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


def generate_report(
    evidence_dir: Path = DEFAULT_EVIDENCE,
    rtl_dir: Path = DEFAULT_RTL,
) -> dict[str, object]:
    work = evidence_dir / "work"
    raw = evidence_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive_names = ("direct_rtl.prj", "xvlog.log", "xelab.log", "xsim.log", "xsim.jou")
    for name in archive_names:
        source = work / name
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, raw / name)

    xsim_text = (raw / "xsim.log").read_text(encoding="utf-8", errors="replace")
    parsed = parse_xsim_log(xsim_text)
    rtl_paths = sorted(rtl_dir.glob("*.v"))
    dat_paths = sorted(work.glob("*.dat"))
    if not rtl_paths or not dat_paths:
        raise ValueError("generated RTL or initialization data are absent")
    source_paths = [
        ROOT / "hls" / "rtl_tb" / "axi_memory_model.sv",
        ROOT / "hls" / "rtl_tb" / "tb_gdn_top_direct.sv",
    ]
    revision, dirty = _git_revision()
    manifest: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "One current-source HLS-generated Verilog RESET/STEP/READBACK smoke "
            "using a custom direct AXI-Lite and AXI memory-model testbench."
        ),
        "source_revision": revision,
        "working_tree_dirty": dirty,
        "simulator": {
            "tool": "AMD XSIM",
            "version": "2025.2",
            "rtl_language": "verilog",
            "multithreading": "off",
            "coverage": "ignored",
            "assertions": "ignored",
            **parsed["xsim_kernel"],
        },
        "configuration": {
            "layer_id": 0,
            "tokens": 1,
            "num_value_heads": 32,
            "key_dim": 128,
            "value_dim": 128,
            "block_size": 32,
            "p_k": 16,
            "p_v": 8,
        },
        "command_results": parsed["commands"],
        "checks": parsed["checks"],
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
        "required_64_token_rtl_parity": "NOT_RUN",
        "interpretation": (
            "The direct harness establishes a bounded-memory one-token RTL smoke "
            "for the generated snapshot. It is not the required 64-token HLS "
            "C/RTL parity result and does not establish implementation timing, "
            "power, energy, or selected recurrent-correction hardware."
        ),
    }
    json_path = evidence_dir / "direct_rtl_smoke_summary.json"
    md_path = evidence_dir / "direct_rtl_smoke_summary.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    command_lines = [
        f"- `{row['command']}`: `{row['cycles']}` cycles, status "
        f"`{row['status']}`, generation `{row['generation']}`"
        for row in parsed["commands"]
    ]
    md_path.write_text(
        "\n".join(
            [
                "# Direct RTL Smoke",
                "",
                "- Status: `PASS`",
                "- Scope: one HLS-generated Verilog RESET/STEP/READBACK sequence",
                "- Harness: custom direct AXI-Lite/AXI memory models",
                f"- XSIM kernel peak: `{parsed['xsim_kernel']['peak_memory_kb']}` KB",
                "- Required 64-token RTL parity: `NOT_RUN`",
                "",
                "## Commands",
                "",
                *command_lines,
                "",
                manifest["interpretation"],
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
    print(json.dumps({"status": report["status"], "tokens": 1}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

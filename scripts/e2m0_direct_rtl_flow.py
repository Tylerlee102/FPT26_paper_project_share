"""Compile and run the corrected E2M0 generated RTL with Verilator in WSL."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.e2m0_direct_rtl_trace_report import EVIDENCE, RTL, generate_report
from scripts.generate_e2m0_direct_rtl_trace_assets import generate_assets


ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "hls" / "rtl_tb" / "tb_gdn_e2m0_top_direct.sv"
AXI = ROOT / "hls" / "rtl_tb" / "axi_memory_model.sv"


def _run(
    command: list[str],
    *,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def _wsl_path(path: Path, distro: str) -> str:
    result = _run(
        ["wsl.exe", "-d", distro, "--", "wslpath", "-a", str(path.resolve())],
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"wslpath failed for {path}: {result.stdout}")
    return result.stdout.strip()


def _bash(distro: str, script: str, *, timeout: int) -> subprocess.CompletedProcess[str]:
    return _run(
        ["wsl.exe", "-d", distro, "--", "bash", "-lc", script],
        timeout=timeout,
    )


def run_flow(
    *,
    distro: str = "Ubuntu-24.04",
    evidence: Path = EVIDENCE,
    rtl: Path = RTL,
    jobs: int = 4,
    model_threads: int = 1,
    token_limit: int = 64,
) -> dict[str, object]:
    for path in (TB, AXI, rtl):
        if not path.exists():
            raise FileNotFoundError(path)
    if len(list(rtl.glob("*.v"))) < 100 or not list(rtl.glob("*.dat")):
        raise ValueError("the corrected-candidate HLS RTL directory is incomplete")
    assets = evidence / "assets"
    manifest = generate_assets(output_dir=assets)
    raw = evidence / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    version = _run(
        ["wsl.exe", "-d", distro, "--", "verilator", "--version"], timeout=30
    )
    if version.returncode != 0:
        raise RuntimeError(f"Verilator is unavailable in {distro}: {version.stdout}")
    temp_root = f"/tmp/gdn_e2m0_direct_{os.getpid()}"
    rtl_wsl = _wsl_path(rtl, distro)
    tb_wsl = _wsl_path(TB, distro)
    axi_wsl = _wsl_path(AXI, distro)
    assets_wsl = _wsl_path(assets, distro)
    setup = "\n".join(
        [
            "set -euo pipefail",
            f"rm -rf -- {shlex.quote(temp_root)}",
            f"mkdir -p {shlex.quote(temp_root + '/src')} {shlex.quote(temp_root + '/run/assets')} {shlex.quote(temp_root + '/obj')}",
            f"cp {shlex.quote(rtl_wsl)}/*.v {shlex.quote(temp_root + '/src/')}",
            f"cp {shlex.quote(rtl_wsl)}/*.dat {shlex.quote(temp_root + '/run/')}",
            f"cp {shlex.quote(tb_wsl)} {shlex.quote(axi_wsl)} {shlex.quote(temp_root + '/src/')}",
            f"cp {shlex.quote(assets_wsl)}/*.hex {shlex.quote(temp_root + '/run/assets/')}",
        ]
    )
    setup_result = _bash(distro, setup, timeout=300)
    if setup_result.returncode != 0:
        raise RuntimeError(f"WSL staging failed: {setup_result.stdout}")

    compile_command = " ".join(
        [
            "/usr/bin/time -v -o",
            shlex.quote(temp_root + "/compile_time.log"),
            "verilator --binary --timing --top-module tb_gdn_e2m0_top_direct",
            f"-j {max(1, jobs)} -O3 --threads {max(1, model_threads)} -CFLAGS -O3 "
            "--output-split 20000 --output-split-cfuncs 20000",
            "-Wno-fatal -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-UNOPTFLAT",
            "-Wno-LATCH -Wno-CMPCONST -Wno-UNSIGNED -Wno-CASEINCOMPLETE",
            "-Wno-TIMESCALEMOD -Wno-INITIALDLY",
            "--Mdir",
            shlex.quote(temp_root + "/obj"),
            shlex.quote(temp_root + "/src/axi_memory_model.sv"),
            shlex.quote(temp_root + "/src/tb_gdn_e2m0_top_direct.sv"),
            shlex.quote(temp_root + "/src") + "/*.v",
        ]
    )
    print("Compiling 151 HLS-generated Verilog files with Verilator...", flush=True)
    compile_result = _bash(distro, compile_command, timeout=7200)
    (raw / "verilator_compile.log").write_text(
        compile_result.stdout, encoding="utf-8", errors="replace"
    )
    copy_compile_time = _bash(
        distro,
        f"cp {shlex.quote(temp_root + '/compile_time.log')} {_shell_path(raw / 'verilator_compile_time.log', distro)}",
        timeout=60,
    )
    if copy_compile_time.returncode != 0:
        raise RuntimeError(f"could not archive compile timing: {copy_compile_time.stdout}")
    if compile_result.returncode != 0:
        raise RuntimeError(
            "Verilator compilation failed; see reports/cosim/corrected/"
            "e2m0_direct_rtl_trace64/raw/verilator_compile.log\n"
            + compile_result.stdout[-4000:]
        )

    run_command = " ".join(
        [
            "set -o pipefail; cd",
            shlex.quote(temp_root + "/run"),
            "&& /usr/bin/time -v -o",
            shlex.quote(temp_root + "/run_time.log"),
            shlex.quote(temp_root + "/obj/Vtb_gdn_e2m0_top_direct"),
            f"+TOKEN_LIMIT={token_limit}",
        ]
    )
    if args.token_limit == 0:
        stage = "LOAD-only exact RTL check"
    else:
        stage = f"LOAD + {args.token_limit} STEP + READBACK exact RTL trace"
    print(f"Running {stage}...", flush=True)
    simulation_result = _bash(distro, run_command, timeout=7200)
    (raw / "verilator_run.log").write_text(
        simulation_result.stdout, encoding="utf-8", errors="replace"
    )
    copy_run_time = _bash(
        distro,
        f"cp {shlex.quote(temp_root + '/run_time.log')} {_shell_path(raw / 'verilator_run_time.log', distro)}",
        timeout=60,
    )
    if copy_run_time.returncode != 0:
        raise RuntimeError(f"could not archive simulation timing: {copy_run_time.stdout}")

    execution = {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "distro": distro,
        "verilator_version": version.stdout.strip(),
        "jobs": jobs,
        "model_threads": model_threads,
        "token_limit": token_limit,
        "temporary_build_directory": temp_root,
        "compile_exit_code": compile_result.returncode,
        "simulation_exit_code": simulation_result.returncode,
        "source_verilog_files": len(list(rtl.glob("*.v"))),
        "source_initialization_files": len(list(rtl.glob("*.dat"))),
        "asset_files": len(manifest["files"]),
        "compile_command": compile_command,
        "simulation_command": run_command,
    }
    (raw / "execution.json").write_text(
        json.dumps(execution, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if simulation_result.returncode != 0:
        raise RuntimeError(
            "Verilator simulation failed; see reports/cosim/corrected/"
            "e2m0_direct_rtl_trace64/raw/verilator_run.log\n"
            + simulation_result.stdout[-4000:]
        )
    if token_limit == 64:
        report = generate_report(evidence=evidence, rtl=rtl)
    else:
        marker = f"E2M0_DIRECT_RTL_BENCHMARK PASS tokens={token_limit}"
        if marker not in simulation_result.stdout:
            raise RuntimeError("bounded Verilator benchmark PASS marker is absent")
        report = {
            "status": "PASS",
            "scope": "bounded host-simulator throughput benchmark; not parity evidence",
            "tokens": token_limit,
            "model_threads": model_threads,
            "execution": execution,
        }
        (evidence / f"benchmark_t{model_threads}_{token_limit}token.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    cleanup = _bash(distro, f"rm -rf -- {shlex.quote(temp_root)}", timeout=120)
    if cleanup.returncode != 0:
        print(f"Warning: temporary WSL build was not removed: {temp_root}", flush=True)
    return report


def _shell_path(path: Path, distro: str) -> str:
    return shlex.quote(_wsl_path(path, distro))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distro", default="Ubuntu-24.04")
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--rtl", type=Path, default=RTL)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--model-threads", type=int, default=1)
    parser.add_argument("--token-limit", type=int, default=64)
    args = parser.parse_args(argv)
    evidence = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    rtl = args.rtl if args.rtl.is_absolute() else ROOT / args.rtl
    report = run_flow(
        distro=args.distro,
        evidence=evidence,
        rtl=rtl,
        jobs=args.jobs,
        model_threads=args.model_threads,
        token_limit=args.token_limit,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "tokens": args.token_limit,
                "transactions": 66 if args.token_limit == 64 else args.token_limit + 1,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

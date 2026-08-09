"""Run exact RS2/R3 generated RTL with a scheduler-free Verilator harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.generate_rs2_direct_rtl_trace_assets import generate_assets
from scripts.generate_rs2_fast_wrapper import DEFAULT_OUTPUT as WRAPPER
from scripts.generate_rs2_fast_wrapper import generate as generate_wrapper
from scripts.rs2_direct_rtl_flow import _bash, _run, _wsl_path
from scripts.rs2_direct_rtl_trace_report import CANONICAL, RTL, generate_report


ROOT = Path(__file__).resolve().parents[1]
MEMORY = WRAPPER.with_name("axi_memory_model_fast.sv")
HARNESS = ROOT / "hls" / "rtl_tb" / "rs2_fast_harness.cpp"
DEFAULT_EVIDENCE = (
    ROOT / "reports" / "cosim" / "corrected" / "rs2_fast_direct_rtl_trace64"
)


def _build_key(paths: list[Path], version: str, model_threads: int) -> str:
    digest = hashlib.sha256()
    digest.update(version.encode("utf-8"))
    digest.update(f"model_threads={model_threads}\n".encode("ascii"))
    digest.update(b"scheduler_free_no_timing_v1\n")
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()[:20]


def run_flow(
    *,
    distro: str = "Ubuntu-24.04",
    evidence: Path = DEFAULT_EVIDENCE,
    rtl: Path = RTL,
    jobs: int = 8,
    model_threads: int = 8,
    token_limit: int = 64,
    simulation_timeout_seconds: int | None = None,
) -> dict[str, object]:
    if token_limit < 0 or token_limit > 64:
        raise ValueError("token_limit must be in [0,64]")
    wrapper_manifest = generate_wrapper(WRAPPER, MEMORY)
    for path in (WRAPPER, MEMORY, HARNESS, rtl):
        if not path.exists():
            raise FileNotFoundError(path)
    rtl_paths = sorted(rtl.glob("*.v"))
    dat_paths = sorted(rtl.glob("*.dat"))
    if len(rtl_paths) < 100 or not dat_paths:
        raise ValueError("the selected RS2/R3 generated RTL directory is incomplete")

    assets = evidence / "assets"
    asset_manifest = generate_assets(output_dir=assets)
    raw = (
        evidence / "raw"
        if token_limit == 64
        else evidence / "benchmarks" / f"t{model_threads}_{token_limit}token" / "raw"
    )
    raw.mkdir(parents=True, exist_ok=True)

    version_result = _run(
        ["wsl.exe", "-d", distro, "--", "verilator", "--version"], timeout=30
    )
    if version_result.returncode != 0:
        raise RuntimeError(f"Verilator is unavailable in {distro}: {version_result.stdout}")
    version = version_result.stdout.strip()
    build_paths = [WRAPPER, MEMORY, HARNESS, *rtl_paths]
    build_key = _build_key(build_paths, version, model_threads)
    temp_root = f"/tmp/gdn_rs2_fast_cache_{build_key}"
    binary = f"{temp_root}/obj/Vrs2_fast_wrapper"

    rtl_wsl = _wsl_path(rtl, distro)
    wrapper_wsl = _wsl_path(WRAPPER, distro)
    memory_wsl = _wsl_path(MEMORY, distro)
    harness_wsl = _wsl_path(HARNESS, distro)
    assets_wsl = _wsl_path(assets, distro)
    cache_probe = _bash(
        distro,
        f"test -x {shlex.quote(binary)} -a -f {shlex.quote(temp_root + '/compile_time.log')}",
        timeout=30,
    )
    cache_hit = cache_probe.returncode == 0
    setup_lines = ["set -euo pipefail"]
    if not cache_hit:
        setup_lines.extend(
            [
                f"rm -rf -- {shlex.quote(temp_root)}",
                f"mkdir -p {shlex.quote(temp_root + '/src')} {shlex.quote(temp_root + '/obj')}",
                f"cp {shlex.quote(rtl_wsl)}/*.v {shlex.quote(temp_root + '/src/')}",
                f"cp {shlex.quote(wrapper_wsl)} {shlex.quote(memory_wsl)} {shlex.quote(harness_wsl)} {shlex.quote(temp_root + '/src/')}",
            ]
        )
    setup_lines.extend(
        [
            f"rm -rf -- {shlex.quote(temp_root + '/run')}",
            f"mkdir -p {shlex.quote(temp_root + '/run/assets')}",
            f"cp {shlex.quote(rtl_wsl)}/*.dat {shlex.quote(temp_root + '/run/')}",
            f"cp {shlex.quote(assets_wsl)}/*.hex {shlex.quote(temp_root + '/run/assets/')}",
        ]
    )
    setup = _bash(distro, "\n".join(setup_lines), timeout=300)
    if setup.returncode != 0:
        raise RuntimeError(f"WSL staging failed: {setup.stdout}")

    cflags = f"-O3 -std=c++17 -DRS2_MODEL_THREADS={model_threads}"
    compile_command = " ".join(
        [
            "/usr/bin/time -v -o",
            shlex.quote(temp_root + "/compile_time.log"),
            "verilator --cc --exe --build --top-module rs2_fast_wrapper",
            f"-j {max(1, jobs)} -O3 --threads {max(1, model_threads)} --no-timing",
            "-CFLAGS",
            shlex.quote(cflags),
            "--output-split 20000 --output-split-cfuncs 20000",
            "-Wno-fatal -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-UNOPTFLAT",
            "-Wno-LATCH -Wno-CMPCONST -Wno-UNSIGNED -Wno-CASEINCOMPLETE",
            "-Wno-TIMESCALEMOD -Wno-INITIALDLY -Wno-STMTDLY",
            "--Mdir",
            shlex.quote(temp_root + "/obj"),
            shlex.quote(temp_root + "/src/axi_memory_model_fast.sv"),
            shlex.quote(temp_root + "/src/rs2_fast_wrapper.sv"),
            shlex.quote(temp_root + "/src") + "/*.v",
            shlex.quote(temp_root + "/src/rs2_fast_harness.cpp"),
        ]
    )
    if cache_hit:
        compile_result = subprocess.CompletedProcess(
            args=["verilator-cache", build_key],
            returncode=0,
            stdout=f"CACHE_HIT key={build_key}\n",
        )
    else:
        compile_result = _bash(distro, compile_command, timeout=7200)
    (raw / "verilator_compile.log").write_text(
        compile_result.stdout, encoding="utf-8", errors="replace"
    )
    compile_time_target = _wsl_path(raw / "verilator_compile_time.log", distro)
    copied = _bash(
        distro,
        f"cp {shlex.quote(temp_root + '/compile_time.log')} {shlex.quote(compile_time_target)}",
        timeout=60,
    )
    if compile_result.returncode != 0 or copied.returncode != 0:
        raise RuntimeError("scheduler-free Verilator compilation failed")

    timeout_seconds = simulation_timeout_seconds
    if timeout_seconds is None:
        timeout_seconds = 12 * 3600 if token_limit == 64 else 3600
    run_log = raw / "verilator_run.log"
    run_log_wsl = _wsl_path(run_log, distro)
    run_command = " ".join(
        [
            "set -o pipefail; cd",
            shlex.quote(temp_root + "/run"),
            "&& /usr/bin/time -v -o",
            shlex.quote(temp_root + "/run_time.log"),
            "stdbuf -oL -eL",
            shlex.quote(binary),
            "assets",
            str(token_limit),
            f"2>&1 | tee {shlex.quote(run_log_wsl)}",
        ]
    )
    simulation_result = _bash(distro, run_command, timeout=timeout_seconds)
    if not run_log.is_file():
        run_log.write_text(
            simulation_result.stdout, encoding="utf-8", errors="replace"
        )
    run_time_target = _wsl_path(raw / "verilator_run_time.log", distro)
    copied = _bash(
        distro,
        f"cp {shlex.quote(temp_root + '/run_time.log')} {shlex.quote(run_time_target)}",
        timeout=60,
    )
    execution = {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "distro": distro,
        "verilator_version": version,
        "harness_mode": "scheduler_free_cpp",
        "jobs": jobs,
        "model_threads": model_threads,
        "token_limit": token_limit,
        "simulation_timeout_seconds": timeout_seconds,
        "build_cache_key": build_key,
        "build_cache_hit": cache_hit,
        "compile_exit_code": compile_result.returncode,
        "simulation_exit_code": simulation_result.returncode,
        "source_verilog_files": len(rtl_paths),
        "source_initialization_files": len(dat_paths),
        "asset_files": len(asset_manifest["files"]),
        "wrapper_manifest": wrapper_manifest,
        "zero_delay_policy": (
            "Verilator --no-timing; the wrapper contains no timed process and only "
            "HLS-generated #0 initialization delays are ignored"
        ),
        "compile_command": compile_command,
        "simulation_command": run_command,
    }
    (raw / "execution.json").write_text(
        json.dumps(execution, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if simulation_result.returncode != 0 or copied.returncode != 0:
        raise RuntimeError(
            "scheduler-free Verilator simulation failed; see "
            f"{run_log.relative_to(ROOT).as_posix()}"
        )

    if token_limit == 64:
        return generate_report(
            evidence=evidence,
            canonical=CANONICAL,
            rtl=rtl,
            harness_mode="scheduler_free_cpp",
        )
    marker = f"RS2_DIRECT_RTL_BENCHMARK PASS tokens={token_limit}"
    if marker not in run_log.read_text(encoding="utf-8", errors="replace"):
        raise RuntimeError("bounded scheduler-free benchmark PASS marker is absent")
    report = {
        "status": "PASS",
        "scope": "bounded exact scheduler-free generated-RTL benchmark",
        "tokens": token_limit,
        "model_threads": model_threads,
        "execution": execution,
    }
    (evidence / f"benchmark_fast_t{model_threads}_{token_limit}token.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distro", default="Ubuntu-24.04")
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--rtl", type=Path, default=RTL)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--model-threads", type=int, default=8)
    parser.add_argument("--token-limit", type=int, default=64)
    parser.add_argument("--simulation-timeout-seconds", type=int)
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
        simulation_timeout_seconds=args.simulation_timeout_seconds,
    )
    print(json.dumps({"status": report["status"], "tokens": args.token_limit}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

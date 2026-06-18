from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .sweep import CONFIGS


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
OUT_DIR = ROOT / "reports" / "benchmark" / "sweeps"
TOP_COSIM = ROOT / "reports" / "cosim"
TOP_CSYNTH = ROOT / "reports" / "csynth"
COSIM_REPORTS = ("gdn_top_cosim.rpt", "latency.csv", "summary.md")


def _copy_file_if_exists(source: Path, dst: Path) -> None:
    if source.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dst)


def _replace_generated_dir(source: Path, dst: Path, names: tuple[str, ...]) -> None:
    dst.relative_to(OUT_DIR)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for name in names:
        _copy_file_if_exists(source / name, dst / name)


def _restore_generated_dir(source: Path, dst: Path, names: tuple[str, ...]) -> None:
    if not source.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for name in names:
        _copy_file_if_exists(source / name, dst / name)


def _run(command: list[str], *, env: dict[str, str], timeout_seconds: int | None, allow_timeout: bool = False) -> None:
    proc = subprocess.Popen(command, cwd=ROOT, env=env)
    try:
        rc = proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], cwd=ROOT, check=False)
        else:
            proc.kill()
            proc.wait()
        if allow_timeout:
            return
        raise RuntimeError(f"{' '.join(command)} timed out after {timeout_seconds} seconds")
    if rc != 0:
        raise RuntimeError(f"{' '.join(command)} failed with exit code {rc}")


def _env_for(config_name: str, tokens: int) -> dict[str, str]:
    configs = {config.name: config for config in CONFIGS}
    config = configs[config_name]
    env = os.environ.copy()
    env["GDN_P_K"] = str(config.p_k)
    env["GDN_P_V"] = str(config.p_v)
    env["GDN_BLOCK_SIZE"] = str(config.block_size)
    env["GDN_COSIM_VECTORS"] = str(tokens)
    return env


def _snapshot_default_cosim() -> None:
    if (TOP_COSIM / "latency.csv").exists():
        _replace_generated_dir(TOP_COSIM, OUT_DIR / "parallel_pk16_pv8_b32" / "cosim", COSIM_REPORTS)


def _restore_default_reports() -> None:
    _restore_generated_dir(OUT_DIR / "parallel_pk16_pv8_b32" / "cosim", TOP_COSIM, COSIM_REPORTS)
    _copy_file_if_exists(OUT_DIR / "parallel_pk16_pv8_b32" / "util.md", TOP_CSYNTH / "util.md")


def _run_config(config_name: str, *, tokens: int, skip_csynth: bool, timeout_seconds: int) -> None:
    env = _env_for(config_name, tokens)
    if not skip_csynth:
        print(f"Running HLS csynth for {config_name}")
        _run([PYTHON, "-m", "scripts.hls_flow", "csynth"], env=env, timeout_seconds=timeout_seconds)
        _run([PYTHON, "-m", "scripts.hls_report"], env=env, timeout_seconds=300)
        _copy_file_if_exists(TOP_CSYNTH / "util.md", OUT_DIR / config_name / "util.md")

    print(f"Running RTL cosim for {config_name} ({tokens} tokens)")
    _run([PYTHON, "-m", "scripts.hls_flow", "cosim"], env=env, timeout_seconds=timeout_seconds, allow_timeout=True)
    _run([PYTHON, "-m", "scripts.cosim_report"], env=env, timeout_seconds=300)
    _replace_generated_dir(TOP_COSIM, OUT_DIR / config_name / "cosim", COSIM_REPORTS)
    print(f"Copied cosim reports for {config_name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and archive RTL cosim latency for Phase 6 sweep points.")
    parser.add_argument("--configs", nargs="*", default=[config.name for config in CONFIGS if config.name != "parallel_pk16_pv8_b32"])
    parser.add_argument("--tokens", type=int, default=64)
    parser.add_argument("--timeout-seconds", type=int, default=14_400)
    parser.add_argument("--skip-csynth", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args(argv)

    known = {config.name for config in CONFIGS}
    unknown = [name for name in args.configs if name not in known]
    if unknown:
        raise ValueError(f"Unknown sweep config(s): {', '.join(unknown)}")

    _snapshot_default_cosim()
    try:
        for config_name in args.configs:
            if args.skip_existing and (OUT_DIR / config_name / "cosim" / "latency.csv").exists():
                print(f"Skipping {config_name}; cosim latency already exists")
                continue
            _run_config(
                config_name,
                tokens=args.tokens,
                skip_csynth=args.skip_csynth,
                timeout_seconds=args.timeout_seconds,
            )
    finally:
        _restore_default_reports()

    subprocess.run([PYTHON, "-m", "scripts.sweep", "--plan"], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

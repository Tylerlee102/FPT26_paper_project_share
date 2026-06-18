from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .sweep import CONFIGS


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
OUT_DIR = ROOT / "reports" / "benchmark" / "sweeps"
VIVADO_REPORTS = (
    "synth_util.rpt",
    "synth_timing.rpt",
    "impl_util.rpt",
    "impl_timing.rpt",
    "impl_power.rpt",
    "summary.md",
)


def _copy_vivado_reports(config_name: str) -> None:
    dst = OUT_DIR / config_name / "vivado"
    dst.mkdir(parents=True, exist_ok=True)
    for name in VIVADO_REPORTS:
        source = ROOT / "reports" / "vivado" / name
        if source.exists():
            shutil.copyfile(source, dst / name)


def _run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(command)} failed with exit code {result.returncode}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Vivado implementation for Phase 6 sweep configs.")
    parser.add_argument("--configs", nargs="*", default=[config.name for config in CONFIGS])
    parser.add_argument("--skip-csynth", action="store_true", help="Use the current HLS RTL instead of rebuilding it.")
    args = parser.parse_args(argv)

    configs = {config.name: config for config in CONFIGS}
    unknown = [name for name in args.configs if name not in configs]
    if unknown:
        raise ValueError(f"Unknown sweep config(s): {', '.join(unknown)}")

    for name in args.configs:
        config = configs[name]
        env_args = [
            f"GDN_P_K={config.p_k}",
            f"GDN_P_V={config.p_v}",
            f"GDN_BLOCK_SIZE={config.block_size}",
        ]
        if not args.skip_csynth:
            print(f"Running HLS csynth for {name} ({', '.join(env_args)})")
            env_prefix = (
                "$env:GDN_P_K='{}'; $env:GDN_P_V='{}'; $env:GDN_BLOCK_SIZE='{}'; ".format(
                    config.p_k, config.p_v, config.block_size
                )
            )
            _run(["powershell.exe", "-NoProfile", "-Command", env_prefix + f"& '{PYTHON}' -m scripts.hls_flow csynth"])
            _run([PYTHON, "-m", "scripts.hls_report"])

        print(f"Running Vivado impl for {name}")
        _run([PYTHON, "-m", "scripts.vivado_flow", "impl"])
        _run([PYTHON, "-m", "scripts.vivado_report"])
        _copy_vivado_reports(name)
        print(f"Copied Vivado reports for {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "benchmark" / "sweeps"
PLAN_CSV = ROOT / "reports" / "benchmark" / "sweep_plan.csv"
PYTHON = sys.executable


@dataclass(frozen=True)
class SweepConfig:
    name: str
    p_k: int
    p_v: int
    block_size: int
    purpose: str


CONFIGS = (
    SweepConfig("parallel_pk8_pv4_b32", 8, 4, 32, "parallelism"),
    SweepConfig("parallel_pk16_pv8_b32", 16, 8, 32, "parallelism_default"),
    SweepConfig("parallel_pk32_pv16_b32", 32, 16, 32, "parallelism"),
    SweepConfig("block_b16_pk16_pv8", 16, 8, 16, "block_size"),
    SweepConfig("block_b16_pk32_pv16", 32, 16, 16, "block_size_max_parallelism"),
)


def _write_plan() -> None:
    PLAN_CSV.parent.mkdir(parents=True, exist_ok=True)
    with PLAN_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["config", "p_k", "p_v", "block_size", "purpose", "status"])
        writer.writeheader()
        for config in CONFIGS:
            has_csynth = (OUT_DIR / config.name / "util.md").exists()
            has_csim = (OUT_DIR / config.name / "results.md").exists()
            has_cosim = (OUT_DIR / config.name / "cosim" / "latency.csv").exists()
            has_impl = (OUT_DIR / config.name / "vivado" / "impl_timing.rpt").exists()
            if config.name == "parallel_pk16_pv8_b32" and has_csynth and has_impl and has_cosim:
                status = "default_cosim_post_impl_done"
            elif config.name == "parallel_pk16_pv8_b32" and has_csynth and has_impl:
                status = "default_post_impl_done"
            elif has_csynth and has_impl and has_cosim:
                status = "csynth_cosim_post_impl_done"
            elif has_csynth and has_impl:
                status = "csynth_post_impl_done"
            elif has_csynth:
                status = "csynth_done_impl_pending"
            elif has_csim:
                status = "csim_done_csynth_impl_pending"
            else:
                status = "pending_csim_csynth_impl"
            writer.writerow(
                {
                    "config": config.name,
                    "p_k": config.p_k,
                    "p_v": config.p_v,
                    "block_size": config.block_size,
                    "purpose": config.purpose,
                    "status": status,
                }
            )


def _copy_reports(config: SweepConfig, *, include_csim: bool, include_csynth: bool) -> None:
    dst = OUT_DIR / config.name
    dst.mkdir(parents=True, exist_ok=True)
    sources: list[Path] = []
    if include_csynth:
        sources.append(ROOT / "reports" / "csynth" / "util.md")
    if include_csim:
        sources.append(ROOT / "reports" / "csim" / "results.md")
    for source in sources:
        if source.exists():
            shutil.copyfile(source, dst / source.name)


def _run_step(config: SweepConfig, step: str) -> None:
    env = os.environ.copy()
    env["GDN_P_K"] = str(config.p_k)
    env["GDN_P_V"] = str(config.p_v)
    env["GDN_BLOCK_SIZE"] = str(config.block_size)
    result = subprocess.run([PYTHON, "-m", "scripts.hls_flow", step], cwd=ROOT, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"{step} failed for {config.name} with exit code {result.returncode}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan or run Phase 6 HLS sweep configurations.")
    parser.add_argument("--plan", action="store_true", help="Write reports/benchmark/sweep_plan.csv.")
    parser.add_argument("--run-csim", action="store_true", help="Run HLS C-sim for selected configs.")
    parser.add_argument("--run-csynth", action="store_true", help="Run HLS C-synthesis for selected configs.")
    parser.add_argument("--configs", nargs="*", default=[config.name for config in CONFIGS], help="Config names to run.")
    args = parser.parse_args(argv)

    selected = {config.name: config for config in CONFIGS}
    unknown = [name for name in args.configs if name not in selected]
    if unknown:
        raise ValueError(f"Unknown sweep config(s): {', '.join(unknown)}")

    if args.plan or (not args.run_csim and not args.run_csynth):
        _write_plan()
        print(f"Wrote {PLAN_CSV.relative_to(ROOT)}")

    for name in args.configs:
        config = selected[name]
        if args.run_csim:
            _run_step(config, "csim")
            subprocess.run([PYTHON, "-m", "scripts.csim_report"], cwd=ROOT, check=True)
        if args.run_csynth:
            _run_step(config, "csynth")
            subprocess.run([PYTHON, "-m", "scripts.hls_report"], cwd=ROOT, check=True)
        if args.run_csim or args.run_csynth:
            _copy_reports(config, include_csim=args.run_csim, include_csynth=args.run_csynth)
            print(f"Copied reports for {config.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

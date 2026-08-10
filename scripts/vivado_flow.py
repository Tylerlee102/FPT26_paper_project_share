from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .prepare_e2m0_ooc_rtl import generate as prepare_e2m0_ooc_rtl
from .prepare_bf16_ooc_rtl import generate as prepare_bf16_ooc_rtl
from .prepare_mxfp8_ooc_rtl import generate as prepare_mxfp8_ooc_rtl
from .prepare_rs2_ooc_rtl import generate as prepare_rs2_ooc_rtl
from .xilinx_tools import find_vivado_batch


TCL_BY_STEP = {
    "synth": Path("vivado/tcl/run_synth.tcl"),
    "impl": Path("vivado/tcl/run_impl.tcl"),
    "e2m0-synth": Path("vivado/tcl/run_e2m0_synth.tcl"),
    "e2m0-impl": Path("vivado/tcl/run_e2m0_impl.tcl"),
    "e2m0-postroute-sweep": Path("vivado/tcl/run_e2m0_postroute_sweep.tcl"),
    "rs2-synth": Path("vivado/tcl/run_rs2_synth.tcl"),
    "rs2-impl": Path("vivado/tcl/run_rs2_impl.tcl"),
    "rs2-fold-control-impl": Path(
        "vivado/tcl/run_rs2_fold_control_impl.tcl"
    ),
    "rs2-fold-write-impl": Path("vivado/tcl/run_rs2_fold_write_impl.tcl"),
    "rs2-layer-banks-impl": Path("vivado/tcl/run_rs2_layer_banks_impl.tcl"),
    "rs2-postroute-sweep": Path("vivado/tcl/run_rs2_postroute_sweep.tcl"),
    "rs2-postroute-fanout-opt": Path(
        "vivado/tcl/run_rs2_postroute_fanout_opt.tcl"
    ),
    "rs2-postroute-retime-opt": Path(
        "vivado/tcl/run_rs2_postroute_retime_opt.tcl"
    ),
    "rs2-postroute-slr-opt": Path(
        "vivado/tcl/run_rs2_postroute_slr_opt.tcl"
    ),
    "rs2-postroute-explore-opt": Path(
        "vivado/tcl/run_rs2_postroute_explore_opt.tcl"
    ),
    "rs2-postroute-aggressive-explore-opt": Path(
        "vivado/tcl/run_rs2_postroute_aggressive_explore_opt.tcl"
    ),
    "rs2-postroute-fanout-aggressive-opt": Path(
        "vivado/tcl/run_rs2_postroute_fanout_aggressive_opt.tcl"
    ),
    "rs2-timing-analysis": Path("vivado/tcl/analyze_rs2_timing.tcl"),
    "bf16-synth": Path("vivado/tcl/run_bf16_synth.tcl"),
    "bf16-impl": Path("vivado/tcl/run_bf16_impl.tcl"),
    "bf16-postroute-sweep": Path("vivado/tcl/run_bf16_postroute_sweep.tcl"),
    "mxfp8-synth": Path("vivado/tcl/run_mxfp8_synth.tcl"),
    "mxfp8-impl": Path("vivado/tcl/run_mxfp8_impl.tcl"),
    "mxfp8-postroute-sweep": Path("vivado/tcl/run_mxfp8_postroute_sweep.tcl"),
}


def _ps_quote(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Vivado synthesis or implementation.")
    parser.add_argument("step", choices=sorted(TCL_BY_STEP))
    args = parser.parse_args(argv)

    vivado = find_vivado_batch()
    if vivado is None:
        print(
            "Vivado was not found on PATH or under C:/AMDDesignTools or C:/Xilinx.",
            file=sys.stderr,
        )
        return 2

    root = Path(__file__).resolve().parents[1]
    if args.step.startswith("e2m0-"):
        prepare_e2m0_ooc_rtl()
    elif args.step == "rs2-fold-control-impl":
        prepare_rs2_ooc_rtl(
            source=(
                root
                / "gdn_rs2_fold_control_hls"
                / "u55c_250mhz"
                / "syn"
                / "verilog"
                / "gdn_rs2_top.v"
            ),
            output=(
                root
                / "build"
                / "vivado"
                / "rs2_fold_control_ooc_rtl"
                / "gdn_rs2_top.v"
            ),
        )
    elif args.step == "rs2-fold-write-impl":
        prepare_rs2_ooc_rtl(
            source=(
                root
                / "gdn_rs2_fold_write_hls"
                / "u55c_250mhz"
                / "syn"
                / "verilog"
                / "gdn_rs2_top.v"
            ),
            output=(
                root
                / "build"
                / "vivado"
                / "rs2_fold_write_ooc_rtl"
                / "gdn_rs2_top.v"
            ),
        )
    elif args.step == "rs2-layer-banks-impl":
        prepare_rs2_ooc_rtl(
            source=(
                root
                / "gdn_rs2_layer_banks_hls"
                / "u55c_250mhz"
                / "syn"
                / "verilog"
                / "gdn_rs2_top.v"
            ),
            output=(
                root
                / "build"
                / "vivado"
                / "rs2_layer_banks_ooc_rtl"
                / "gdn_rs2_top.v"
            ),
        )
    elif args.step.startswith("rs2-") and args.step not in {
        "rs2-postroute-sweep",
        "rs2-postroute-fanout-opt",
        "rs2-postroute-retime-opt",
        "rs2-postroute-slr-opt",
        "rs2-postroute-explore-opt",
        "rs2-postroute-aggressive-explore-opt",
        "rs2-postroute-fanout-aggressive-opt",
        "rs2-timing-analysis",
        "rs2-fold-control-impl",
        "rs2-fold-write-impl",
        "rs2-layer-banks-impl",
    }:
        prepare_rs2_ooc_rtl()
    elif args.step.startswith("bf16-") and args.step != "bf16-postroute-sweep":
        prepare_bf16_ooc_rtl()
    elif args.step.startswith("mxfp8-") and args.step != "mxfp8-postroute-sweep":
        prepare_mxfp8_ooc_rtl()
    tcl = TCL_BY_STEP[args.step]
    log = Path("reports/vivado") / f"vivado_{args.step}.log"
    journal = Path("reports/vivado") / f"vivado_{args.step}.jou"
    (root / "reports" / "vivado").mkdir(parents=True, exist_ok=True)

    if os.name == "nt" and vivado.suffix.lower() in {".bat", ""}:
        drive = "X:"
        drive_root = f"{drive}\\"
        mapped_tcl_rel = str(tcl).replace("/", "\\")
        mapped_log_rel = str(log).replace("/", "\\")
        mapped_journal_rel = str(journal).replace("/", "\\")
        mapped_tcl = f"{drive_root}{mapped_tcl_rel}"
        mapped_log = f"{drive_root}{mapped_log_rel}"
        mapped_journal = f"{drive_root}{mapped_journal_rel}"
        cmd_command = (
            f"cd /d {drive_root} && "
            f'call "{vivado}" -mode batch -source "{mapped_tcl}" '
            f'-log "{mapped_log}" -journal "{mapped_journal}"'
        )
        ps_command = (
            "$ErrorActionPreference = 'Stop'; "
            f"cmd.exe /d /c 'subst {drive} /d >nul 2>nul'; "
            f"subst {drive} {_ps_quote(root)}; "
            "try { "
            f"cmd.exe /d /c {_ps_quote(cmd_command)}; "
            "$rc = $LASTEXITCODE "
            "} finally { "
            "Set-Location C:\\; "
            f"subst {drive} /d "
            "} "
            "exit $rc"
        )
        return subprocess.call(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
            cwd=root,
        )

    return subprocess.call(
        [str(vivado), "-mode", "batch", "-source", str(root / tcl), "-log", str(root / log), "-journal", str(root / journal)],
        cwd=root,
    )


if __name__ == "__main__":
    raise SystemExit(main())

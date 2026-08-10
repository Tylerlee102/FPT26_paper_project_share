from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .hls_source_check import main as source_check_main
from .xilinx_tools import (
    find_gnuwin_bin,
    find_mingw_runtime_bin,
    find_settings64,
    find_vitis_hls,
    find_vitis_hls_batch,
)


TCL_BY_STEP = {
    "csim": Path("hls/tcl/run_csim.tcl"),
    "csynth": Path("hls/tcl/run_csynth.tcl"),
    "cosim": Path("hls/tcl/run_cosim.tcl"),
    "e2m0-arithmetic-csim": Path("hls/e2m0/tcl/run_arithmetic_csim.tcl"),
    "e2m0-csim": Path("hls/e2m0/tcl/run_csim.tcl"),
    "e2m0-control-cosim": Path("hls/e2m0/tcl/run_control_cosim.tcl"),
    "e2m0-csynth": Path("hls/e2m0/tcl/run_csynth.tcl"),
    "e2m0-trace-csim": Path("hls/e2m0/tcl/run_trace_csim.tcl"),
    "e2m0-trace-cosim": Path("hls/e2m0/tcl/run_trace_cosim.tcl"),
    "rs2-arithmetic-csim": Path("hls/rs2/tcl/run_arithmetic_csim.tcl"),
    "rs2-csim": Path("hls/rs2/tcl/run_csim.tcl"),
    "rs2-control-cosim": Path("hls/rs2/tcl/run_control_cosim.tcl"),
    "rs2-reset-trace-cosim": Path("hls/rs2/tcl/run_reset_trace_cosim.tcl"),
    "rs2-reset-trace-cosim-resume": Path(
        "hls/rs2/tcl/run_reset_trace_cosim_resume.tcl"
    ),
    "rs2-csynth": Path("hls/rs2/tcl/run_csynth.tcl"),
    "rs2-trace-csim": Path("hls/rs2/tcl/run_trace_csim.tcl"),
    "rs2-uram-latency2-csim": Path(
        "hls/rs2/tcl/run_uram_latency2_csim.tcl"
    ),
    "rs2-uram-latency2-csynth": Path(
        "hls/rs2/tcl/run_uram_latency2_csynth.tcl"
    ),
    "rs2-fold-control-csim": Path(
        "hls/rs2/tcl/run_fold_control_csim.tcl"
    ),
    "rs2-fold-control-csynth": Path(
        "hls/rs2/tcl/run_fold_control_csynth.tcl"
    ),
    "rs2-fold-write-csim": Path("hls/rs2/tcl/run_fold_write_csim.tcl"),
    "rs2-fold-write-csynth": Path("hls/rs2/tcl/run_fold_write_csynth.tcl"),
    "rs2-layer-banks-csim": Path("hls/rs2/tcl/run_layer_banks_csim.tcl"),
    "rs2-layer-banks-csynth": Path("hls/rs2/tcl/run_layer_banks_csynth.tcl"),
    "rs2-trace-cosim": Path("hls/rs2/tcl/run_trace_cosim.tcl"),
    "bf16-csim": Path("hls/bf16/tcl/run_csim.tcl"),
    "bf16-csynth": Path("hls/bf16/tcl/run_csynth.tcl"),
    "mxfp8-arithmetic-csim": Path("hls/mxfp8/tcl/run_arithmetic_csim.tcl"),
    "mxfp8-csim": Path("hls/mxfp8/tcl/run_csim.tcl"),
    "mxfp8-csynth": Path("hls/mxfp8/tcl/run_csynth.tcl"),
    "export": Path("hls/tcl/run_export.tcl"),
}


def _ps_quote(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _hls_loader_for_unwrapped_exe(vitis_hls: Path) -> Path | None:
    parts = [part.lower() for part in vitis_hls.parts]
    if vitis_hls.name.lower() != "vitis_hls.exe" or "unwrapped" not in parts:
        return None
    bin_dir = vitis_hls.parents[2]
    loader = bin_dir / "loader.bat"
    return loader if loader.exists() else None


def _archive_completed_step(step: str, root: Path) -> None:
    if step == "bf16-csim":
        source_root = root / "gdn_bf16_hls" / "u55c_250mhz"
        destination = root / "reports" / "csim" / "corrected" / "bf16_current"
        copies = {
            source_root / "csim" / "report" / "gdn_bf16_top_csim.log": (
                destination / "gdn_bf16_top_csim.log"
            ),
            source_root / "u55c_250mhz.log": destination / "u55c_250mhz.log",
        }
    elif step == "bf16-csynth":
        source_root = root / "gdn_bf16_hls" / "u55c_250mhz"
        report_root = source_root / "syn" / "report"
        destination = root / "reports" / "csynth" / "corrected" / "bf16_current"
        copies = {
            report_root / "gdn_bf16_top_csynth.xml": (
                destination / "report" / "gdn_bf16_top_csynth.xml"
            ),
            report_root / "gdn_bf16_top_csynth.rpt": (
                destination / "report" / "gdn_bf16_top_csynth.rpt"
            ),
            report_root / "gdn_bf16_top_impl_csynth.rpt": (
                destination / "report" / "gdn_bf16_top_impl_csynth.rpt"
            ),
            source_root / "u55c_250mhz.log": destination / "u55c_250mhz.log",
        }
    elif step in {"rs2-arithmetic-csim", "rs2-csim", "rs2-trace-csim"}:
        project = {
            "rs2-arithmetic-csim": "gdn_rs2_arithmetic_hls",
            "rs2-csim": "gdn_rs2_hls",
            "rs2-trace-csim": "gdn_rs2_trace_hls",
        }[step]
        stem = {
            "rs2-arithmetic-csim": "arithmetic",
            "rs2-csim": "smoke",
            "rs2-trace-csim": "trace64",
        }[step]
        source_root = root / project / "u55c_250mhz"
        destination = root / "reports" / "csim" / "corrected" / "rs2_current" / stem
        copies = {
            source_root / "csim" / "report" / "gdn_rs2_top_csim.log": (
                destination / "gdn_rs2_top_csim.log"
            ),
            source_root / "u55c_250mhz.log": destination / "u55c_250mhz.log",
        }
        if step == "rs2-arithmetic-csim":
            copies = {
                source_root / "csim" / "report" / "rs2_arithmetic_top_csim.log": (
                    destination / "rs2_arithmetic_top_csim.log"
                ),
                source_root / "u55c_250mhz.log": destination / "u55c_250mhz.log",
            }
        elif step == "rs2-trace-csim":
            trace_log = source_root / "csim" / "report" / "gdn_rs2_top_csim.log"
            marker = (
                "PASS: 64 encoded random-state tokens, exact outputs/counters, "
                "and final snapshot"
            )
            if marker not in trace_log.read_text(encoding="utf-8", errors="replace"):
                raise RuntimeError(
                    "refusing to archive rs2-trace-csim without the 64-token PASS marker"
                )
    elif step == "rs2-csynth":
        source_root = root / "gdn_rs2_hls" / "u55c_250mhz"
        report_root = source_root / "syn" / "report"
        destination = root / "reports" / "csynth" / "corrected" / "rs2_current"
        copies = {
            report_root / "gdn_rs2_top_csynth.xml": (
                destination / "report" / "gdn_rs2_top_csynth.xml"
            ),
            report_root / "gdn_rs2_top_csynth.rpt": (
                destination / "report" / "gdn_rs2_top_csynth.rpt"
            ),
            report_root / "gdn_rs2_top_impl_csynth.rpt": (
                destination / "report" / "gdn_rs2_top_impl_csynth.rpt"
            ),
            report_root / "p_anonymous_namespace_fold_log_csynth.rpt": (
                destination / "report" / "p_anonymous_namespace_fold_log_csynth.rpt"
            ),
            report_root / "select_e2m1_scale_power_csynth.rpt": (
                destination / "report" / "select_e2m1_scale_power_csynth.rpt"
            ),
            report_root / "select_e2m1_scale_power_Pipeline_select_e2m1_normalize_csynth.rpt": (
                destination
                / "report"
                / "select_e2m1_scale_power_Pipeline_select_e2m1_normalize_csynth.rpt"
            ),
            report_root / "select_e2m1_scale_power_Pipeline_select_e2m1_max_csynth.rpt": (
                destination
                / "report"
                / "select_e2m1_scale_power_Pipeline_select_e2m1_max_csynth.rpt"
            ),
            source_root / "u55c_250mhz.log": destination / "u55c_250mhz.log",
        }
    elif step in {
        "rs2-control-cosim",
        "rs2-reset-trace-cosim",
        "rs2-reset-trace-cosim-resume",
        "rs2-trace-cosim",
    }:
        project = {
            "rs2-control-cosim": "gdn_rs2_hls",
            "rs2-reset-trace-cosim": "gdn_rs2_reset_trace_cosim_hls",
            "rs2-reset-trace-cosim-resume": "gdn_rs2_reset_trace_cosim_hls",
            "rs2-trace-cosim": "gdn_rs2_trace_cosim_hls",
        }[step]
        stem = {
            "rs2-control-cosim": "control",
            "rs2-reset-trace-cosim": "trace64_reset",
            "rs2-reset-trace-cosim-resume": "trace64_reset",
            "rs2-trace-cosim": "trace64",
        }[step]
        source_root = root / project / "u55c_250mhz"
        destination = root / "reports" / "cosim" / "corrected" / "rs2_current" / stem
        solution_log = source_root / "u55c_250mhz.log"
        rtl_log = source_root / "sim" / "report" / "verilog" / "gdn_rs2_top.log"
        marker = {
            "rs2-control-cosim": (
                "PASS: corrected RS2 generated-RTL control smoke, two exact commands"
            ),
            "rs2-reset-trace-cosim": (
                "PASS: 64 encoded reset-state tokens, exact outputs/counters, "
                "and final snapshot"
            ),
            "rs2-reset-trace-cosim-resume": (
                "PASS: 64 encoded reset-state tokens, exact outputs/counters, "
                "and final snapshot"
            ),
            "rs2-trace-cosim": (
                "PASS: 64 encoded random-state tokens, exact outputs/counters, "
                "and final snapshot"
            ),
        }[step]
        solution_text = solution_log.read_text(encoding="utf-8", errors="replace")
        rtl_text = rtl_log.read_text(encoding="utf-8", errors="replace")
        if marker not in rtl_text or "C/RTL co-simulation finished: PASS" not in solution_text:
            raise RuntimeError(f"refusing to archive {step} without its RTL PASS markers")
        copies = {
            source_root / "sim" / "report" / "gdn_rs2_top_cosim.rpt": (
                destination / "gdn_rs2_top_cosim.rpt"
            ),
            rtl_log: (
                destination / "verilog" / "gdn_rs2_top.log"
            ),
            source_root / "sim" / "report" / "verilog" / "lat.rpt": (
                destination / "verilog" / "lat.rpt"
            ),
            source_root
            / "sim"
            / "report"
            / "verilog"
            / "result.transaction.rpt": (
                destination / "verilog" / "result.transaction.rpt"
            ),
            source_root / "sim" / "wrapc_pc" / "run_xsim.log": (
                destination / "verilog" / "run_xsim.log"
            ),
            solution_log: destination / "u55c_250mhz.log",
        }
    else:
        return

    for source, target in copies.items():
        if not source.is_file():
            raise FileNotFoundError(f"completed {step} artifact is absent: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(f"Archived {len(copies)} {step} artifacts under {destination.relative_to(root)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Vitis HLS flow step when the tool is available.")
    parser.add_argument("step", choices=sorted(TCL_BY_STEP))
    args = parser.parse_args(argv)

    check_rc = source_check_main()
    if check_rc != 0:
        return check_rc

    vitis_hls = find_vitis_hls_batch() or find_vitis_hls()
    if vitis_hls is None:
        print(
            "Vitis HLS was not found on PATH. Source-contract checks passed, "
            f"but {args.step} was not run.",
            file=sys.stderr,
        )
        return 2

    root = Path(__file__).resolve().parents[1]
    tcl = root / TCL_BY_STEP[args.step]

    if os.name == "nt":
        settings = find_settings64()
        gnuwin = find_gnuwin_bin()
        mingw_runtime = find_mingw_runtime_bin()
        hls_loader = _hls_loader_for_unwrapped_exe(vitis_hls)
        if hls_loader is not None or (settings is not None and vitis_hls.suffix.lower() in {".bat", ""}):
            drive = "X:"
            drive_root = f"{drive}\\"
            mapped_rel_tcl = TCL_BY_STEP[args.step].as_posix().replace("/", "\\")
            mapped_tcl = f"{drive_root}{mapped_rel_tcl}"
            setup_commands = [f"cd /d {drive_root}"]
            path_prefixes = [
                str(path) for path in (gnuwin, mingw_runtime) if path is not None
            ]
            if settings is not None:
                setup_commands.append(f'call "{settings}"')
            if path_prefixes:
                setup_commands.append(
                    f'set "PATH={";".join(path_prefixes)};%PATH%"'
                )
            if mingw_runtime is not None:
                setup_commands.append(
                    f'set "GDN_COSIM_MINGW={mingw_runtime}"'
                )
            if hls_loader is not None:
                setup_commands.append(f'call "{hls_loader}" -exec vitis_hls -f "{mapped_tcl}"')
            else:
                setup_commands.append(f'call "{vitis_hls}" -f "{mapped_tcl}"')
            cmd_command = " && ".join(setup_commands)
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
            return_code = subprocess.call(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
                cwd=root,
            )
            if return_code == 0:
                _archive_completed_step(args.step, root)
            return return_code

    return_code = subprocess.call([str(vitis_hls), "-f", str(tcl)], cwd=root)
    if return_code == 0:
        _archive_completed_step(args.step, root)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())

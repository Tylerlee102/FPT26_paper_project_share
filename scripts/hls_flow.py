from __future__ import annotations

import argparse
import os
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
            return subprocess.call(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
                cwd=root,
            )

    return subprocess.call([str(vitis_hls), "-f", str(tcl)], cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())

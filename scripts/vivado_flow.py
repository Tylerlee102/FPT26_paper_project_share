from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .xilinx_tools import find_vivado_batch


TCL_BY_STEP = {
    "synth": Path("vivado/tcl/run_synth.tcl"),
    "impl": Path("vivado/tcl/run_impl.tcl"),
}


def _ps_quote(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Vivado synthesis or implementation.")
    parser.add_argument("step", choices=sorted(TCL_BY_STEP))
    args = parser.parse_args(argv)

    vivado = find_vivado_batch()
    if vivado is None:
        print("Vivado was not found on PATH or under C:/Xilinx.", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
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

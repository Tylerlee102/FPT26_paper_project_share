"""Archive and summarize a bounded official-XSim RS2 diagnostic run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIM_ROOT = ROOT / "gdn_rs2_reset_trace_cosim_hls" / "u55c_250mhz" / "sim"
DEFAULT_C_LOG = SIM_ROOT / "wrapc" / "tmp.log"
DEFAULT_XELAB_LOG = SIM_ROOT / "verilog" / "xelab.log"
DEFAULT_XSIM_LOG = SIM_ROOT / "verilog" / "xsim.log"
DEFAULT_OUTPUT = (
    ROOT / "reports" / "cosim" / "corrected" / "rs2_current" / "xsim_diagnostic"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _progress(text: str) -> tuple[int, int]:
    rows = re.findall(r"RTL Simulation\s*:\s*(\d+)\s*/\s*(\d+)", text)
    if not rows:
        return 0, 0
    completed, total = rows[-1]
    return int(completed), int(total)


def build(
    c_log: Path,
    xelab_log: Path,
    xsim_log: Path,
    output_dir: Path,
) -> dict[str, object]:
    for path in (c_log, xelab_log, xsim_log):
        if not path.is_file():
            raise FileNotFoundError(path)

    c_text = c_log.read_text(encoding="utf-8", errors="replace")
    xelab_text = xelab_log.read_text(encoding="utf-8", errors="replace")
    xsim_text = xsim_log.read_text(encoding="utf-8", errors="replace")
    c_pass = "PASS: 8 encoded random-state tokens" in c_text
    elaboration_pass = "Built simulation snapshot gdn_rs2_top" in xelab_text
    launched = "Starting XSIM" in xsim_text or "# xsim v2025.2" in xsim_text
    completed, total = _progress(xsim_text)

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    archived: dict[str, dict[str, object]] = {}
    for label, source in (
        ("c_transaction_generator.log", c_log),
        ("xelab.log", xelab_log),
        ("xsim.log", xsim_log),
    ):
        target = raw_dir / label
        shutil.copy2(source, target)
        archived[_relative(target)] = {
            "bytes": target.stat().st_size,
            "sha256": _sha256(target),
            "source": _relative(source),
            "source_sha256": _sha256(source),
        }

    milestones = {
        "eight_token_c_transaction_generation": "PASS" if c_pass else "FAIL",
        "xelab": "PASS" if elaboration_pass else "FAIL",
        "xsim_launch": "PASS" if launched else "FAIL",
        "completed_transactions": completed,
        "total_transactions": total,
    }
    setup_pass = c_pass and elaboration_pass and launched and total == 10
    payload: dict[str, object] = {
        "schema": 1,
        "status": "INCOMPLETE" if setup_pass and completed < total else "FAIL",
        "scope": "bounded official Vitis HLS/XSIM diagnostic; not RTL parity evidence",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trace_tokens": 8,
        "required_64_token_rtl_parity": "NOT_RUN",
        "milestones": milestones,
        "termination": {
            "kind": "BOUNDED_DIAGNOSTIC_STOP",
            "finding": (
                "The run was intentionally stopped after XSIM launched and the "
                "last preserved progress sample remained at 0/10 transactions."
            ),
        },
        "claim_boundary": [
            "C transaction generation and RTL elaboration completed.",
            "No official XSIM transaction completed in the preserved run.",
            "This artifact does not establish one-token or 64-token RTL parity.",
        ],
        "raw_artifacts": archived,
    }
    output = output_dir / "rs2_xsim_diagnostic.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c-log", type=Path, default=DEFAULT_C_LOG)
    parser.add_argument("--xelab-log", type=Path, default=DEFAULT_XELAB_LOG)
    parser.add_argument("--xsim-log", type=Path, default=DEFAULT_XSIM_LOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = build(
        _resolve(args.c_log),
        _resolve(args.xelab_log),
        _resolve(args.xsim_log),
        _resolve(args.output),
    )
    print(json.dumps({"status": result["status"], "milestones": result["milestones"]}))
    return 0 if result["status"] == "INCOMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())

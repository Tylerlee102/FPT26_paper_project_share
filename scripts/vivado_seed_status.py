from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "vivado" / "seed_sweep_status.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _summary_value(text: str, label: str) -> str:
    match = re.search(rf"- {re.escape(label)}:\s*(.+)", text)
    return match.group(1).strip() if match else "unknown"


def write_report(path: Path) -> None:
    impl_tcl = ROOT / "vivado" / "tcl" / "run_impl.tcl"
    summary = ROOT / "reports" / "vivado" / "summary.md"
    impl_text = _read(impl_tcl)
    summary_text = _read(summary)
    has_seed = bool(re.search(r"\b(seed|randomSeed|random_seed)\b", impl_text, flags=re.IGNORECASE))
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Vivado Placement Seed Sweep Status",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Implementation Tcl: `{impl_tcl.relative_to(ROOT).as_posix()}`",
        "",
        "Status: not_run",
        "",
        "Reason: the current non-project Vivado implementation flow invokes `place_design` directly and does not expose a verified placement-seed parameter. Re-running the same Tcl multiple times would not provide a controlled seed sweep, so no extra implementation runs were launched for this item.",
        "",
        "| Current default implementation metric | Value |",
        "|---|---:|",
        f"| Implementation WNS | {_summary_value(summary_text, 'Implementation WNS')} |",
        f"| LUT utilization | {_summary_value(summary_text, 'LUT utilization')} |",
        f"| BRAM utilization | {_summary_value(summary_text, 'BRAM utilization')} |",
        f"| DSP utilization | {_summary_value(summary_text, 'DSP utilization')} |",
        f"| Total on-chip power | {_summary_value(summary_text, 'Total on-chip power')} |",
        f"| Seed parameter found in Tcl | {'yes' if has_seed else 'no'} |",
        "",
        "Recommended follow-up: convert the implementation flow to a project-run flow or add a verified Vivado seed parameter before reporting min/mean/max WNS across seeds.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Document Vivado placement seed-sweep feasibility.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    write_report(report_path)
    print(report_path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

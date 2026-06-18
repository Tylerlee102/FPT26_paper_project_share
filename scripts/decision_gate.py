from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .xilinx_tools import find_vitis_hls

@dataclass(frozen=True)
class GateEvidence:
    vitis_hls_available: bool
    vitis_hls_path: Path | None
    csim_report: Path | None
    csynth_report: Path | None
    util_report: Path | None
    source_handoff: Path | None


def _first_existing(root: Path, candidates: list[str]) -> Path | None:
    for candidate in candidates:
        path = root / candidate
        if path.exists():
            return path
    return None


def _read(path: Path | None) -> str:
    return "" if path is None else path.read_text(encoding="utf-8", errors="replace")


def _extract_float(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return None if match is None else float(match.group(1))


def _yes_no(condition: bool) -> str:
    return "yes" if condition else "no"


def _remaining_work_pass(value: str) -> bool:
    numbers = re.findall(r"\d+(?:\.\d+)?", value)
    return bool(numbers) and max(float(number) for number in numbers) <= 3.0


def collect_evidence(root: Path) -> GateEvidence:
    vitis_hls = find_vitis_hls()
    return GateEvidence(
        vitis_hls_available=vitis_hls is not None,
        vitis_hls_path=vitis_hls,
        csim_report=_first_existing(
            root,
            [
                "reports/csim/results.md",
                "reports/csim/csim.log",
                "reports/csim/tb_gdn_top.log",
            ],
        ),
        csynth_report=_first_existing(
            root,
            [
                "reports/csynth/gdn_top_csynth.rpt",
                "reports/csynth/csynth.rpt",
                "gdn_mxfp4_hls/u55c_250mhz/syn/report/gdn_top_csynth.rpt",
            ],
        ),
        util_report=_first_existing(root, ["reports/csynth/util.md"]),
        source_handoff=_first_existing(root, ["reports/csynth/handoff.md"]),
    )


def build_decision_gate_report(root: Path, *, remaining_work_days: str = "0") -> str:
    evidence = collect_evidence(root)
    timestamp = datetime.now(UTC).isoformat()

    csim_status = "MISSING"
    csim_detail = "No HLS C-sim result file found; bit-exact 32/32 vector status is unknown."
    if evidence.csim_report is not None:
        csim_status = "PRESENT"
        csim_detail = f"Found `{evidence.csim_report.relative_to(root).as_posix()}`; manual review required."

    csynth_status = "MISSING"
    csynth_detail = "No HLS csynth report found; Fmax and II are unknown."
    if evidence.csynth_report is not None:
        csynth_status = "PRESENT"
        csynth_detail = f"Found `{evidence.csynth_report.relative_to(root).as_posix()}`; parser integration required."

    util_status = "MISSING"
    util_detail = "No `reports/csynth/util.md`; LUT and BRAM utilization are unknown."
    if evidence.util_report is not None:
        util_status = "PRESENT"
        util_detail = f"Found `{evidence.util_report.relative_to(root).as_posix()}`; manual review required."

    tool_status = "AVAILABLE" if evidence.vitis_hls_available else "MISSING"
    tool_path = evidence.vitis_hls_path.as_posix() if evidence.vitis_hls_path is not None else "not found"
    csim_text = _read(evidence.csim_report)
    util_text = _read(evidence.util_report)
    vector_match = re.search(r"vectors=(\d+)/(\d+)", csim_text)
    csim_stale = "Status: stale" in csim_text
    if vector_match is not None:
        passed_vectors = int(vector_match.group(1))
        total_vectors = int(vector_match.group(2))
        csim_current = f"{passed_vectors}/{total_vectors}" + (" (stale)" if csim_stale else "")
        csim_pass = (
            passed_vectors == total_vectors
            and total_vectors >= 32
            and "CSim done with 0 errors" in csim_text
            and not csim_stale
        )
    elif "CSim done with 0 errors" in csim_text:
        csim_current = "top smoke PASS; vector parity not found"
        csim_pass = False
    else:
        csim_current = "unknown"
        csim_pass = False
    fmax = _extract_float(r"Estimated Fmax:\s*([0-9.]+)\s*MHz", util_text)
    if fmax is None:
        fmax = _extract_float(r"Estimated clock:\s*[0-9.]+\s*ns\s*\(([0-9.]+)\s*MHz\)", util_text)
    lut_pct = _extract_float(r"LUT utilization:\s*([0-9.]+)%", util_text)
    bram_pct = _extract_float(r"BRAM utilization:\s*([0-9.]+)%", util_text)
    ii_pass = "Inner-loop II: 1" in util_text or "II=1" in util_text
    fmax_current = "unknown" if fmax is None else f"{fmax:.2f} MHz"
    lut_current = "unknown" if lut_pct is None else f"{lut_pct:.2f}%"
    bram_current = "unknown" if bram_pct is None else f"{bram_pct:.2f}%"
    remaining_pass = _remaining_work_pass(remaining_work_days)
    fmax_pass = fmax is not None and fmax >= 200.0
    lut_pass = lut_pct is not None and lut_pct < 80.0
    bram_pass = bram_pct is not None and bram_pct < 80.0
    gate_ready = csim_pass and fmax_pass and ii_pass and lut_pass and bram_pass and remaining_pass
    gate_status = "READY_FOR_HUMAN_GO" if gate_ready else "BLOCKED"

    lines = [
        "# Phase 4 MXFP4 Decision Gate",
        "",
        f"Generated: {timestamp}",
        "",
        f"Overall status: **{gate_status}**",
        "",
        "Human decision required before proceeding beyond Phase 4. This report does not flip "
        "`USE_MXFP4`; proceed only after explicit human approval.",
        "",
        "## Required Evidence",
        "",
        "| Item | Status | Detail |",
        "|---|---|---|",
        f"| Vitis HLS available | {tool_status} | `{tool_path}` |",
        f"| Latest `make hls-csim` | {csim_status} | {csim_detail} |",
        f"| Latest `make hls-csynth` | {csynth_status} | {csynth_detail} |",
        f"| `reports/csynth/util.md` | {util_status} | {util_detail} |",
        f"| Remaining work estimate | PRESENT | {remaining_work_days} person-days to Phase 5 readiness, assuming Vitis HLS is available. |",
        "",
        "## Gate Criteria",
        "",
        "| Criterion | Required | Current | Pass? |",
        "|---|---:|---:|---|",
        f"| Csim bit-exact vectors | 32/32 | {csim_current} | {_yes_no(csim_pass)} |",
        f"| Csynth Fmax | >= 200 MHz | {fmax_current} | {_yes_no(fmax_pass)} |",
        f"| Inner-loop II | 1 | {'1' if ii_pass else 'unknown'} | {_yes_no(ii_pass)} |",
        f"| LUT utilization | < 80% | {lut_current} | {_yes_no(lut_pass)} |",
        f"| BRAM utilization | < 80% | {bram_current} | {_yes_no(bram_pass)} |",
        f"| Remaining work | <= 3 person-days | {remaining_work_days} person-days | {_yes_no(remaining_pass)} |",
        "",
        "## Recommendation",
        "",
        (
            "All machine-checkable Phase 4 criteria in this report pass. The human team may "
            "explicitly approve MXFP4 and proceed to Phase 5."
            if gate_ready
            else "Do not proceed to Phase 5 yet. Fix the failing Phase 4 criteria above, or make "
            "an explicit human fallback decision to INT4."
        ),
        "",
    ]

    if evidence.source_handoff is not None:
        lines.extend(
            [
                "## Source Handoff",
                "",
                f"See `{evidence.source_handoff.relative_to(root).as_posix()}` for the Phase 3 source handoff.",
                "",
            ]
        )

    return "\n".join(lines)


def write_decision_gate_report(
    root: Path,
    output: Path,
    *,
    remaining_work_days: str = "4-6",
) -> Path:
    text = build_decision_gate_report(root, remaining_work_days=remaining_work_days)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Phase 4 MXFP4 decision gate report.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="reports/decision_gate.md")
    parser.add_argument("--remaining-work-days", default="0")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output = root / args.output
    write_decision_gate_report(root, output, remaining_work_days=args.remaining_work_days)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

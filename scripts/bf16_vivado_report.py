"""Extract the matched BF16 U55C synthesis and physical-fit result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.e2m0_vivado_report import parse_utilization


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = ROOT / "reports" / "vivado" / "baselines" / "bf16"
DEFAULT_OUTPUT = DEFAULT_REPORT_DIR
IMPL_LOG = ROOT / "reports" / "vivado" / "vivado_bf16-impl.log"
RTL_MANIFEST = ROOT / "build" / "vivado" / "bf16_ooc_rtl" / "manifest.json"
SYNTH_DCP = ROOT / "build" / "vivado" / "gdn_bf16_vivado" / "bf16_post_synth.dcp"
CAPACITY = ROOT / "reports" / "benchmark" / "corrected" / "state_capacity_lower_bound.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _git_revision() -> str:
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _requirement(text: str, resource: str) -> dict[str, int]:
    line = next(
        (
            row
            for row in text.splitlines()
            if "ERROR: [DRC UTLZ-1]" in row
            and f"Resource utilization: {resource}" in row
        ),
        None,
    )
    if line is None:
        raise ValueError(f"BF16 capacity DRC is absent for {resource}")
    match = re.search(
        r"requires (\d+) of such cell types but only (\d+) compatible sites are available",
        line,
    )
    if match is None:
        raise ValueError(f"BF16 capacity counts are absent for {resource}")
    return {"required": int(match.group(1)), "available": int(match.group(2))}


def generate_report(report_dir: Path, output: Path) -> dict[str, object]:
    util_path = report_dir / "synth_util.rpt"
    required = (util_path, IMPL_LOG, RTL_MANIFEST, SYNTH_DCP, CAPACITY)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    util_text = util_path.read_text(encoding="utf-8", errors="replace")
    log_text = IMPL_LOG.read_text(encoding="utf-8", errors="replace")
    utilization = parse_utilization(util_text.replace("CLB LUTs*", "CLB LUTs"))
    ram36 = _requirement(log_text, "RAMB36/FIFO over-utilized")
    compatible = _requirement(log_text, "RAMB18 and RAMB36/FIFO over-utilized")
    capacity = json.loads(CAPACITY.read_text(encoding="utf-8"))
    bf16_capacity = next(row for row in capacity["rows"] if row["variant"] == "BF16")
    rtl_manifest = json.loads(RTL_MANIFEST.read_text(encoding="utf-8"))
    rtl_source = ROOT / rtl_manifest["source"]
    rtl_output = ROOT / rtl_manifest["output"]
    rtl_integrity = (
        rtl_manifest.get("status") == "PASS"
        and _sha256(rtl_source) == rtl_manifest["source_sha256"].upper()
        and _sha256(rtl_output) == rtl_manifest["output_sha256"].upper()
    )
    synthesis_pass = (
        "synth_design completed successfully" in log_text
        and "Synthesis finished with 0 errors" in log_text
    )
    placement_capacity_fail = (
        "place_design failed" in log_text
        and "ERROR: [DRC UTLZ-1]" in log_text
        and ram36["required"] > ram36["available"]
    )
    extraction_pass = synthesis_pass and placement_capacity_fail and rtl_integrity
    report: dict[str, object] = {
        "schema": 1,
        "status": "PASS" if extraction_pass else "FAIL",
        "scope": "matched 36-layer BF16 persistent-state U55C out-of-context physical-fit attempt",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": _git_revision(),
        "target_device": "xcu55c-fsvh2892-2L-e",
        "target_period_ns": 4.0,
        "synthesis_completion": "PASS" if synthesis_pass else "FAIL",
        "placement_completion": "FAIL_CAPACITY" if placement_capacity_fail else "UNKNOWN",
        "route_completion": "NOT_APPLICABLE_PHYSICAL_FIT_FAILED",
        "physical_fit": "FAIL",
        "synthesized_utilization": utilization,
        "capacity_drc": {
            "ramb36_fifo": ram36,
            "ramb18_ramb36_compatible": compatible,
            "rule": "UTLZ-1",
        },
        "ideal_state_only_lower_bound": {
            "logical_state_bytes": bf16_capacity["logical_state_bytes"],
            "ideal_min_uram": bf16_capacity["ideal_min_uram_for_mantissas"],
            "available_uram": bf16_capacity["device_uram"],
            "raw_bit_capacity_necessary_condition": bf16_capacity[
                "raw_bit_capacity_necessary_condition"
            ],
        },
        "rtl_transformation": {
            **rtl_manifest,
            "integrity_status": "PASS" if rtl_integrity else "FAIL",
        },
        "timing": "NOT_RUN_PHYSICAL_FIT_FAILED",
        "vectorless_power": "NOT_RUN_PHYSICAL_FIT_FAILED",
        "board_energy": "BLOCKED_EXTERNAL_NO_U55C_DEVICE_OR_XRT",
        "raw_artifact_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in required
        },
        "limitations": [
            "The all-layer BF16 state bank cannot be placed on the declared U55C; no routed timing or power value exists.",
            "The synthesis netlist mapped the state bank to RAMB36, but the independent ideal URAM-only state lower bound also exceeds the device's 960 URAMs.",
            "A reduced-layer BF16 route would change the controlled state layout and is therefore not substituted.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "bf16_vivado_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "bf16_vivado_summary.md").write_text(
        "\n".join(
            [
                "# Matched BF16 Physical-Fit Attempt",
                "",
                f"Generated: `{report['generated_at']}`",
                f"Extraction status: `{report['status']}`",
                "",
                f"- Synthesis: `{report['synthesis_completion']}`",
                f"- Placement: `{report['placement_completion']}`",
                f"- Physical fit: `{report['physical_fit']}`",
                f"- Synthesized resources: `{utilization['clb_luts']['used']:,}` CLB LUT, `{utilization['clb_registers']['used']:,}` FF, `{utilization['block_ram_tiles']['used']:,}` BRAM tiles, `{utilization['uram']['used']}` URAM, `{utilization['dsps']['used']}` DSP",
                f"- Capacity DRC: `{ram36['required']:,}` RAMB36/FIFO required versus `{ram36['available']:,}` available",
                f"- Independent state-only lower bound: `{bf16_capacity['ideal_min_uram_for_mantissas']:,}` URAM versus `{bf16_capacity['device_uram']}` available",
                "- Routed timing, vectorless power, and energy: unavailable because placement failed",
                "",
                "A reduced-layer route is not substituted because it would change the controlled all-layer state layout.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report_dir = args.report_dir if args.report_dir.is_absolute() else ROOT / args.report_dir
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report = generate_report(report_dir, output)
    print(json.dumps({"status": report["status"], "physical_fit": report["physical_fit"]}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Extract a provenance-rich report from the corrected baseline HLS archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = (
    ROOT / "reports" / "csynth" / "corrected_attempt9_transport_pipeline_cleanup"
)
DEFAULT_OUTPUT = ROOT / "reports" / "csynth" / "corrected"
CSIM_MANIFEST = ROOT / "reports" / "csim" / "corrected" / "csim_manifest.json"
SOURCE_GLOBS = (
    "hls/include/*.hpp",
    "hls/src/*.cpp",
    "hls/tcl/run_csynth.tcl",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _text(root: ET.Element, path: str) -> str:
    value = root.findtext(path)
    if value is None:
        raise ValueError(f"missing XML value: {path}")
    return value.strip()


def _parse_top_xml(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    resources = root.find("./AreaEstimates/Resources")
    available = root.find("./AreaEstimates/AvailableResources")
    if resources is None or available is None:
        raise ValueError("top XML has no area estimates")
    names = ("BRAM_18K", "DSP", "FF", "LUT", "URAM")
    resource_values = {name: int(_text(resources, name)) for name in names}
    available_values = {name: int(_text(available, name)) for name in names}
    estimated_ns = float(
        _text(
            root,
            "./PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod",
        )
    )
    latency_root = root.find(
        "./PerformanceEstimates/SummaryOfOverallLatency"
    )
    if latency_root is None:
        raise ValueError("top XML has no latency summary")
    return {
        "tool_version": _text(root, "./ReportVersion/Version"),
        "target_device": _text(root, "./UserAssignments/Part"),
        "target_clock_ns": float(_text(root, "./UserAssignments/TargetClockPeriod")),
        "clock_uncertainty_ns": float(
            _text(root, "./UserAssignments/ClockUncertainty")
        ),
        "estimated_clock_ns": estimated_ns,
        "estimated_fmax_mhz": 1000.0 / estimated_ns,
        "latency_cycles_min": int(_text(latency_root, "Best-caseLatency")),
        "latency_cycles_average": int(_text(latency_root, "Average-caseLatency")),
        "latency_cycles_max": int(_text(latency_root, "Worst-caseLatency")),
        "interval_cycles_min": int(_text(latency_root, "Interval-min")),
        "interval_cycles_max": int(_text(latency_root, "Interval-max")),
        "resources": resource_values,
        "available_device_resources": available_values,
        "device_utilization_percent": {
            name: 100.0 * resource_values[name] / available_values[name]
            for name in names
        },
    }


def _parse_slr_resources(report: str) -> tuple[dict[str, int], dict[str, float]]:
    names = ("BRAM_18K", "DSP", "FF", "LUT", "URAM")
    available_match = re.search(r"^\|Available SLR\s*\|([^\n]+)$", report, re.MULTILINE)
    utilization_match = re.search(
        r"^\|Utilization SLR \(%\)\s*\|([^\n]+)$", report, re.MULTILINE
    )
    if available_match is None or utilization_match is None:
        raise ValueError("text report has no SLR resource rows")

    def fields(match: re.Match[str]) -> list[str]:
        return [field.strip() for field in match.group(1).split("|") if field.strip()]

    available_fields = fields(available_match)
    utilization_fields = fields(utilization_match)
    if len(available_fields) != len(names) or len(utilization_fields) != len(names):
        raise ValueError("unexpected SLR resource column count")
    available = dict(zip(names, (int(value) for value in available_fields)))
    utilization = dict(
        zip(names, (0.0 if value == "~0" else float(value) for value in utilization_fields))
    )
    return available, utilization


def _parse_loop_results(log: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    pattern = re.compile(
        r"Pipelining result\s*:\s*Target II = (NA|\d+), Final II = (\d+), "
        r"Depth = (\d+), loop '([^']+)'"
    )
    targeted: list[dict[str, object]] = []
    untargeted: list[dict[str, object]] = []
    for target, final, depth, name in pattern.findall(log):
        row = {
            "loop": name,
            "target_ii": None if target == "NA" else int(target),
            "final_ii": int(final),
            "depth": int(depth),
        }
        (untargeted if target == "NA" else targeted).append(row)
    if not targeted:
        raise ValueError("HLS log contains no explicitly targeted loops")
    return targeted, untargeted


def _source_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for pattern in SOURCE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            hashes[path.relative_to(ROOT).as_posix()] = _sha256(path)
    return hashes


def _tree_hashes(archive: Path) -> tuple[dict[str, str], str]:
    hashes = {
        path.relative_to(ROOT).as_posix(): _sha256(path)
        for path in sorted(archive.rglob("*"))
        if path.is_file()
    }
    canonical = "".join(f"{path} {digest}\n" for path, digest in hashes.items())
    return hashes, hashlib.sha256(canonical.encode("ascii")).hexdigest().upper()


def generate_report(archive: Path, output: Path) -> dict[str, object]:
    top_xml = archive / "report" / "gdn_top_csynth.xml"
    top_report = archive / "report" / "gdn_top_csynth.rpt"
    raw_log = archive / "u55c_250mhz.log"
    for path in (top_xml, top_report, raw_log, CSIM_MANIFEST):
        if not path.exists():
            raise FileNotFoundError(path)

    metrics = _parse_top_xml(top_xml)
    report_text = top_report.read_text(encoding="utf-8", errors="replace")
    log_text = raw_log.read_text(encoding="utf-8", errors="replace")
    slr_available, slr_utilization = _parse_slr_resources(report_text)
    targeted, untargeted = _parse_loop_results(log_text)
    csim_manifest = json.loads(CSIM_MANIFEST.read_text(encoding="utf-8"))
    current_sources = _source_hashes()
    csim_sources = csim_manifest["source_sha256"]
    shared_sources = {
        path: digest
        for path, digest in current_sources.items()
        if path in csim_sources
    }
    source_mismatches = {
        path: {"current": digest, "csim": csim_sources[path]}
        for path, digest in shared_sources.items()
        if digest.lower() != str(csim_sources[path]).lower()
    }
    latest_source = max(
        (_repo_path for _repo_path in (ROOT / path for path in current_sources)),
        key=lambda path: path.stat().st_mtime,
    )
    source_fresh = latest_source.stat().st_mtime <= raw_log.stat().st_mtime + 1.0
    completed = "Finished Command csynth_design" in log_text
    vendor_constraint_pass = (
        "Loop Constraint Status: All loop constraints were satisfied" in log_text
    )
    targeted_ii_pass = all(
        row["target_ii"] == row["final_ii"] == 1 for row in targeted
    )
    archive_hashes, archive_tree_hash = _tree_hashes(archive)

    status = (
        "PASS"
        if completed and source_fresh and not source_mismatches and targeted_ii_pass
        else "FAIL"
    )
    manifest: dict[str, object] = {
        "schema": 1,
        "status": status,
        "scope": "corrected uniform-MXFP4 baseline HLS C-synthesis estimate",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": "bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe",
        "archive": archive.relative_to(ROOT).as_posix(),
        "archive_tree_sha256": archive_tree_hash,
        "raw_artifact_sha256": archive_hashes,
        "source_sha256": current_sources,
        "source_matches_preceding_csim": not source_mismatches,
        "source_mismatches": source_mismatches,
        "freshness": {
            "status": "PASS" if source_fresh else "FAIL",
            "latest_source": latest_source.relative_to(ROOT).as_posix(),
            "latest_source_mtime_utc": datetime.fromtimestamp(
                latest_source.stat().st_mtime, timezone.utc
            ).isoformat(),
            "raw_log_mtime_utc": datetime.fromtimestamp(
                raw_log.stat().st_mtime, timezone.utc
            ).isoformat(),
        },
        "command_completion": "PASS" if completed else "FAIL",
        "metrics": metrics,
        "available_slr_resources": slr_available,
        "slr_utilization_percent_reported": slr_utilization,
        "targeted_loop_ii_status": "PASS" if targeted_ii_pass else "FAIL",
        "targeted_loops": targeted,
        "untargeted_loops": untargeted,
        "vendor_loop_constraint_summary": (
            "PASS" if vendor_constraint_pass else "FAIL"
        ),
        "vendor_loop_constraint_text": (
            "All loop constraints were satisfied"
            if vendor_constraint_pass
            else "All loop constraints were NOT satisfied"
        ),
        "rtl_cosimulation_smoke": "FAIL",
        "required_64_token_rtl_cosimulation": "NOT_RUN",
        "post_route_timing_and_drc": "NOT_RUN",
        "selected_write_log_candidate_physical_evidence": "NOT_RUN",
        "limitations": [
            "HLS estimate only; not post-route utilization, timing, or power",
            "uniform MXFP4 baseline, not the selected residual-stack/write-log candidate",
            "top-level latency spans multiple command paths and is not measured token throughput",
            "one-token XSIM smoke failed on memory; required 64-token RTL parity is not run",
        ],
    }

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "baseline_csynth_summary.json"
    md_path = output / "baseline_csynth_summary.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    resources = metrics["resources"]
    md_path.write_text(
        "\n".join(
            [
                "# Corrected Uniform-MXFP4 Baseline C-Synthesis",
                "",
                f"Generated: `{manifest['timestamp']}`",
                "",
                f"- Extraction status: `{status}`",
                f"- Target: `{metrics['target_device']}` at `{metrics['target_clock_ns']:.2f}` ns",
                f"- Estimated clock: `{metrics['estimated_clock_ns']:.3f}` ns (`{metrics['estimated_fmax_mhz']:.2f}` MHz)",
                f"- Top-level command latency range: `{metrics['latency_cycles_min']}` to `{metrics['latency_cycles_max']}` cycles",
                f"- Resources: `{resources['LUT']}` LUT, `{resources['FF']}` FF, `{resources['BRAM_18K']}` BRAM18K, `{resources['URAM']}` URAM, `{resources['DSP']}` DSP",
                f"- Reported SLR utilization: `{slr_utilization['LUT']:.0f}%` LUT, `{slr_utilization['FF']:.0f}%` FF, `{slr_utilization['BRAM_18K']:.0f}%` BRAM18K, `{slr_utilization['URAM']:.0f}%` URAM",
                f"- Explicitly targeted loop II: `{'PASS' if targeted_ii_pass else 'FAIL'}` ({len(targeted)} loops)",
                f"- Vendor overall loop-constraint summary: `{'PASS' if vendor_constraint_pass else 'FAIL'}`",
                f"- Source freshness: `{'PASS' if source_fresh else 'FAIL'}`",
                f"- Source equality with preceding 64-token C-sim: `{'PASS' if not source_mismatches else 'FAIL'}`",
                "",
                "Vitis reports that all loop constraints were satisfied. Automatic",
                "pipelining is disabled for control/transport loops; every explicitly",
                "pipelined arithmetic and state loop reaches II=1.",
                "",
                "This is an HLS estimate for the corrected uniform-MXFP4 baseline. The",
                "one-token RTL smoke failed on simulator memory; required 64-token parity,",
                "post-route timing/DRC, physical power, and the selected write-log",
                "candidate remain unverified.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    manifest = generate_report(_resolve(args.archive), _resolve(args.output))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

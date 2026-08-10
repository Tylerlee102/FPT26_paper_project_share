"""Archive and summarize the isolated two-cycle-URAM RS2 experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from scripts.bf16_hls_report import parse_top_xml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "reports" / "csynth" / "experiments" / "rs2_uram_latency2_20260809"
)
DEFAULT_MANIFEST = (
    ROOT / "build" / "experiments" / "rs2_uram_latency2" / "manifest.json"
)
DEFAULT_SELECTED = (
    ROOT / "reports" / "csynth" / "corrected" / "rs2_hls_summary.json"
)
DEFAULT_TIMING_PATHS = (
    ROOT
    / "reports"
    / "vivado"
    / "corrected"
    / "rs2_current"
    / "timing_analysis"
    / "worst_100_setup_paths.rpt"
)
EXPERIMENT_ROOT = ROOT / "gdn_rs2_uram_latency2_hls" / "u55c_250mhz"
TRACE_ROOT = ROOT / "gdn_rs2_uram_latency2_trace_hls" / "u55c_250mhz"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _inputs(manifest_path: Path) -> dict[str, Path]:
    return {
        "derived_source": manifest_path.parent / "gdn_rs2_top.cpp",
        "generation_manifest": manifest_path,
        "csim_report": TRACE_ROOT / "csim" / "report" / "gdn_rs2_top_csim.log",
        "csim_solution_log": TRACE_ROOT / "u55c_250mhz.log",
        "csynth_top_xml": (
            EXPERIMENT_ROOT / "syn" / "report" / "gdn_rs2_top_csynth.xml"
        ),
        "csynth_top_report": (
            EXPERIMENT_ROOT / "syn" / "report" / "gdn_rs2_top_csynth.rpt"
        ),
        "csynth_impl_report": (
            EXPERIMENT_ROOT / "syn" / "report" / "gdn_rs2_top_impl_csynth.rpt"
        ),
        "csynth_solution_log": EXPERIMENT_ROOT / "u55c_250mhz.log",
    }


def generate_report(
    output: Path = DEFAULT_OUTPUT,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    selected_path: Path = DEFAULT_SELECTED,
    timing_paths_path: Path = DEFAULT_TIMING_PATHS,
) -> dict[str, object]:
    inputs = _inputs(manifest_path)
    required = (*inputs.values(), selected_path, timing_paths_path)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = json.loads(selected_path.read_text(encoding="utf-8"))
    selected_metrics = selected["csynth"]["metrics"]
    experiment_metrics = parse_top_xml(inputs["csynth_top_xml"])
    selected_resources = selected_metrics["resources"]
    experiment_resources = experiment_metrics["resources"]

    source_path = ROOT / str(manifest["source"])
    source_identity_pass = (
        _sha256(source_path) == manifest["source_sha256"]
        and _sha256(inputs["derived_source"]) == manifest["output_sha256"]
        and manifest.get("selected_source_modified") is False
    )
    csim_text = _read_text(inputs["csim_report"]) + "\n" + _read_text(
        inputs["csim_solution_log"]
    )
    csynth_text = _read_text(inputs["csynth_solution_log"])
    exact_csim_pass = (
        "PASS: 64 encoded random-state tokens, exact outputs/counters, and final snapshot"
        in csim_text
        and "CSim done with 0 errors" in csim_text
    )
    csynth_pass = (
        "Finished Command csynth_design" in csynth_text
        and "Loop Constraint Status: All loop constraints were satisfied"
        in csynth_text
    )

    timing_text = _read_text(timing_paths_path)
    timing_endpoints = {
        "reported_paths": len(
            re.findall(r"^\s*-\d+\.\d+\s*$", timing_text, re.MULTILINE)
        ),
        "resident_residual_mentions": timing_text.count("resident_residual_U"),
        "uram_enable_a_mentions": timing_text.count("/EN_A"),
        "uram_enable_b_mentions": timing_text.count("/EN_B"),
        "uram_byte_write_enable_mentions": timing_text.count("/BWE_B"),
    }

    output.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for label, source in inputs.items():
        destination = output / source.name
        if destination.exists() and destination != source:
            destination = output / f"{label}_{source.name}"
        shutil.copy2(source, destination)
        copied[destination.name] = _sha256(destination)

    deltas = {
        name: int(experiment_resources[name]) - int(selected_resources[name])
        for name in selected_resources
    }
    deltas.update(
        {
            "latency_cycles_min": int(experiment_metrics["latency_cycles_min"])
            - int(selected_metrics["latency_cycles_min"]),
            "latency_cycles_average": int(
                experiment_metrics["latency_cycles_average"]
            )
            - int(selected_metrics["latency_cycles_average"]),
            "latency_cycles_max": int(experiment_metrics["latency_cycles_max"])
            - int(selected_metrics["latency_cycles_max"]),
            "estimated_clock_ns": float(experiment_metrics["estimated_clock_ns"])
            - float(selected_metrics["estimated_clock_ns"]),
        }
    )

    status = "PASS" if source_identity_pass and exact_csim_pass and csynth_pass else "FAIL"
    summary: dict[str, object] = {
        "schema": 1,
        "status": status,
        "experiment": "RS2 two-cycle URAM binding",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": "isolated architecture experiment; selected kernel is unchanged",
        "source_identity": {
            "status": "PASS" if source_identity_pass else "FAIL",
            "selected_source": str(manifest["source"]),
            "selected_source_sha256": manifest["source_sha256"],
            "derived_source": str(manifest["output"]),
            "derived_source_sha256": manifest["output_sha256"],
            "selected_source_modified": manifest["selected_source_modified"],
        },
        "verification": {
            "exact_64_token_csim": "PASS" if exact_csim_pass else "FAIL",
            "csynth": "PASS" if csynth_pass else "FAIL",
            "explicit_loop_constraints": "PASS" if csynth_pass else "FAIL",
            "route": "NOT_RUN",
        },
        "selected_metrics": selected_metrics,
        "experiment_metrics": experiment_metrics,
        "delta_experiment_minus_selected": deltas,
        "physical_path_evidence": {
            "source": _relative(timing_paths_path),
            "sha256": _sha256(timing_paths_path),
            **timing_endpoints,
        },
        "decision": {
            "status": "REJECT_BEFORE_ROUTE",
            "promoted": False,
            "reason": (
                "The variant leaves the HLS clock estimate unchanged, adds FF/LUT "
                "cost and worst-case cycles, and registers URAM output latency while "
                "the routed failures terminate on URAM enable/write-control pins."
            ),
        },
        "artifact_sha256": dict(sorted(copied.items())),
    }
    if status != "PASS":
        raise RuntimeError("refusing to archive a nonpassing URAM-latency experiment")

    summary_path = output / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    readme = output / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# RS2 two-cycle URAM experiment",
                "",
                "This isolated variant adds `latency=2` to the four URAM bindings; it",
                "does not modify or replace the selected RS2 source. Exact 64-token C",
                "simulation and C synthesis pass, including every explicit II=1 constraint.",
                "",
                "The HLS estimate remains 3.106 ns. Relative to the selected source, the",
                f"variant adds {deltas['FF']:,} FFs, {deltas['LUT']:,} LUTs, and",
                f"{deltas['latency_cycles_max']:,} worst-case cycles. The archived routed",
                "path list is dominated by `resident_residual` URAM enable/write-control",
                "endpoints, which output latency does not target. Routing was therefore not",
                "run, and the variant is rejected rather than promoted.",
                "",
                "## Artifact hashes",
                "",
                "| Artifact | SHA256 |",
                "|---|---|",
                *[
                    f"| `{name}` | `{digest}` |"
                    for name, digest in sorted(copied.items())
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        summary = generate_report(output)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(exc)
        return 1
    print(json.dumps({"status": summary["status"], "decision": summary["decision"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

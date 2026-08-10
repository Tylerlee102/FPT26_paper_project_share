"""Archive and summarize the isolated RS2 fold-write timing experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from scripts.bf16_hls_report import parse_top_xml
from scripts.e2m0_vivado_report import parse_drc, parse_power, parse_timing_summary
from scripts.rs2_vivado_report import parse_fractional_utilization


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "vivado" / "experiments" / "rs2_fold_write_20260809"
HLS_ROOT = ROOT / "gdn_rs2_fold_write_hls" / "u55c_250mhz"
CSIM_ROOT = ROOT / "gdn_rs2_fold_write_trace_hls" / "u55c_250mhz"
MANIFEST = ROOT / "build" / "experiments" / "rs2_fold_write" / "manifest.json"
SELECTED_HLS = ROOT / "reports" / "csynth" / "corrected" / "rs2_hls_summary.json"
SELECTED_VIVADO = (
    ROOT / "reports" / "vivado" / "corrected" / "rs2_current" / "rs2_vivado_summary.json"
)
PRIOR = (
    ROOT
    / "reports"
    / "vivado"
    / "experiments"
    / "rs2_fold_control_20260809"
    / "summary.json"
)
OOC_MANIFEST = ROOT / "build" / "vivado" / "rs2_fold_write_ooc_rtl" / "manifest.json"
IMPL_LOG = ROOT / "reports" / "vivado" / "vivado_rs2-fold-write-impl.log"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _path_characteristics(text: str) -> dict[str, int | float]:
    patterns = {
        "path_delay_ns": r"\| Path Delay\s*\|\s*([\d.]+)",
        "logic_delay_ns": r"\| Logic Delay\s*\|\s*([\d.]+)",
        "net_delay_ns": r"\| Net Delay\s*\|\s*([\d.]+)",
        "logic_levels": r"\| Logic Levels\s*\|\s*(\d+)",
        "slr_crossings": r"\| SLR Crossings\s*\|\s*(\d+)",
        "high_fanout": r"\| High Fanout\s*\|\s*(\d+)",
    }
    result: dict[str, int | float] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match is None:
            raise ValueError(f"missing design-analysis field: {key}")
        result[key] = (
            int(match.group(1))
            if key in {"logic_levels", "slr_crossings", "high_fanout"}
            else float(match.group(1))
        )
    return result


def _delta_timing(current: dict[str, object], baseline: dict[str, object]) -> dict[str, object]:
    return {
        "wns_ns": float(current["wns_ns"]) - float(baseline["wns_ns"]),
        "tns_ns": float(current["tns_ns"]) - float(baseline["tns_ns"]),
        "setup_failing_endpoints": int(current["setup_failing_endpoints"])
        - int(baseline["setup_failing_endpoints"]),
    }


def generate_report(output: Path = OUTPUT) -> dict[str, object]:
    paths = {
        "derived_source": MANIFEST.parent / "gdn_rs2_top.cpp",
        "generation_manifest": MANIFEST,
        "csim_report": CSIM_ROOT / "csim" / "report" / "gdn_rs2_top_csim.log",
        "csim_solution_log": CSIM_ROOT / "u55c_250mhz.log",
        "csynth_top_xml": HLS_ROOT / "syn" / "report" / "gdn_rs2_top_csynth.xml",
        "csynth_top_report": HLS_ROOT / "syn" / "report" / "gdn_rs2_top_csynth.rpt",
        "csynth_impl_report": HLS_ROOT / "syn" / "report" / "gdn_rs2_top_impl_csynth.rpt",
        "csynth_solution_log": HLS_ROOT / "u55c_250mhz.log",
        "ooc_manifest": OOC_MANIFEST,
        "vivado_impl_log": IMPL_LOG,
        "utilization": output / "impl_util.rpt",
        "timing": output / "impl_timing.rpt",
        "drc": output / "impl_drc.rpt",
        "power": output / "impl_power.rpt",
        "design_analysis": output / "design_analysis.rpt",
        "worst_paths": output / "worst_100_setup_paths.rpt",
    }
    for path in (*paths.values(), SELECTED_HLS, SELECTED_VIVADO, PRIOR):
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ooc = json.loads(OOC_MANIFEST.read_text(encoding="utf-8"))
    selected_hls = json.loads(SELECTED_HLS.read_text(encoding="utf-8"))
    selected_vivado = json.loads(SELECTED_VIVADO.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    experiment_hls = parse_top_xml(paths["csynth_top_xml"])
    timing = parse_timing_summary(_read(paths["timing"]))
    utilization = parse_fractional_utilization(_read(paths["utilization"]))
    drc = parse_drc(_read(paths["drc"]))
    power = parse_power(_read(paths["power"]))
    path_characteristics = _path_characteristics(_read(paths["design_analysis"]))

    selected_source = ROOT / str(manifest["source"])
    derived_source = ROOT / str(manifest["output"])
    source_identity_pass = (
        manifest.get("selected_source_modified") is False
        and _sha256(selected_source) == manifest["source_sha256"]
        and _sha256(derived_source) == manifest["output_sha256"]
        and ooc.get("status") == "PASS"
        and _sha256(ROOT / str(ooc["source"])) == ooc["source_sha256"]
        and _sha256(ROOT / str(ooc["output"])) == ooc["output_sha256"]
    )
    csim_text = _read(paths["csim_report"]) + "\n" + _read(paths["csim_solution_log"])
    csynth_text = _read(paths["csynth_solution_log"])
    impl_text = _read(paths["vivado_impl_log"])
    exact_pass = (
        "PASS: 64 encoded random-state tokens, exact outputs/counters, and final snapshot"
        in csim_text
        and "CSim done with 0 errors" in csim_text
    )
    csynth_pass = (
        "Finished Command csynth_design" in csynth_text
        and "Loop Constraint Status: All loop constraints were satisfied" in csynth_text
        and "Implementing module 'p_anonymous_namespace_commit_fold_block'" in csynth_text
        and "Implementing module 'p_anonymous_namespace_fold_log_if_full'" in csynth_text
    )
    route_pass = (
        "route_design completed successfully" in impl_text
        and "rs2_fold_write_post_impl.dcp' has been generated" in impl_text
        and "Exiting Vivado" in impl_text
    )

    selected_hls_metrics = selected_hls["csynth"]["metrics"]
    selected_timing = selected_vivado["target_clock"]["timing"]
    prior_timing = prior["postroute"]["experiment_timing"]
    prior_path = prior["postroute"]["experiment_path_characteristics"]
    selected_path = prior["postroute"]["selected_path_characteristics"]
    hls_delta = {
        key: int(experiment_hls["resources"][key])
        - int(selected_hls_metrics["resources"][key])
        for key in selected_hls_metrics["resources"]
    }
    hls_delta["latency_cycles_max"] = int(experiment_hls["latency_cycles_max"]) - int(
        selected_hls_metrics["latency_cycles_max"]
    )
    path_delta_prior = {
        key: float(path_characteristics[key]) - float(prior_path[key])
        for key in path_characteristics
    }

    output.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for label in (
        "derived_source",
        "generation_manifest",
        "csim_report",
        "csim_solution_log",
        "csynth_top_xml",
        "csynth_top_report",
        "csynth_impl_report",
        "csynth_solution_log",
        "ooc_manifest",
        "vivado_impl_log",
    ):
        source = paths[label]
        destination = output / f"{label}_{source.name}"
        shutil.copy2(source, destination)
        copied[destination.name] = _sha256(destination)
    for path in output.glob("*.rpt"):
        copied[path.name] = _sha256(path)

    status = (
        "PASS"
        if source_identity_pass
        and exact_pass
        and csynth_pass
        and route_pass
        and drc["error_count"] == 0
        and drc["critical_warning_count"] == 0
        else "FAIL"
    )
    summary: dict[str, object] = {
        "schema": 1,
        "status": status,
        "experiment": "RS2 localized fold control and write commit",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": "isolated architecture timing experiment; selected kernel unchanged",
        "source_identity": {
            "status": "PASS" if source_identity_pass else "FAIL",
            "selected_source_modified": False,
            "selected_source_sha256": manifest["source_sha256"],
            "derived_source_sha256": manifest["output_sha256"],
            "ooc_top_sha256": ooc["output_sha256"],
        },
        "verification": {
            "exact_64_token_csim": "PASS" if exact_pass else "FAIL",
            "csynth": "PASS" if csynth_pass else "FAIL",
            "explicit_loop_constraints": "PASS" if csynth_pass else "FAIL",
            "route_completion": "PASS" if route_pass else "FAIL",
            "target_250mhz": (
                "PASS"
                if float(timing["wns_ns"]) >= 0.0 and float(timing["whs_ns"]) >= 0.0
                else "FAIL"
            ),
        },
        "hls": {
            "selected": selected_hls_metrics,
            "experiment": experiment_hls,
            "delta_experiment_minus_selected": hls_delta,
        },
        "postroute": {
            "selected_timing": selected_timing,
            "prior_fold_control_timing": prior_timing,
            "experiment_timing": timing,
            "delta_experiment_minus_selected": _delta_timing(timing, selected_timing),
            "delta_experiment_minus_prior": _delta_timing(timing, prior_timing),
            "selected_path_characteristics": selected_path,
            "prior_fold_control_path_characteristics": prior_path,
            "experiment_path_characteristics": path_characteristics,
            "path_delta_experiment_minus_prior": path_delta_prior,
            "utilization": utilization,
            "drc": drc,
            "vectorless_power_at_failed_4ns_constraint": power,
        },
        "decision": {
            "status": "BEST_ISOLATED_TIMING_REJECT_250MHZ",
            "promoted": False,
            "reason": (
                "The commit-stage hierarchy gives the best isolated WNS and fewer "
                "failing endpoints, but setup remains negative at 250 MHz, high fanout "
                "moves back to outer fold control, and latency increases."
            ),
        },
        "artifact_sha256": dict(sorted(copied.items())),
    }
    if status != "PASS":
        raise RuntimeError("refusing to archive an invalid fold-write experiment")

    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "README.md").write_text(
        "\n".join(
            [
                "# RS2 localized fold-write timing experiment",
                "",
                "This source-isolated variant preserves the localized fold decision and",
                "moves each folded-state write into a separate non-inlined commit helper.",
                "It passes exact 64-token C simulation, synthesis, and matched U55C routing.",
                "",
                f"Post-route WNS is {timing['wns_ns']:.3f} ns, improving on the selected",
                f"{selected_timing['wns_ns']:.3f} ns and prior helper-only",
                f"{prior_timing['wns_ns']:.3f} ns results. Hold and DRC pass, but 250 MHz",
                "setup timing still fails, so the variant is not promoted.",
                "",
                "The worst path again begins in outer fold control and ends at a",
                "resident-primary URAM enable. The commit helper also increases worst-case",
                "latency. Vectorless power at the failed 4 ns constraint is diagnostic only.",
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
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        result = generate_report(output)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(exc)
        return 1
    print(json.dumps({"status": result["status"], "decision": result["decision"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

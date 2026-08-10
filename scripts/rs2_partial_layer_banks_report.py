"""Archive and summarize the isolated RS2 partial layer-bank experiment."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from scripts.bf16_hls_report import parse_top_xml
from scripts.e2m0_vivado_report import parse_drc, parse_power, parse_timing_summary
from scripts.rs2_layer_banks_report import _delta, _path_characteristics, _read, _sha256
from scripts.rs2_vivado_report import parse_fractional_utilization


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "reports"
    / "vivado"
    / "experiments"
    / "rs2_partial_layer_banks_20260810"
)
HLS_ROOT = ROOT / "gdn_rs2_partial_layer_banks_hls" / "u55c_250mhz"
CSIM_ROOT = ROOT / "gdn_rs2_partial_layer_banks_trace_hls" / "u55c_250mhz"
MANIFEST = (
    ROOT / "build" / "experiments" / "rs2_partial_layer_banks" / "manifest.json"
)
OOC_MANIFEST = (
    ROOT / "build" / "vivado" / "rs2_partial_layer_banks_ooc_rtl" / "manifest.json"
)
IMPL_LOG = ROOT / "reports" / "vivado" / "vivado_rs2-partial-layer-banks-impl.log"
SELECTED_HLS = ROOT / "reports" / "csynth" / "corrected" / "rs2_hls_summary.json"
SELECTED_VIVADO = (
    ROOT / "reports" / "vivado" / "corrected" / "rs2_current" / "rs2_vivado_summary.json"
)
SELECTED_UTIL = (
    ROOT / "reports" / "vivado" / "corrected" / "rs2_current" / "impl_util.rpt"
)
BEST_ISOLATED = (
    ROOT
    / "reports"
    / "vivado"
    / "experiments"
    / "rs2_fold_write_20260809"
    / "summary.json"
)


def _utilization_delta(
    current: dict[str, dict[str, int | float]],
    baseline: dict[str, dict[str, int | float]],
) -> dict[str, int]:
    return {
        key: int(current[key]["used"]) - int(baseline[key]["used"])
        for key in baseline
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
    for path in (
        *paths.values(),
        SELECTED_HLS,
        SELECTED_VIVADO,
        SELECTED_UTIL,
        BEST_ISOLATED,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ooc = json.loads(OOC_MANIFEST.read_text(encoding="utf-8"))
    selected_hls = json.loads(SELECTED_HLS.read_text(encoding="utf-8"))["csynth"][
        "metrics"
    ]
    selected_vivado = json.loads(SELECTED_VIVADO.read_text(encoding="utf-8"))
    best = json.loads(BEST_ISOLATED.read_text(encoding="utf-8"))
    experiment_hls = parse_top_xml(paths["csynth_top_xml"])
    timing = parse_timing_summary(_read(paths["timing"]))
    utilization = parse_fractional_utilization(_read(paths["utilization"]))
    selected_utilization = parse_fractional_utilization(_read(SELECTED_UTIL))
    drc = parse_drc(_read(paths["drc"]))
    power = parse_power(_read(paths["power"]))
    path_characteristics = _path_characteristics(_read(paths["design_analysis"]))

    selected_source = ROOT / str(manifest["source"])
    derived_source = ROOT / str(manifest["output"])
    source_identity_pass = (
        manifest.get("selected_source_modified") is False
        and manifest.get("partition_factor") == 6
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
    cyclic_marker = "Cyclic partitioning with factor 6 on dimension 2"
    csynth_pass = (
        "Finished Command csynth_design" in csynth_text
        and "Loop Constraint Status: All loop constraints were satisfied" in csynth_text
        and csynth_text.count(cyclic_marker) >= 2
        and "resident_residual'" in csynth_text
        and "resident_primary'" in csynth_text
    )
    route_pass = (
        "route_design completed successfully" in impl_text
        and "rs2_partial_layer_banks_post_impl.dcp' has been generated" in impl_text
        and "Exiting Vivado" in impl_text
    )

    selected_timing = selected_vivado["target_clock"]["timing"]
    best_timing = best["postroute"]["experiment_timing"]
    hls_resource_delta = {
        key: int(experiment_hls["resources"][key])
        - int(selected_hls["resources"][key])
        for key in selected_hls["resources"]
    }
    hls_resource_delta["latency_cycles_max"] = int(
        experiment_hls["latency_cycles_max"]
    ) - int(selected_hls["latency_cycles_max"])
    timing_keys = ("wns_ns", "tns_ns", "setup_failing_endpoints")

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
        "experiment": "RS2 six-way cyclic primary/residual layer banks",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": "isolated architecture experiment; selected kernel unchanged",
        "comparison_sources": {
            "selected_hls": {
                "path": SELECTED_HLS.relative_to(ROOT).as_posix(),
                "sha256": _sha256(SELECTED_HLS),
            },
            "selected_vivado": {
                "path": SELECTED_VIVADO.relative_to(ROOT).as_posix(),
                "sha256": _sha256(SELECTED_VIVADO),
            },
            "selected_utilization": {
                "path": SELECTED_UTIL.relative_to(ROOT).as_posix(),
                "sha256": _sha256(SELECTED_UTIL),
            },
            "best_isolated": {
                "path": BEST_ISOLATED.relative_to(ROOT).as_posix(),
                "sha256": _sha256(BEST_ISOLATED),
            },
        },
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
            "cyclic_factor_6_layer_partition": "PASS" if csynth_pass else "FAIL",
            "route_completion": "PASS" if route_pass else "FAIL",
            "target_250mhz": "PASS" if float(timing["wns_ns"]) >= 0.0 else "FAIL",
        },
        "hls": {
            "selected": selected_hls,
            "experiment": experiment_hls,
            "delta_experiment_minus_selected": hls_resource_delta,
        },
        "postroute": {
            "selected_timing": selected_timing,
            "best_isolated_timing": best_timing,
            "experiment_timing": timing,
            "delta_experiment_minus_selected": _delta(
                timing, selected_timing, timing_keys
            ),
            "delta_experiment_minus_best_isolated": _delta(
                timing, best_timing, timing_keys
            ),
            "experiment_path_characteristics": path_characteristics,
            "selected_utilization": selected_utilization,
            "utilization": utilization,
            "utilization_delta_experiment_minus_selected": _utilization_delta(
                utilization, selected_utilization
            ),
            "drc": drc,
            "route_log_timing_critical_warning_count": impl_text.count(
                "CRITICAL WARNING: [Route 35-39]"
            ),
            "vectorless_power_at_failed_4ns_constraint": power,
        },
        "decision": {
            "status": "REJECT_PARTIAL_LAYER_BANKING_TIMING_AND_COST",
            "promoted": False,
            "reason": (
                "Six-way cyclic banking slightly improves worst slack but does not close "
                "250 MHz, worsens TNS and failing-endpoint count, and increases routed "
                "LUT/register/DSP cost relative to the selected design."
            ),
        },
        "artifact_sha256": dict(sorted(copied.items())),
    }
    if status != "PASS":
        raise RuntimeError("refusing to archive an invalid partial layer-bank experiment")

    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    delta = summary["postroute"]["delta_experiment_minus_selected"]
    utilization_delta = summary["postroute"][
        "utilization_delta_experiment_minus_selected"
    ]
    (output / "README.md").write_text(
        "\n".join(
            [
                "# RS2 six-way cyclic layer-bank experiment",
                "",
                "This source-isolated variant cyclically partitions the primary and",
                "residual state stores into six banks while preserving arithmetic,",
                "capacity, commands, fold cadence, and the exact recurrent-state trace.",
                "",
                f"The routed result reaches {timing['wns_ns']:.3f} ns WNS and",
                f"{timing['tns_ns']:,.3f} ns TNS with {timing['setup_failing_endpoints']:,}",
                "failing setup endpoints. Hold and DRC pass, but 250 MHz setup does not.",
                f"Relative to selected, WNS changes by {delta['wns_ns']:+.3f} ns, TNS",
                f"by {delta['tns_ns']:+,.3f} ns, and failing endpoints by",
                f"{delta['setup_failing_endpoints']:+,}. Routed LUTs change by",
                f"{utilization_delta['clb_luts']:+,}, registers by",
                f"{utilization_delta['clb_registers']:+,}, and DSPs by",
                f"{utilization_delta['dsps']:+,}.",
                "",
                "The worst path crosses one SLR and has high fanout 41 on URAM control.",
                "The variant is not promoted. Vectorless power at the failed 4 ns",
                "constraint is diagnostic only.",
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
    except (FileNotFoundError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        print(exc)
        return 1
    print(json.dumps({"status": result["status"], "decision": result["decision"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

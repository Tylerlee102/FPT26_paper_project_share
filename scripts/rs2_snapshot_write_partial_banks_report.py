"""Archive the isolated RS2 snapshot-write locality experiment."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
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
    / "rs2_snapshot_write_partial_banks_20260810"
)
HLS_ROOT = ROOT / "gdn_rs2_snapshot_write_partial_banks_hls" / "u55c_250mhz"
CSIM_ROOT = ROOT / "gdn_rs2_snapshot_write_partial_banks_trace_hls" / "u55c_250mhz"
MANIFEST = (
    ROOT
    / "build"
    / "experiments"
    / "rs2_snapshot_write_partial_banks"
    / "manifest.json"
)
OOC_MANIFEST = (
    ROOT
    / "build"
    / "vivado"
    / "rs2_snapshot_write_partial_banks_ooc_rtl"
    / "manifest.json"
)
IMPL_LOG = (
    ROOT
    / "reports"
    / "vivado"
    / "vivado_rs2-snapshot-write-partial-banks-impl.log"
)
SELECTED_HLS = ROOT / "reports" / "csynth" / "corrected" / "rs2_hls_summary.json"
SELECTED_VIVADO = (
    ROOT
    / "reports"
    / "vivado"
    / "corrected"
    / "rs2_current"
    / "rs2_vivado_summary.json"
)
SELECTED_UTIL = (
    ROOT / "reports" / "vivado" / "corrected" / "rs2_current" / "impl_util.rpt"
)
PARENT = (
    ROOT
    / "reports"
    / "vivado"
    / "experiments"
    / "rs2_fold_write_partial_banks_20260810"
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


def _startpoint_origins(text: str) -> dict[str, int]:
    origins: Counter[str] = Counter()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.endswith(("/C", "/CLK")) or line[:1].isspace():
            continue
        if "commit_snapshot_block" in stripped:
            label = "commit_snapshot_block"
        elif "load_snapshot" in stripped:
            label = "load_snapshot"
        elif "gmem5_m_axi" in stripped:
            label = "gmem5_axi_backpressure"
        elif "read_snapshot" in stripped:
            label = "read_snapshot"
        elif "reset_slot" in stripped:
            label = "reset_slot"
        elif "trunc_ln1150" in stripped:
            label = "layer_address_control"
        elif "ram_reg_uram" in stripped:
            label = "resident_uram_read_clock"
        elif "dot_base" in stripped:
            label = "dot_base"
        elif "fold" in stripped:
            label = "fold"
        elif "ap_CS_fsm_reg" in stripped:
            label = "top_fsm"
        elif "grp_gdn_rs2_top_impl" in stripped:
            label = "top_impl"
        else:
            label = "other"
        origins[label] += 1
    return dict(sorted(origins.items()))


def generate_report(output: Path = OUTPUT) -> dict[str, object]:
    paths = {
        "derived_source": MANIFEST.parent / "gdn_rs2_top.cpp",
        "generation_manifest": MANIFEST,
        "csim_report": CSIM_ROOT / "csim" / "report" / "gdn_rs2_top_csim.log",
        "csim_solution_log": CSIM_ROOT / "u55c_250mhz.log",
        "csynth_top_xml": HLS_ROOT / "syn" / "report" / "gdn_rs2_top_csynth.xml",
        "csynth_top_report": HLS_ROOT / "syn" / "report" / "gdn_rs2_top_csynth.rpt",
        "csynth_impl_report": HLS_ROOT
        / "syn"
        / "report"
        / "gdn_rs2_top_impl_csynth.rpt",
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
        PARENT,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ooc = json.loads(OOC_MANIFEST.read_text(encoding="utf-8"))
    selected_hls = json.loads(SELECTED_HLS.read_text(encoding="utf-8"))["csynth"][
        "metrics"
    ]
    selected_vivado = json.loads(SELECTED_VIVADO.read_text(encoding="utf-8"))
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    experiment_hls = parse_top_xml(paths["csynth_top_xml"])
    timing = parse_timing_summary(_read(paths["timing"]))
    utilization = parse_fractional_utilization(_read(paths["utilization"]))
    selected_utilization = parse_fractional_utilization(_read(SELECTED_UTIL))
    drc = parse_drc(_read(paths["drc"]))
    power = parse_power(_read(paths["power"]))
    path_characteristics = _path_characteristics(_read(paths["design_analysis"]))
    startpoint_origins = _startpoint_origins(_read(paths["worst_paths"]))

    selected_source = ROOT / str(manifest["source"])
    derived_source = ROOT / str(manifest["output"])
    source_identity_pass = (
        manifest.get("selected_source_modified") is False
        and manifest.get("snapshot_write_transform")
        == {"helpers": 1, "replacements": 1}
        and manifest.get("parent_transform", {}).get("partition_factor") == 6
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
    helper_rtl = HLS_ROOT / "syn" / "verilog"
    cyclic_marker = "Cyclic partitioning with factor 6 on dimension 2"
    csynth_pass = (
        "Finished Command csynth_design" in csynth_text
        and "Loop Constraint Status: All loop constraints were satisfied" in csynth_text
        and csynth_text.count(cyclic_marker) >= 2
        and (helper_rtl / "gdn_rs2_top_p_anonymous_namespace_commit_snapshot_block.v").is_file()
        and (helper_rtl / "gdn_rs2_top_p_anonymous_namespace_commit_fold_block.v").is_file()
        and (helper_rtl / "gdn_rs2_top_p_anonymous_namespace_fold_log_if_full.v").is_file()
    )
    route_pass = (
        "route_design completed successfully" in impl_text
        and "rs2_snapshot_write_partial_banks_post_impl.dcp' has been generated"
        in impl_text
        and "Exiting Vivado" in impl_text
    )

    selected_timing = selected_vivado["target_clock"]["timing"]
    parent_timing = parent["postroute"]["experiment_timing"]
    timing_keys = ("wns_ns", "tns_ns", "setup_failing_endpoints")
    hls_resource_delta = {
        key: int(experiment_hls["resources"][key])
        - int(selected_hls["resources"][key])
        for key in selected_hls["resources"]
    }
    hls_resource_delta["latency_cycles_max"] = int(
        experiment_hls["latency_cycles_max"]
    ) - int(selected_hls["latency_cycles_max"])

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
        and sum(startpoint_origins.values()) == 100
        and drc["error_count"] == 0
        and drc["critical_warning_count"] == 0
        else "FAIL"
    )
    if float(timing["wns_ns"]) >= 0.0:
        decision_status = "PROMOTION_CANDIDATE_SNAPSHOT_WRITE_LOCALITY"
        decision_reason = (
            "The isolated variant closes the declared 250 MHz constraint and must be "
            "ported into the selected source and reverified before promotion."
        )
    elif float(timing["wns_ns"]) > float(parent_timing["wns_ns"]):
        if (
            float(timing["tns_ns"]) > float(parent_timing["tns_ns"])
            and int(timing["setup_failing_endpoints"])
            <= int(parent_timing["setup_failing_endpoints"])
        ):
            decision_status = "RETAIN_PROMISING_SNAPSHOT_WRITE_LOCALITY"
            decision_reason = (
                "Snapshot-write hierarchy improves every registered setup metric "
                "relative to the matched parent but does not close 250 MHz; the idea "
                "should be isolated on a lower-cost parent before promotion."
            )
        else:
            decision_status = "RETAIN_SNAPSHOT_WRITE_LOCALITY_FOR_NEXT_ITERATION"
            decision_reason = (
                "Snapshot-write hierarchy improves worst setup slack but worsens at "
                "least one aggregate setup metric relative to the matched parent and "
                "does not close 250 MHz; the locality idea may inform a smaller "
                "unbanked experiment, while this composition is not promoted."
            )
    else:
        decision_status = "REJECT_SNAPSHOT_WRITE_LOCALITY_TIMING"
        decision_reason = (
            "Snapshot-write hierarchy does not improve worst setup slack relative to "
            "the matched parent and remains below the 250 MHz target."
        )

    comparison_sources = {
        "selected_hls": SELECTED_HLS,
        "selected_vivado": SELECTED_VIVADO,
        "selected_utilization": SELECTED_UTIL,
        "combined_parent": PARENT,
    }
    summary: dict[str, object] = {
        "schema": 1,
        "status": status,
        "experiment": "RS2 localized snapshot/fold writes with six-way cyclic layer banks",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": "isolated architecture experiment; selected kernel unchanged",
        "comparison_sources": {
            label: {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(path),
            }
            for label, path in comparison_sources.items()
        },
        "source_identity": {
            "status": "PASS" if source_identity_pass else "FAIL",
            "selected_source_modified": False,
            "selected_source_sha256": manifest["source_sha256"],
            "parent_output_sha256": manifest["parent_output_sha256"],
            "derived_source_sha256": manifest["output_sha256"],
            "ooc_top_sha256": ooc["output_sha256"],
        },
        "verification": {
            "exact_64_token_csim": "PASS" if exact_pass else "FAIL",
            "csynth": "PASS" if csynth_pass else "FAIL",
            "explicit_loop_constraints": "PASS" if csynth_pass else "FAIL",
            "snapshot_and_fold_write_hierarchy": "PASS" if csynth_pass else "FAIL",
            "cyclic_factor_6_layer_partition": "PASS" if csynth_pass else "FAIL",
            "worst_100_path_classification": (
                "PASS" if sum(startpoint_origins.values()) == 100 else "FAIL"
            ),
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
            "combined_parent_timing": parent_timing,
            "experiment_timing": timing,
            "delta_experiment_minus_selected": _delta(
                timing, selected_timing, timing_keys
            ),
            "delta_experiment_minus_combined_parent": _delta(
                timing, parent_timing, timing_keys
            ),
            "experiment_path_characteristics": path_characteristics,
            "worst_100_startpoint_origins": startpoint_origins,
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
            "status": decision_status,
            "promoted": False,
            "reason": decision_reason,
        },
        "artifact_sha256": dict(sorted(copied.items())),
    }
    if status != "PASS":
        raise RuntimeError("refusing to archive an invalid snapshot-write experiment")

    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    parent_delta = summary["postroute"][
        "delta_experiment_minus_combined_parent"
    ]
    selected_delta = summary["postroute"]["delta_experiment_minus_selected"]
    (output / "README.md").write_text(
        "\n".join(
            [
                "# RS2 snapshot-write locality experiment",
                "",
                "This source-isolated variant places LOAD-time primary/residual writes",
                "behind a non-inlined helper on top of the matched fold-write plus",
                "factor-six banking parent. Arithmetic, state layout and capacity,",
                "commands, fold cadence, target, and route directives remain fixed.",
                "",
                f"Exact 64-token C simulation passes. HLS estimates {experiment_hls['estimated_clock_ns']:.3f} ns",
                f"and {experiment_hls['latency_cycles_max']:,} maximum cycles. The final",
                f"route reaches {timing['wns_ns']:.3f} ns WNS and {timing['tns_ns']:,.3f} ns TNS",
                f"with {timing['setup_failing_endpoints']:,} failing setup endpoints.",
                f"Hold is {timing['whs_ns']:+.3f} ns with {timing['hold_failing_endpoints']} failures;",
                f"DRC has {drc['critical_warning_count']} critical warnings and {drc['error_count']} errors.",
                "",
                f"Relative to the combined parent, WNS changes by {parent_delta['wns_ns']:+.3f} ns,",
                f"TNS by {parent_delta['tns_ns']:+,.3f} ns, and failing endpoints by",
                f"{parent_delta['setup_failing_endpoints']:+,}. Relative to selected, WNS",
                f"changes by {selected_delta['wns_ns']:+.3f} ns.",
                f"The worst path is {path_characteristics['path_delay_ns']:.3f} ns, with",
                f"{path_characteristics['logic_delay_ns']:.3f} ns logic and",
                f"{path_characteristics['net_delay_ns']:.3f} ns net delay across",
                f"{path_characteristics['slr_crossings']} SLR crossings.",
                "",
                f"Decision: `{decision_status}`. Vectorless power at a failed 4 ns",
                "constraint is diagnostic only.",
                "",
                "## Worst-100 startpoint origins",
                "",
                "| Origin | Paths |",
                "|---|---:|",
                *[
                    f"| `{name}` | {count} |"
                    for name, count in startpoint_origins.items()
                ],
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

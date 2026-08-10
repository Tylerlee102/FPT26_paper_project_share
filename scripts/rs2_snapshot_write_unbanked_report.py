"""Archive the isolated unbanked RS2 snapshot-write experiment."""

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
OUTPUT = ROOT / "reports/vivado/experiments/rs2_snapshot_write_unbanked_20260810"
HLS_ROOT = ROOT / "gdn_rs2_snapshot_write_unbanked_hls/u55c_250mhz"
CSIM_ROOT = ROOT / "gdn_rs2_snapshot_write_unbanked_trace_hls/u55c_250mhz"
MANIFEST = ROOT / "build/experiments/rs2_snapshot_write_unbanked/manifest.json"
OOC_MANIFEST = ROOT / "build/vivado/rs2_snapshot_write_unbanked_ooc_rtl/manifest.json"
IMPL_LOG = ROOT / "reports/vivado/vivado_rs2-snapshot-write-unbanked-impl.log"
SELECTED_HLS = ROOT / "reports/csynth/corrected/rs2_hls_summary.json"
SELECTED_VIVADO = ROOT / "reports/vivado/corrected/rs2_current/rs2_vivado_summary.json"
SELECTED_UTIL = ROOT / "reports/vivado/corrected/rs2_current/impl_util.rpt"
PARENT = ROOT / "reports/vivado/experiments/rs2_fold_write_20260809/summary.json"


def _origins(text: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for line in text.splitlines():
        path = line.strip()
        if not path.endswith(("/C", "/CLK")) or line[:1].isspace():
            continue
        if "commit_snapshot_block" in path:
            label = "commit_snapshot_block"
        elif "load_snapshot" in path:
            label = "load_snapshot"
        elif "read_snapshot" in path:
            label = "read_snapshot"
        elif "reset_slot" in path:
            label = "reset_slot"
        elif "trunc_ln1150" in path:
            label = "layer_address_control"
        elif "ram_reg_uram" in path:
            label = "resident_uram_read_clock"
        elif "fold" in path:
            label = "fold"
        elif "ap_CS_fsm_reg" in path:
            label = "top_fsm"
        elif "grp_gdn_rs2_top_impl" in path:
            label = "top_impl"
        else:
            label = "other"
        counts[label] += 1
    return dict(sorted(counts.items()))


def generate_report(output: Path = OUTPUT) -> dict[str, object]:
    files = {
        "derived_source": MANIFEST.parent / "gdn_rs2_top.cpp",
        "generation_manifest": MANIFEST,
        "csim_report": CSIM_ROOT / "csim/report/gdn_rs2_top_csim.log",
        "csim_solution_log": CSIM_ROOT / "u55c_250mhz.log",
        "csynth_top_xml": HLS_ROOT / "syn/report/gdn_rs2_top_csynth.xml",
        "csynth_top_report": HLS_ROOT / "syn/report/gdn_rs2_top_csynth.rpt",
        "csynth_impl_report": HLS_ROOT / "syn/report/gdn_rs2_top_impl_csynth.rpt",
        "csynth_solution_log": HLS_ROOT / "u55c_250mhz.log",
        "ooc_manifest": OOC_MANIFEST,
        "vivado_impl_log": IMPL_LOG,
        "utilization": output / "impl_util.rpt",
        "timing": output / "impl_timing.rpt",
        "drc": output / "impl_drc.rpt",
        "power": output / "impl_power.rpt",
        "analysis": output / "design_analysis.rpt",
        "worst_paths": output / "worst_100_setup_paths.rpt",
    }
    for path in (*files.values(), SELECTED_HLS, SELECTED_VIVADO, SELECTED_UTIL, PARENT):
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ooc = json.loads(OOC_MANIFEST.read_text(encoding="utf-8"))
    selected_hls = json.loads(SELECTED_HLS.read_text(encoding="utf-8"))["csynth"]["metrics"]
    selected_route = json.loads(SELECTED_VIVADO.read_text(encoding="utf-8"))
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    hls = parse_top_xml(files["csynth_top_xml"])
    timing = parse_timing_summary(_read(files["timing"]))
    utilization = parse_fractional_utilization(_read(files["utilization"]))
    selected_util = parse_fractional_utilization(_read(SELECTED_UTIL))
    drc = parse_drc(_read(files["drc"]))
    power = parse_power(_read(files["power"]))
    path = _path_characteristics(_read(files["analysis"]))
    origins = _origins(_read(files["worst_paths"]))
    selected_source = ROOT / manifest["source"]
    derived_source = ROOT / manifest["output"]
    source_pass = (
        manifest.get("selected_source_modified") is False
        and manifest.get("snapshot_write_transform") == {"helpers": 1, "replacements": 1}
        and _sha256(selected_source) == manifest["source_sha256"]
        and _sha256(derived_source) == manifest["output_sha256"]
        and ooc.get("status") == "PASS"
        and _sha256(ROOT / ooc["source"]) == ooc["source_sha256"]
        and _sha256(ROOT / ooc["output"]) == ooc["output_sha256"]
    )
    csim_text = _read(files["csim_report"]) + _read(files["csim_solution_log"])
    exact_pass = (
        "PASS: 64 encoded random-state tokens, exact outputs/counters, and final snapshot" in csim_text
        and "CSim done with 0 errors" in csim_text
    )
    synth_text = _read(files["csynth_solution_log"])
    rtl = HLS_ROOT / "syn/verilog"
    synth_pass = (
        "Finished Command csynth_design" in synth_text
        and "Loop Constraint Status: All loop constraints were satisfied" in synth_text
        and (rtl / "gdn_rs2_top_p_anonymous_namespace_commit_snapshot_block.v").is_file()
        and (rtl / "gdn_rs2_top_p_anonymous_namespace_commit_fold_block.v").is_file()
    )
    impl_text = _read(files["vivado_impl_log"])
    route_pass = (
        "route_design completed successfully" in impl_text
        and "rs2_snapshot_write_unbanked_post_impl.dcp' has been generated" in impl_text
        and "Exiting Vivado" in impl_text
    )

    output.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for label in (
        "derived_source", "generation_manifest", "csim_report", "csim_solution_log",
        "csynth_top_xml", "csynth_top_report", "csynth_impl_report",
        "csynth_solution_log", "ooc_manifest", "vivado_impl_log",
    ):
        source = files[label]
        target = output / f"{label}_{source.name}"
        shutil.copy2(source, target)
        hashes[target.name] = _sha256(target)
    for report in output.glob("*.rpt"):
        hashes[report.name] = _sha256(report)

    classified = sum(origins.values()) == 100
    status = "PASS" if all((source_pass, exact_pass, synth_pass, route_pass, classified, drc["error_count"] == 0, drc["critical_warning_count"] == 0)) else "FAIL"
    parent_timing = parent["postroute"]["experiment_timing"]
    selected_timing = selected_route["target_clock"]["timing"]
    keys = ("wns_ns", "tns_ns", "setup_failing_endpoints")
    decision = (
        "PROMOTION_CANDIDATE_UNBANKED_SNAPSHOT_WRITE"
        if float(timing["wns_ns"]) >= 0 and float(timing["whs_ns"]) >= 0
        else "RETAIN_UNBANKED_SNAPSHOT_WRITE_CLUE"
        if float(timing["wns_ns"]) > float(parent_timing["wns_ns"])
        else "REJECT_UNBANKED_SNAPSHOT_WRITE_TIMING"
    )
    summary: dict[str, object] = {
        "schema": 1,
        "status": status,
        "experiment": "RS2 localized snapshot writes on unbanked fold-write parent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": "isolated architecture experiment; selected kernel unchanged",
        "source_identity": {
            "status": "PASS" if source_pass else "FAIL",
            "selected_source_modified": False,
            "selected_source_sha256": manifest["source_sha256"],
            "parent_output_sha256": manifest["parent_output_sha256"],
            "derived_source_sha256": manifest["output_sha256"],
            "ooc_top_sha256": ooc["output_sha256"],
        },
        "verification": {
            "exact_64_token_csim": "PASS" if exact_pass else "FAIL",
            "csynth": "PASS" if synth_pass else "FAIL",
            "route_completion": "PASS" if route_pass else "FAIL",
            "worst_100_path_classification": "PASS" if classified else "FAIL",
            "target_250mhz": "PASS" if float(timing["wns_ns"]) >= 0 and float(timing["whs_ns"]) >= 0 else "FAIL",
        },
        "hls": {
            "selected": selected_hls,
            "experiment": hls,
            "delta_experiment_minus_selected": {
                **{key: int(hls["resources"][key]) - int(selected_hls["resources"][key]) for key in selected_hls["resources"]},
                "latency_cycles_max": int(hls["latency_cycles_max"]) - int(selected_hls["latency_cycles_max"]),
            },
        },
        "postroute": {
            "selected_timing": selected_timing,
            "fold_write_parent_timing": parent_timing,
            "experiment_timing": timing,
            "delta_experiment_minus_selected": _delta(timing, selected_timing, keys),
            "delta_experiment_minus_fold_write_parent": _delta(timing, parent_timing, keys),
            "experiment_path_characteristics": path,
            "worst_100_startpoint_origins": origins,
            "selected_utilization": selected_util,
            "utilization": utilization,
            "drc": drc,
            "vectorless_power_at_failed_4ns_constraint": power,
        },
        "decision": {"status": decision, "promoted": False},
        "artifact_sha256": dict(sorted(hashes.items())),
    }
    if status != "PASS":
        raise RuntimeError("refusing to archive invalid unbanked snapshot-write evidence")
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        "\n".join([
            "# RS2 unbanked snapshot-write experiment", "",
            "This isolated variant adds snapshot-write locality to the strongest unbanked fold-write parent.", "",
            f"Exact Csim passes. Final WNS is {timing['wns_ns']:.3f} ns, TNS is {timing['tns_ns']:,.3f} ns,",
            f"and {timing['setup_failing_endpoints']:,} setup endpoints fail. Hold is {timing['whs_ns']:+.3f} ns.",
            f"Decision: `{decision}`. Vectorless power at the failed 4 ns target is diagnostic only.", "",
            "## Worst-100 startpoint origins", "", "| Origin | Paths |", "|---|---:|",
            *[f"| `{name}` | {count} |" for name, count in origins.items()], "",
        ]), encoding="utf-8"
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

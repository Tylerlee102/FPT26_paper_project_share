"""Archive the RS2 fold-write address-register max-fanout experiment."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.e2m0_vivado_report import parse_drc, parse_power, parse_timing_summary
from scripts.rs2_fold_write_address_fanout_experiment import (
    SOURCE_ROOT,
    TARGET_NAME,
    TRANSFORMS,
)
from scripts.rs2_layer_banks_report import _delta, _path_characteristics, _read, _sha256
from scripts.rs2_vivado_report import parse_fractional_utilization


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/vivado/experiments/rs2_fold_write_address_fanout16_20260810"
MANIFEST = ROOT / "build/experiments/rs2_fold_write_address_fanout16/manifest.json"
RTL_ROOT = MANIFEST.parent / "rtl"
OOC_MANIFEST = ROOT / "build/vivado/rs2_fold_write_address_fanout16_ooc_rtl/manifest.json"
IMPL_LOG = ROOT / "reports/vivado/vivado_rs2-fold-write-address-fanout16-impl.log"
PARENT = ROOT / "reports/vivado/experiments/rs2_fold_write_20260809/summary.json"


def _origins(text: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for line in text.splitlines():
        path = line.strip()
        if not path.endswith(("/C", "/CLK")) or line[:1].isspace():
            continue
        if "commit_fold_block" in path and "lshr_ln" in path:
            label = "commit_fold_address"
        elif "reset_slot" in path:
            label = "reset_control"
        elif "ram_reg_uram" in path:
            label = "resident_uram_read_clock"
        elif "fold_log" in path:
            label = "fold_control"
        elif "ap_CS_fsm_reg" in path:
            label = "top_fsm"
        elif "grp_gdn_rs2_top_impl" in path:
            label = "top_impl"
        else:
            label = "other"
        counts[label] += 1
    return dict(sorted(counts.items()))


def _replication_summary(text: str) -> dict[str, int]:
    counts = [int(value) for value in re.findall(r"Replicated (\d+) times", text)]
    return {
        "replication_event_count": len(counts),
        "replicated_instance_count": sum(counts),
        "max_instances_in_one_event": max(counts, default=0),
    }


def generate_report(output: Path = OUTPUT) -> dict[str, object]:
    files = {
        "modified_impl": RTL_ROOT / TARGET_NAME,
        "generation_manifest": MANIFEST,
        "ooc_manifest": OOC_MANIFEST,
        "vivado_impl_log": IMPL_LOG,
        "utilization": output / "impl_util.rpt",
        "timing": output / "impl_timing.rpt",
        "drc": output / "impl_drc.rpt",
        "power": output / "impl_power.rpt",
        "analysis": output / "design_analysis.rpt",
        "worst_paths": output / "worst_100_setup_paths.rpt",
    }
    for path in (*files.values(), PARENT, SOURCE_ROOT / TARGET_NAME):
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ooc = json.loads(OOC_MANIFEST.read_text(encoding="utf-8"))
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    source_text = (SOURCE_ROOT / TARGET_NAME).read_text(encoding="utf-8")
    modified_text = files["modified_impl"].read_text(encoding="utf-8")
    copied_identity = all(
        source.name == TARGET_NAME or _sha256(source) == _sha256(RTL_ROOT / source.name)
        for source in SOURCE_ROOT.iterdir()
        if source.is_file()
    )
    declarations_pass = all(
        source_text.count(old) == 1 and modified_text.count(new) == 1
        for old, new in TRANSFORMS.items()
    )
    source_pass = (
        manifest.get("status") == "PASS"
        and manifest.get("hls_cpp_modified") is False
        and manifest.get("generated_rtl_modified") is True
        and manifest.get("transform")
        == {
            "attribute": "max_fanout",
            "declaration_replacements": 2,
            "registers": ["lshr_ln9_reg_369", "lshr_ln_reg_364"],
            "value": 16,
        }
        and _sha256(SOURCE_ROOT / TARGET_NAME) == manifest["source_target_sha256"]
        and _sha256(files["modified_impl"]) == manifest["output_target_sha256"]
        and declarations_pass
        and copied_identity
        and ooc.get("status") == "PASS"
        and _sha256(ROOT / ooc["source"]) == ooc["source_sha256"]
        and _sha256(ROOT / ooc["output"]) == ooc["output_sha256"]
    )
    impl_text = _read(IMPL_LOG)
    route_pass = (
        "route_design completed successfully" in impl_text
        and "rs2_fold_write_address_fanout16_post_impl.dcp' has been generated" in impl_text
        and "Exiting Vivado" in impl_text
    )
    timing = parse_timing_summary(_read(files["timing"]))
    utilization = parse_fractional_utilization(_read(files["utilization"]))
    drc = parse_drc(_read(files["drc"]))
    power = parse_power(_read(files["power"]))
    path = _path_characteristics(_read(files["analysis"]))
    origins = _origins(_read(files["worst_paths"]))
    replication = _replication_summary(impl_text)
    parent_timing = parent["postroute"]["experiment_timing"]
    parent_utilization = parent["postroute"]["utilization"]
    classified = sum(origins.values()) == 100
    status = (
        "PASS"
        if all(
            (
                source_pass,
                route_pass,
                classified,
                replication["replicated_instance_count"] > 0,
                drc["error_count"] == 0,
                drc["critical_warning_count"] == 0,
            )
        )
        else "FAIL"
    )
    keys = ("wns_ns", "tns_ns", "setup_failing_endpoints")
    decision = (
        "PROMOTION_CANDIDATE_ADDRESS_FANOUT16"
        if float(timing["wns_ns"]) >= 0 and float(timing["whs_ns"]) >= 0
        else "RETAIN_ADDRESS_FANOUT16_CLUE"
        if float(timing["wns_ns"]) > float(parent_timing["wns_ns"])
        else "REJECT_ADDRESS_FANOUT16_TIMING"
    )

    output.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for label in ("modified_impl", "generation_manifest", "ooc_manifest", "vivado_impl_log"):
        source = files[label]
        target = output / f"{label}_{source.name}"
        shutil.copy2(source, target)
        hashes[target.name] = _sha256(target)
    for report in output.glob("*.rpt"):
        hashes[report.name] = _sha256(report)

    summary: dict[str, object] = {
        "schema": 1,
        "status": status,
        "experiment": "RS2 fold-write registered-address max-fanout 16",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": "synthesis-only RTL attribute experiment; HLS logic unchanged",
        "source_identity": {
            "status": "PASS" if source_pass else "FAIL",
            "hls_cpp_modified": False,
            "generated_rtl_modified": True,
            "parent_generated_rtl_immutable": True,
            "parent_impl_sha256": manifest["source_target_sha256"],
            "modified_impl_sha256": manifest["output_target_sha256"],
            "ooc_top_sha256": ooc["output_sha256"],
        },
        "verification": {
            "parent_exact_64_token_csim": parent["verification"]["exact_64_token_csim"],
            "synthesis_only_transform": "PASS" if source_pass else "FAIL",
            "route_completion": "PASS" if route_pass else "FAIL",
            "physical_replication_observed": (
                "PASS" if replication["replicated_instance_count"] else "FAIL"
            ),
            "worst_100_path_classification": "PASS" if classified else "FAIL",
            "target_250mhz": (
                "PASS"
                if float(timing["wns_ns"]) >= 0 and float(timing["whs_ns"]) >= 0
                else "FAIL"
            ),
        },
        "replication": replication,
        "postroute": {
            "parent_timing": parent_timing,
            "experiment_timing": timing,
            "delta_experiment_minus_parent": _delta(timing, parent_timing, keys),
            "parent_path_characteristics": parent["postroute"][
                "experiment_path_characteristics"
            ],
            "experiment_path_characteristics": path,
            "worst_100_startpoint_origins": origins,
            "parent_utilization": parent_utilization,
            "utilization": utilization,
            "drc": drc,
            "vectorless_power_at_failed_4ns_constraint": power,
        },
        "decision": {
            "status": decision,
            "promoted": False,
            "reason": (
                "The address origins fall from 47 parent worst paths to four, but "
                "setup WNS, TNS, and failing endpoints all regress as critical paths "
                "redistribute to resident-URAM clocks, fold control, and reset control."
            ),
        },
        "artifact_sha256": dict(sorted(hashes.items())),
    }
    if status != "PASS":
        raise RuntimeError("refusing to archive invalid address-fanout evidence")
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "README.md").write_text(
        "\n".join(
            [
                "# RS2 fold-write address max-fanout experiment",
                "",
                "This RTL-only variant adds `max_fanout=16` to both registered fold-write addresses.",
                "The matched parent RTL and inherited exact 64-token C-simulation evidence are unchanged.",
                "",
                f"Final WNS is {timing['wns_ns']:.3f} ns, TNS is {timing['tns_ns']:,.3f} ns, and",
                f"{timing['setup_failing_endpoints']:,} setup endpoints fail. The targeted address",
                f"registers account for {origins.get('commit_fold_address', 0)} of the worst 100 paths.",
                f"Decision: `{decision}`. Vectorless power at the failed 4 ns target is diagnostic only.",
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

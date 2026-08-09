"""Compute logical state bits and ideal memory-primitive capacity lower bounds."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
PARAMS = ROOT / "hls" / "include" / "gdn_params.hpp"
MX_SUMMARY = ROOT / "reports" / "csynth" / "corrected" / "baseline_csynth_summary.json"
BF16_SUMMARY = ROOT / "reports" / "csynth" / "corrected" / "bf16_hls_summary.json"
MXFP8_SUMMARY = ROOT / "reports" / "csynth" / "corrected" / "mxfp8_hls_summary.json"
BF16_VIVADO = (
    ROOT / "reports" / "vivado" / "baselines" / "bf16" / "bf16_vivado_summary.json"
)
MXFP8_VIVADO = (
    ROOT / "reports" / "vivado" / "baselines" / "mxfp8" / "mxfp8_vivado_summary.json"
)
BF16_XML = (
    ROOT
    / "reports"
    / "csynth"
    / "corrected"
    / "bf16_current"
    / "report"
    / "gdn_bf16_top_csynth.xml"
)
DEFAULT_OUTPUT = ROOT / "reports" / "benchmark" / "corrected"
URAM_BITS = 288 * 1024
BRAM18K_BITS = 18 * 1024


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _parameters() -> dict[str, int]:
    text = PARAMS.read_text(encoding="utf-8")

    def literal(name: str) -> int:
        match = re.search(rf"constexpr int {name}\s*=\s*(\d+)\s*;", text)
        if match is None:
            raise ValueError(f"missing literal parameter: {name}")
        return int(match.group(1))

    def define(name: str) -> int:
        match = re.search(rf"#define {name}\s+(\d+)", text)
        if match is None:
            raise ValueError(f"missing default define: {name}")
        return int(match.group(1))

    return {
        "num_sequences": define("GDN_NUM_SEQUENCES"),
        "num_layers": literal("NUM_LAYERS"),
        "num_value_heads": literal("NUM_VALUE_HEADS"),
        "key_dim": literal("KEY_DIM"),
        "value_dim": literal("VALUE_DIM"),
        "block_size": define("GDN_BLOCK_SIZE"),
    }


def _available_resources(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    available = root.find("./AreaEstimates/AvailableResources")
    if available is None:
        raise ValueError("HLS XML has no device resource capacities")
    return {
        "URAM": int(available.findtext("URAM", "0")),
        "BRAM_18K": int(available.findtext("BRAM_18K", "0")),
    }


def _row(
    name: str,
    elements: int,
    scale_blocks: int,
    num_layers: int,
    element_bits: int,
    scale_bits: int,
    available: dict[str, int],
    reported: dict[str, int] | None,
) -> dict[str, object]:
    mantissa_bits = elements * element_bits
    block_scale_bits = scale_blocks * scale_bits
    logical_bits = mantissa_bits + block_scale_bits
    min_uram = math.ceil(mantissa_bits / URAM_BITS)
    min_bram = math.ceil(block_scale_bits / BRAM18K_BITS)
    return {
        "variant": name,
        "element_bits": element_bits,
        "block_scale_bits": scale_bits,
        "per_layer_logical_state_bits": logical_bits // num_layers,
        "per_layer_logical_state_bytes": math.ceil(
            (logical_bits // num_layers) / 8
        ),
        "logical_state_bits": logical_bits,
        "logical_state_bytes": math.ceil(logical_bits / 8),
        "mantissa_state_bits": mantissa_bits,
        "block_scale_state_bits": block_scale_bits,
        "ideal_min_uram_for_mantissas": min_uram,
        "ideal_min_bram18k_for_scales": min_bram,
        "device_uram": available["URAM"],
        "device_bram18k": available["BRAM_18K"],
        "raw_bit_capacity_necessary_condition": (
            "PASS"
            if min_uram <= available["URAM"] and min_bram <= available["BRAM_18K"]
            else "FAIL"
        ),
        "reported_hls_uram": None if reported is None else reported["URAM"],
        "reported_hls_bram18k": (
            None if reported is None else reported["BRAM_18K"]
        ),
        "reported_hls_counts_cover_ideal_lower_bound": (
            "NOT_RUN"
            if reported is None
            else (
                "PASS"
                if reported["URAM"] >= min_uram and reported["BRAM_18K"] >= min_bram
                else "FAIL"
            )
        ),
        "physical_banked_fit": "NOT_RUN",
    }


def generate_report(
    output: Path,
    mx_summary: Path = MX_SUMMARY,
    bf16_summary: Path = BF16_SUMMARY,
    bf16_xml: Path = BF16_XML,
    mxfp8_summary: Path = MXFP8_SUMMARY,
    bf16_vivado: Path = BF16_VIVADO,
    mxfp8_vivado: Path = MXFP8_VIVADO,
) -> dict[str, object]:
    for path in (PARAMS, mx_summary, bf16_summary, bf16_xml, mxfp8_summary, bf16_vivado):
        if not path.exists():
            raise FileNotFoundError(path)
    params = _parameters()
    available = _available_resources(bf16_xml)
    mx = json.loads(mx_summary.read_text(encoding="utf-8"))
    bf16 = json.loads(bf16_summary.read_text(encoding="utf-8"))
    mxfp8 = json.loads(mxfp8_summary.read_text(encoding="utf-8"))
    bf16_physical = json.loads(bf16_vivado.read_text(encoding="utf-8"))
    mxfp8_physical = (
        json.loads(mxfp8_vivado.read_text(encoding="utf-8"))
        if mxfp8_vivado.exists()
        else None
    )
    if any(payload.get("status") != "PASS" for payload in (mx, bf16, mxfp8, bf16_physical)):
        raise ValueError("HLS summaries must be PASS before capacity reconciliation")
    if mxfp8_physical is not None and mxfp8_physical.get("status") != "PASS":
        raise ValueError("MXFP8 physical extraction must be PASS when present")
    elements = (
        params["num_sequences"]
        * params["num_layers"]
        * params["num_value_heads"]
        * params["key_dim"]
        * params["value_dim"]
    )
    scale_blocks = (
        params["num_sequences"]
        * params["num_layers"]
        * params["num_value_heads"]
        * params["key_dim"]
        * (params["value_dim"] // params["block_size"])
    )
    rows = [
        _row(
            "BF16",
            elements,
            scale_blocks,
            params["num_layers"],
            16,
            0,
            available,
            bf16["csynth"]["metrics"]["resources"],
        ),
        _row(
            "uniform_mxfp4_e2m1_e8m0_b32",
            elements,
            scale_blocks,
            params["num_layers"],
            4,
            8,
            available,
            mx["metrics"]["resources"],
        ),
        _row(
            "mxfp8_e4m3_e8m0_b32",
            elements,
            scale_blocks,
            params["num_layers"],
            8,
            8,
            available,
            mxfp8["csynth"]["metrics"]["resources"],
        ),
        _row(
            "flat_int4",
            elements,
            scale_blocks,
            params["num_layers"],
            4,
            0,
            available,
            None,
        ),
    ]
    if rows[0]["logical_state_bits"] != 301_989_888:
        raise AssertionError("unexpected BF16 logical state size")
    if rows[1]["logical_state_bits"] != 80_216_064:
        raise AssertionError("unexpected MXFP4 logical state size")
    rows[0]["physical_banked_fit"] = bf16_physical["physical_fit"]
    if mxfp8_physical is not None:
        rows[2]["physical_banked_fit"] = mxfp8_physical["physical_fit"]

    physical_fit_by_variant = {
        str(row["variant"]): row["physical_banked_fit"] for row in rows
    }

    source_identity = describe_source_files([PARAMS, Path(__file__).resolve()])
    manifest: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "scope": "logical state capacity and ideal primitive-count lower bounds",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "configuration": params,
        "state_elements": elements,
        "state_scale_blocks": scale_blocks,
        "primitive_capacity_assumptions": {
            "uram_bits": URAM_BITS,
            "bram18k_bits": BRAM18K_BITS,
            "method": "ceil(logical bits / nominal primitive bit capacity), before width, banking, port, cascade, placement, and routing overhead",
        },
        "available_device_resources": available,
        "rows": rows,
        "bf16_all_layer_raw_capacity": rows[0][
            "raw_bit_capacity_necessary_condition"
        ],
        "uniform_mxfp4_all_layer_raw_capacity": rows[1][
            "raw_bit_capacity_necessary_condition"
        ],
        "physical_all_layer_state_bank_fit": "SEE_PHYSICAL_FIT_BY_VARIANT",
        "physical_fit_by_variant": physical_fit_by_variant,
        "raw_input_sha256": {
            _display_path(path): _sha256(path)
            for path in (
                PARAMS,
                mx_summary,
                bf16_summary,
                bf16_xml,
                mxfp8_summary,
                bf16_vivado,
                *((mxfp8_vivado,) if mxfp8_vivado.exists() else ()),
            )
        },
        "limitations": [
            "lower bounds ignore memory width, banking, ports, cascade overhead, floorplanning, and routing",
            "a raw-capacity PASS is necessary but not sufficient for physical fit",
            "HLS totals include non-state memories and therefore cannot be smaller than a valid state-only lower bound",
            "uniform-MXFP4 and flat-INT4 all-layer physical banking remain NOT_RUN",
            "the BF16 URAM-only raw-capacity condition fails, but the controlled full 36-layer layout physically fits by splitting its state banks across URAM and BRAM",
        ],
    }

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "state_capacity_lower_bound.json"
    csv_path = output / "state_capacity_lower_bound.csv"
    md_path = output / "state_capacity_lower_bound.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    md_path.write_text(
        "\n".join(
            [
                "# All-Layer State Capacity Lower Bound",
                "",
                f"Generated: `{manifest['timestamp']}`",
                "Calculation status: `PASS`",
                "Physical fit is reported per variant; BF16 and MXFP8 have routed results while uniform MXFP4 and flat INT4 remain `NOT_RUN`.",
                "",
                f"Declared state: `{params['num_sequences']}` sequence x `{params['num_layers']}` layers x `{params['num_value_heads']}` value heads x `{params['key_dim']}` K x `{params['value_dim']}` V = `{elements}` elements.",
                "",
                "| State format | Bytes/layer | Bytes/36 layers | Ideal min URAM | Ideal min BRAM18K | Raw capacity | HLS covers bound | Physical fit |",
                "|---|---:|---:|---:|---:|---|---|---|",
                *[
                    f"| {row['variant']} | {row['per_layer_logical_state_bytes']} | {row['logical_state_bytes']} | {row['ideal_min_uram_for_mantissas']} | {row['ideal_min_bram18k_for_scales']} | {row['raw_bit_capacity_necessary_condition']} | {row['reported_hls_counts_cover_ideal_lower_bound']} | {row['physical_banked_fit']} |"
                    for row in rows
                ],
                "",
                "The BF16 state alone would require an ideal minimum of 1,024 URAM288",
                f"primitives if stored only in URAM, exceeding the device total of {available['URAM']}.",
                "The routed BF16 implementation instead preserves all 36 logical layers with",
                "29 layers in paired 256-bit URAM banks and seven layers in paired 256-bit BRAM banks.",
                "Uniform MXFP4",
                "requires at least 256 URAM288 for E2M1 elements and 256 BRAM18K for",
                "E8M0 scales, before any implementation overhead.",
                "",
                "HLS memory totals are not used as physical-capacity evidence. The physical-fit",
                "column is populated only from placed and routed all-layer implementations;",
                "variants without one remain NOT_RUN.",
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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    generate_report(_resolve(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

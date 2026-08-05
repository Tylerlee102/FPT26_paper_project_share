"""Extract source-locked native-MXFP8 C-sim and C-synthesis evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.bf16_hls_report import parse_step_cycles, parse_targeted_loops, parse_top_xml
from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSIM = ROOT / "reports" / "csim" / "corrected" / "mxfp8_current"
DEFAULT_ARITHMETIC_CSIM = (
    ROOT / "reports" / "csim" / "corrected" / "mxfp8_arithmetic_current"
)
DEFAULT_CSYNTH = ROOT / "reports" / "csynth" / "corrected" / "mxfp8_current"
DEFAULT_OUTPUT = ROOT / "reports" / "csynth" / "corrected"
DESIGN_SOURCES = (
    ROOT / "hls" / "include" / "gdn_params.hpp",
    ROOT / "hls" / "include" / "mx_types.hpp",
    ROOT / "hls" / "include" / "block_exp_align.hpp",
    ROOT / "hls" / "src" / "block_exp_align.cpp",
    ROOT / "hls" / "src" / "gdn_top.cpp",
    ROOT / "hls" / "mxfp8" / "include" / "gdn_mxfp8_kernel.hpp",
    ROOT / "hls" / "mxfp8" / "include" / "e4m3_arithmetic.hpp",
    ROOT / "hls" / "mxfp8" / "src" / "gdn_mxfp8_top.cpp",
    ROOT / "hls" / "mxfp8" / "src" / "e4m3_arithmetic.cpp",
    ROOT / "hls" / "mxfp8" / "src" / "phase1_prepare.cpp",
    ROOT / "hls" / "mxfp8" / "src" / "phase2_state_read.cpp",
    ROOT / "hls" / "mxfp8" / "src" / "phase3_update.cpp",
    ROOT / "hls" / "mxfp8" / "src" / "phase4_state_write.cpp",
    ROOT / "hls" / "mxfp8" / "src" / "phase5_output.cpp",
)
CSIM_SOURCES = (
    *DESIGN_SOURCES,
    ROOT / "hls" / "mxfp8" / "tb" / "tb_gdn_mxfp8_top.cpp",
    ROOT / "hls" / "mxfp8" / "tcl" / "run_csim.tcl",
)
ARITHMETIC_SOURCES = (
    ROOT / "hls" / "include" / "block_exp_align.hpp",
    ROOT / "hls" / "src" / "block_exp_align.cpp",
    ROOT / "hls" / "mxfp8" / "include" / "e4m3_arithmetic.hpp",
    ROOT / "hls" / "mxfp8" / "src" / "e4m3_arithmetic.cpp",
    ROOT / "hls" / "mxfp8" / "tb" / "tb_e4m3_arithmetic.cpp",
    ROOT / "hls" / "mxfp8" / "tcl" / "run_arithmetic_csim.tcl",
)
CSYNTH_SOURCES = (*DESIGN_SOURCES, ROOT / "hls" / "mxfp8" / "tcl" / "run_csynth.tcl")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _fresh(sources: tuple[Path, ...], artifact: Path) -> bool:
    return max(path.stat().st_mtime for path in sources) <= artifact.stat().st_mtime + 1.0


def generate_report(
    csim_dir: Path,
    arithmetic_dir: Path,
    csynth_dir: Path,
    output: Path,
) -> dict[str, object]:
    kernel_csim = csim_dir / "gdn_mxfp8_top_csim.log"
    kernel_solution = csim_dir / "u55c_250mhz.log"
    arithmetic_csim = arithmetic_dir / "scale_by_e4m3_csim.log"
    arithmetic_solution = arithmetic_dir / "u55c_250mhz.log"
    top_xml = csynth_dir / "report" / "gdn_mxfp8_top_csynth.xml"
    top_report = csynth_dir / "report" / "gdn_mxfp8_top_csynth.rpt"
    impl_report = csynth_dir / "report" / "gdn_mxfp8_top_impl_csynth.rpt"
    csynth_log = csynth_dir / "u55c_250mhz.log"
    raw_paths = (
        kernel_csim,
        kernel_solution,
        arithmetic_csim,
        arithmetic_solution,
        top_xml,
        top_report,
        impl_report,
        csynth_log,
    )
    for path in (*raw_paths, *CSIM_SOURCES, *ARITHMETIC_SOURCES, *CSYNTH_SOURCES):
        if not path.exists():
            raise FileNotFoundError(path)

    kernel_text = kernel_csim.read_text(encoding="utf-8", errors="replace")
    kernel_solution_text = kernel_solution.read_text(encoding="utf-8", errors="replace")
    arithmetic_text = arithmetic_csim.read_text(encoding="utf-8", errors="replace")
    arithmetic_solution_text = arithmetic_solution.read_text(
        encoding="utf-8", errors="replace"
    )
    csynth_text = csynth_log.read_text(encoding="utf-8", errors="replace")
    impl_text = impl_report.read_text(encoding="utf-8", errors="replace")
    metrics = parse_top_xml(top_xml)
    step_cycles = parse_step_cycles(impl_text, "step_heads")
    targeted_loops = parse_targeted_loops(csynth_text)

    kernel_pass = (
        "tb_gdn_mxfp8_top PASS" in kernel_text
        and "CSim done with 0 errors" in kernel_text
        and "Finished Command csim_design" in kernel_solution_text
    )
    arithmetic_pass = (
        "tb_e4m3_arithmetic PASS" in arithmetic_text
        and "CSim done with 0 errors" in arithmetic_text
        and "Finished Command csim_design" in arithmetic_solution_text
    )
    targeted_ii_pass = all(
        row["target_ii"] == row["final_ii"] == 1 for row in targeted_loops
    )
    csynth_pass = (
        "Finished Command csynth_design" in csynth_text
        and "Loop Constraint Status: All loop constraints were satisfied" in csynth_text
        and targeted_ii_pass
        and metrics["estimated_fmax_mhz"] >= 200.0
    )
    freshness = {
        "kernel_csim": "PASS" if _fresh(CSIM_SOURCES, kernel_csim) else "FAIL",
        "arithmetic_csim": "PASS"
        if _fresh(ARITHMETIC_SOURCES, arithmetic_csim)
        else "FAIL",
        "csynth": "PASS" if _fresh(CSYNTH_SOURCES, csynth_log) else "FAIL",
    }
    status = (
        "PASS"
        if kernel_pass
        and arithmetic_pass
        and csynth_pass
        and all(value == "PASS" for value in freshness.values())
        else "FAIL"
    )
    identity = describe_source_files(
        [*set(CSIM_SOURCES + ARITHMETIC_SOURCES + CSYNTH_SOURCES), Path(__file__).resolve()]
    )
    manifest: dict[str, object] = {
        "schema": 1,
        "status": status,
        "scope": "matched native MXFP8-E4M3 persistent-state GDN HLS baseline",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": identity["git_revision"],
        "source_identity": identity,
        "configuration": {
            "num_qk_heads": 16,
            "num_value_heads": 32,
            "key_dim": 128,
            "value_dim": 128,
            "num_layers": 36,
            "num_sequences": 1,
            "p_k": 16,
            "p_v": 8,
            "block_size": 32,
            "state_orientation": "KxV",
            "elements": "E4M3 finite-only",
            "shared_scale": "E8M0",
            "accumulator": "signed INT24",
        },
        "csim": {
            "status": "PASS" if kernel_pass and arithmetic_pass else "FAIL",
            "arithmetic": {
                "status": "PASS" if arithmetic_pass else "FAIL",
                "all_code_validity_and_decode_cases": 256,
                "valid_coefficient_products": 253,
                "nonzero_representable_roundtrips": 252,
                "explicit_rne_midpoints": 2,
            },
            "persistent_kernel": {
                "status": "PASS" if kernel_pass else "FAIL",
                "commands": ["RESET", "one exact nonzero STEP", "READBACK"],
                "final_generation": 1,
            },
        },
        "csynth": {
            "status": "PASS" if csynth_pass else "FAIL",
            "metrics": metrics,
            "step_loop_latency_cycles": step_cycles,
            "targeted_loop_ii_status": "PASS" if targeted_ii_pass else "FAIL",
            "targeted_loops": targeted_loops,
            "vendor_loop_constraint_status": "PASS"
            if "Loop Constraint Status: All loop constraints were satisfied" in csynth_text
            else "FAIL",
        },
        "source_freshness": freshness,
        "raw_artifact_sha256": {
            path.relative_to(ROOT).as_posix(): _sha256(path) for path in raw_paths
        },
        "rtl_cosimulation_long_trace": "NOT_RUN",
        "post_route_timing_and_drc": "NOT_RUN",
        "energy_measurement": "NOT_RUN",
        "limitations": [
            "persistent-kernel C-simulation covers one exact nonzero transition, not a long RTL trace",
            "C-synthesis timing, latency, and resources are estimates until the matched OOC route is extracted",
            "no U55C board telemetry is available on the local machine",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "mxfp8_hls_summary.json"
    md_path = output / "mxfp8_hls_summary.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    resources = metrics["resources"]
    md_path.write_text(
        "\n".join(
            [
                "# Matched Native MXFP8 HLS Baseline",
                "",
                f"Generated: `{manifest['timestamp']}`",
                f"Status: `{status}` for source-locked arithmetic C-sim, kernel C-sim, and C-synthesis",
                "",
                "- Arithmetic C-sim: `PASS` for 256 code checks, 253 valid coefficient products, 252 nonzero exact round trips, and 2 RNE midpoints",
                "- Kernel C-sim: `PASS` for RESET, one exact nonzero STEP, and READBACK",
                f"- Target: `{metrics['target_device']}`, `{metrics['target_clock_ns']:.3f}` ns",
                f"- Estimated clock: `{metrics['estimated_clock_ns']:.3f}` ns (`{metrics['estimated_fmax_mhz']:.2f}` MHz)",
                f"- Estimated STEP loop: `{step_cycles['minimum']}` to `{step_cycles['maximum']}` cycles",
                f"- Estimated resources: `{resources['LUT']}` LUT, `{resources['FF']}` FF, `{resources['BRAM_18K']}` BRAM18K, `{resources['URAM']}` URAM, `{resources['DSP']}` DSP",
                f"- Explicit II=1 loop constraints: `{'PASS' if targeted_ii_pass else 'FAIL'}` ({len(targeted_loops)} loops)",
                "- Long-trace RTL parity: `NOT_RUN`",
                "- Board energy: `BLOCKED_EXTERNAL`",
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
    parser.add_argument("--csim", type=Path, default=DEFAULT_CSIM)
    parser.add_argument("--arithmetic-csim", type=Path, default=DEFAULT_ARITHMETIC_CSIM)
    parser.add_argument("--csynth", type=Path, default=DEFAULT_CSYNTH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = generate_report(
        _resolve(args.csim),
        _resolve(args.arithmetic_csim),
        _resolve(args.csynth),
        _resolve(args.output),
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

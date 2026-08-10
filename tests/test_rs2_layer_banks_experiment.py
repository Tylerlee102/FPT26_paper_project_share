from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.rs2_layer_banks_experiment import SOURCE, generate
from scripts.rs2_layer_banks_report import OUTPUT


def test_generator_partitions_only_primary_and_residual_layers(
    tmp_path: Path,
) -> None:
    output = tmp_path / "gdn_rs2_top.cpp"
    manifest_path = tmp_path / "manifest.json"
    selected_before = hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper()
    result = generate(output, manifest_path)
    text = output.read_text(encoding="utf-8")

    assert result["status"] == "PASS"
    assert result["selected_source_modified"] is False
    assert result["source_sha256"] == selected_before
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() == selected_before
    assert result["insertions"] == [
        "#pragma HLS ARRAY_PARTITION variable=resident_primary complete dim=2",
        "#pragma HLS ARRAY_PARTITION variable=resident_residual complete dim=2",
    ]
    assert text.count("ARRAY_PARTITION variable=resident_primary complete dim=2") == 1
    assert text.count("ARRAY_PARTITION variable=resident_residual complete dim=2") == 1
    assert "ARRAY_PARTITION variable=resident_keys complete dim=2" not in text
    assert "ARRAY_PARTITION variable=resident_updates complete dim=2" not in text


def test_layer_bank_tcl_uses_isolated_projects_and_generated_source() -> None:
    root = Path(__file__).resolve().parents[1]
    csim = (root / "hls/rs2/tcl/run_layer_banks_csim.tcl").read_text()
    csynth = (root / "hls/rs2/tcl/run_layer_banks_csynth.tcl").read_text()

    assert "gdn_rs2_layer_banks_trace_hls" in csim
    assert "gdn_rs2_layer_banks_hls" in csynth
    assert "build/experiments/rs2_layer_banks/gdn_rs2_top.cpp" in csim
    assert "build/experiments/rs2_layer_banks/gdn_rs2_top.cpp" in csynth
    assert "xcu55c-fsvh2892-2L-e" in csim
    assert "xcu55c-fsvh2892-2L-e" in csynth


def test_layer_bank_vivado_flow_is_isolated_and_matched() -> None:
    root = Path(__file__).resolve().parents[1]
    create = (root / "vivado/tcl/create_rs2_layer_banks_project.tcl").read_text()
    impl = (root / "vivado/tcl/run_rs2_layer_banks_impl.tcl").read_text()
    flow = (root / "scripts/vivado_flow.py").read_text()

    assert "gdn_rs2_layer_banks_hls/u55c_250mhz/syn/verilog" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "vivado/constraints/timing.xdc" in create
    assert "vivado/constraints/rs2_ooc.xdc" in create
    assert "reports/vivado/experiments/rs2_layer_banks_20260810" in impl
    assert "ExploreWithRemap" in impl
    assert "ExtraNetDelay_high" in impl
    assert "AggressiveExplore" in impl
    assert "rs2-layer-banks-impl" in flow


def test_archived_layer_bank_route_is_rejected_with_exact_evidence() -> None:
    import json

    summary = json.loads((OUTPUT / "summary.json").read_text())
    assert summary["status"] == "PASS"
    assert summary["verification"]["exact_64_token_csim"] == "PASS"
    assert summary["verification"]["complete_layer_partition"] == "PASS"
    assert summary["verification"]["route_completion"] == "PASS"
    assert summary["verification"]["target_250mhz"] == "FAIL"
    assert summary["decision"]["status"] == "REJECT_LAYER_BANKING_TIMING_AND_COST"
    assert summary["decision"]["promoted"] is False
    assert summary["postroute"]["experiment_timing"]["wns_ns"] == -1.867
    assert summary["postroute"]["experiment_path_characteristics"]["high_fanout"] == 3
    assert summary["postroute"]["delta_experiment_minus_selected"]["wns_ns"] < 0
    assert summary["postroute"]["drc"]["critical_warning_count"] == 0

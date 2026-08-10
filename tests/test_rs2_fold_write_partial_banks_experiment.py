from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.rs2_fold_write_experiment import SOURCE
from scripts.rs2_fold_write_partial_banks_experiment import generate
from scripts.rs2_fold_write_partial_banks_report import OUTPUT


def test_generator_combines_fold_write_and_factor_6_banking(tmp_path: Path) -> None:
    output = tmp_path / "gdn_rs2_top.cpp"
    manifest_path = tmp_path / "manifest.json"
    selected_before = hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper()
    result = generate(output, manifest_path)
    text = output.read_text(encoding="utf-8")

    assert result["status"] == "PASS"
    assert result["source_sha256"] == selected_before
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() == selected_before
    assert result["selected_source_modified"] is False
    assert result["fold_write_transform"] == {
        "fold_control_helpers": 1,
        "fold_control_replacements": 1,
        "fold_write_helpers": 1,
        "fold_write_replacements": 1,
    }
    assert result["partition_factor"] == 6
    assert result["layers_per_bank"] == 6
    assert text.count("void fold_log_if_full(") == 1
    assert text.count("void commit_fold_block(") == 1
    assert text.count("ARRAY_PARTITION variable=resident_primary cyclic factor=6") == 1
    assert text.count("ARRAY_PARTITION variable=resident_residual cyclic factor=6") == 1
    assert not (tmp_path / ".fold_write_manifest.json").exists()


def test_combined_hls_flow_is_isolated_and_registered() -> None:
    root = Path(__file__).resolve().parents[1]
    csim = (root / "hls/rs2/tcl/run_fold_write_partial_banks_csim.tcl").read_text()
    csynth = (
        root / "hls/rs2/tcl/run_fold_write_partial_banks_csynth.tcl"
    ).read_text()
    flow = (root / "scripts/hls_flow.py").read_text()
    makefile = (root / "Makefile").read_text()

    generated = "build/experiments/rs2_fold_write_partial_banks/gdn_rs2_top.cpp"
    assert "gdn_rs2_fold_write_partial_banks_trace_hls" in csim
    assert "gdn_rs2_fold_write_partial_banks_hls" in csynth
    assert generated in csim
    assert generated in csynth
    assert "rs2-fold-write-partial-banks-csim" in flow
    assert "rs2-fold-write-partial-banks-csynth" in flow
    assert "hls-rs2-fold-write-partial-banks-csim" in makefile
    assert "hls-rs2-fold-write-partial-banks-csynth" in makefile


def test_combined_vivado_flow_is_isolated_and_matched() -> None:
    root = Path(__file__).resolve().parents[1]
    create = (
        root / "vivado/tcl/create_rs2_fold_write_partial_banks_project.tcl"
    ).read_text()
    impl = (
        root / "vivado/tcl/run_rs2_fold_write_partial_banks_impl.tcl"
    ).read_text()
    flow = (root / "scripts/vivado_flow.py").read_text()

    assert "gdn_rs2_fold_write_partial_banks_hls/u55c_250mhz/syn/verilog" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "vivado/constraints/timing.xdc" in create
    assert "vivado/constraints/rs2_ooc.xdc" in create
    assert "reports/vivado/experiments/rs2_fold_write_partial_banks_20260810" in impl
    assert "ExploreWithRemap" in impl
    assert "ExtraNetDelay_high" in impl
    assert "AggressiveExplore" in impl
    assert "rs2-fold-write-partial-banks-impl" in flow
    assert "vivado-rs2-fold-write-partial-banks-report" in (
        root / "Makefile"
    ).read_text()


def test_archived_combined_route_is_rejected_with_exact_evidence() -> None:
    import json

    summary = json.loads((OUTPUT / "summary.json").read_text())
    assert summary["status"] == "PASS"
    assert summary["verification"]["exact_64_token_csim"] == "PASS"
    assert summary["verification"]["fold_write_hierarchy"] == "PASS"
    assert summary["verification"]["cyclic_factor_6_layer_partition"] == "PASS"
    assert summary["verification"]["route_completion"] == "PASS"
    assert summary["verification"]["target_250mhz"] == "FAIL"
    assert (
        summary["decision"]["status"]
        == "REJECT_COMBINED_FOLD_WRITE_PARTIAL_BANKS_TIMING"
    )
    assert summary["decision"]["promoted"] is False
    timing = summary["postroute"]["experiment_timing"]
    assert timing["wns_ns"] == -2.757
    assert timing["tns_ns"] == -51999.98
    assert timing["setup_failing_endpoints"] == 53673
    assert timing["whs_ns"] == 0.01
    path = summary["postroute"]["experiment_path_characteristics"]
    assert path["path_delay_ns"] == 6.226
    assert path["net_delay_ns"] == 5.989
    assert path["slr_crossings"] == 2
    assert path["high_fanout"] == 9
    assert summary["postroute"]["delta_experiment_minus_fold_write_only"][
        "wns_ns"
    ] < 0
    assert summary["postroute"]["delta_experiment_minus_partial_banks_only"][
        "wns_ns"
    ] < 0
    assert summary["postroute"]["drc"]["critical_warning_count"] == 0

    root = Path(__file__).resolve().parents[1]
    for source in summary["comparison_sources"].values():
        path = root / source["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == source["sha256"]
    for name, expected in summary["artifact_sha256"].items():
        assert hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest().upper() == expected

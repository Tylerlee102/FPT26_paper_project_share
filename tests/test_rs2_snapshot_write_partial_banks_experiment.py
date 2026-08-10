from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.rs2_fold_write_experiment import SOURCE
from scripts.rs2_snapshot_write_partial_banks_experiment import generate
from scripts.rs2_snapshot_write_partial_banks_report import (
    OUTPUT as ARCHIVE,
    _startpoint_origins,
)


def test_generator_localizes_snapshot_writes_after_parent_transform(
    tmp_path: Path,
) -> None:
    output = tmp_path / "gdn_rs2_top.cpp"
    manifest_path = tmp_path / "manifest.json"
    selected_before = hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper()
    result = generate(output, manifest_path)
    text = output.read_text(encoding="utf-8")

    assert result["status"] == "PASS"
    assert result["source_sha256"] == selected_before
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() == selected_before
    assert result["selected_source_modified"] is False
    assert result["parent_transform"] == {
        "fold_write_transform": {
            "fold_control_helpers": 1,
            "fold_control_replacements": 1,
            "fold_write_helpers": 1,
            "fold_write_replacements": 1,
        },
        "partition_factor": 6,
        "layers_per_bank": 6,
    }
    assert result["snapshot_write_transform"] == {
        "helpers": 1,
        "replacements": 1,
    }
    assert text.count("void commit_snapshot_block(") == 1
    assert text.count("        commit_snapshot_block(\n") == 1
    assert text.count("ARRAY_PARTITION variable=resident_primary cyclic factor=6") == 1
    assert text.count("ARRAY_PARTITION variable=resident_residual cyclic factor=6") == 1
    assert not (tmp_path / ".parent_manifest.json").exists()


def test_snapshot_write_hls_flow_is_isolated_and_registered() -> None:
    root = Path(__file__).resolve().parents[1]
    csim = (
        root / "hls/rs2/tcl/run_snapshot_write_partial_banks_csim.tcl"
    ).read_text()
    csynth = (
        root / "hls/rs2/tcl/run_snapshot_write_partial_banks_csynth.tcl"
    ).read_text()
    flow = (root / "scripts/hls_flow.py").read_text()
    makefile = (root / "Makefile").read_text()

    generated = "build/experiments/rs2_snapshot_write_partial_banks/gdn_rs2_top.cpp"
    assert "gdn_rs2_snapshot_write_partial_banks_trace_hls" in csim
    assert "gdn_rs2_snapshot_write_partial_banks_hls" in csynth
    assert generated in csim
    assert generated in csynth
    assert "rs2-snapshot-write-partial-banks-csim" in flow
    assert "rs2-snapshot-write-partial-banks-csynth" in flow
    assert "hls-rs2-snapshot-write-partial-banks-csim" in makefile
    assert "hls-rs2-snapshot-write-partial-banks-csynth" in makefile


def test_snapshot_write_vivado_flow_is_isolated_and_matched() -> None:
    root = Path(__file__).resolve().parents[1]
    create = (
        root / "vivado/tcl/create_rs2_snapshot_write_partial_banks_project.tcl"
    ).read_text()
    impl = (
        root / "vivado/tcl/run_rs2_snapshot_write_partial_banks_impl.tcl"
    ).read_text()
    flow = (root / "scripts/vivado_flow.py").read_text()
    makefile = (root / "Makefile").read_text()

    assert "gdn_rs2_snapshot_write_partial_banks_hls/u55c_250mhz/syn/verilog" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "vivado/constraints/timing.xdc" in create
    assert "vivado/constraints/rs2_ooc.xdc" in create
    assert "reports/vivado/experiments/rs2_snapshot_write_partial_banks_20260810" in impl
    assert "ExploreWithRemap" in impl
    assert "ExtraNetDelay_high" in impl
    assert "AggressiveExplore" in impl
    assert "rs2-snapshot-write-partial-banks-impl" in flow
    assert "vivado-rs2-snapshot-write-partial-banks-impl" in makefile
    assert "vivado-rs2-snapshot-write-partial-banks-report" in makefile


def test_startpoint_origin_classifier_accounts_for_all_paths() -> None:
    text = "\n".join(
        [
            "grp_p_anonymous_namespace_commit_snapshot_block_fu_1/state_reg/C",
            "grp_p_anonymous_namespace_load_snapshot_fu_2/state_reg/C",
            "gmem5_m_axi_U/full_n_reg/C",
            "grp_p_anonymous_namespace_dot_base_column_fu_3/reg/C",
            "grp_p_anonymous_namespace_fold_log_if_full_fu_4/reg/C",
            "grp_p_anonymous_namespace_read_snapshot_fu_5/ram_reg/CLK",
            "grp_p_anonymous_namespace_reset_slot_fu_5/state_reg/C",
            "grp_gdn_rs2_top_impl_fu_5/trunc_ln1150_reg_1/C",
            "grp_gdn_rs2_top_impl_fu_5/ram_reg_uram_1/CLK",
            "grp_gdn_rs2_top_impl_fu_5/ap_CS_fsm_reg[2]/C",
            "grp_gdn_rs2_top_impl_fu_5/reg/C",
            "unclassified/reg/C",
            "  endpoint/D",
        ]
    )

    assert _startpoint_origins(text) == {
        "commit_snapshot_block": 1,
        "dot_base": 1,
        "fold": 1,
        "gmem5_axi_backpressure": 1,
        "load_snapshot": 1,
        "layer_address_control": 1,
        "other": 1,
        "read_snapshot": 1,
        "reset_slot": 1,
        "resident_uram_read_clock": 1,
        "top_fsm": 1,
        "top_impl": 1,
    }


def test_snapshot_write_archive_is_complete_and_source_is_immutable() -> None:
    summary_path = ARCHIVE / "summary.json"
    import json

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["source_identity"]["status"] == "PASS"
    assert summary["source_identity"]["selected_source_modified"] is False
    assert summary["verification"]["exact_64_token_csim"] == "PASS"
    assert summary["verification"]["csynth"] == "PASS"
    assert summary["verification"]["route_completion"] == "PASS"
    assert summary["verification"]["worst_100_path_classification"] == "PASS"
    assert summary["postroute"]["drc"]["critical_warning_count"] == 0
    assert summary["postroute"]["drc"]["error_count"] == 0
    assert sum(summary["postroute"]["worst_100_startpoint_origins"].values()) == 100
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() == (
        "87D9D80BD8C2EB1DA665D195EADF0536FEE455F4E246B61BD2ABD3523382647E"
    )

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.rs2_fold_write_experiment import SOURCE
from scripts.rs2_split_fold_write_experiment import generate
from scripts.rs2_split_fold_write_report import (
    OUTPUT as ARCHIVE,
    _startpoint_origins,
)


def test_generator_splits_fold_commits_after_parent_transform(tmp_path: Path) -> None:
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
        "fold_control_helpers": 1,
        "fold_control_replacements": 1,
        "fold_write_helpers": 1,
        "fold_write_replacements": 1,
    }
    assert result["split_write_transform"] == {
        "combined_helpers_remaining": 0,
        "primary_calls": 1,
        "primary_helpers": 1,
        "residual_calls": 1,
        "residual_helpers": 1,
    }
    assert "void commit_fold_block(" not in text
    assert text.count("void commit_primary_fold_block(") == 1
    assert text.count("void commit_residual_fold_block(") == 1
    assert not (tmp_path / ".parent_manifest.json").exists()


def test_split_fold_write_hls_flow_is_isolated_and_registered() -> None:
    root = Path(__file__).resolve().parents[1]
    csim = (root / "hls/rs2/tcl/run_split_fold_write_csim.tcl").read_text()
    csynth = (root / "hls/rs2/tcl/run_split_fold_write_csynth.tcl").read_text()
    flow = (root / "scripts/hls_flow.py").read_text()
    makefile = (root / "Makefile").read_text()

    generated = "build/experiments/rs2_split_fold_write/gdn_rs2_top.cpp"
    assert "gdn_rs2_split_fold_write_trace_hls" in csim
    assert "gdn_rs2_split_fold_write_hls" in csynth
    assert generated in csim
    assert generated in csynth
    assert "rs2-split-fold-write-csim" in flow
    assert "rs2-split-fold-write-csynth" in flow
    assert "hls-rs2-split-fold-write-csim" in makefile
    assert "hls-rs2-split-fold-write-csynth" in makefile


def test_split_fold_write_vivado_flow_is_isolated_and_matched() -> None:
    root = Path(__file__).resolve().parents[1]
    create = (root / "vivado/tcl/create_rs2_split_fold_write_project.tcl").read_text()
    impl = (root / "vivado/tcl/run_rs2_split_fold_write_impl.tcl").read_text()
    flow = (root / "scripts/vivado_flow.py").read_text()
    makefile = (root / "Makefile").read_text()

    assert "gdn_rs2_split_fold_write_hls/u55c_250mhz/syn/verilog" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "vivado/constraints/timing.xdc" in create
    assert "vivado/constraints/rs2_ooc.xdc" in create
    assert "reports/vivado/experiments/rs2_split_fold_write_20260810" in impl
    assert "ExploreWithRemap" in impl
    assert "ExtraNetDelay_high" in impl
    assert "AggressiveExplore" in impl
    assert "rs2-split-fold-write-impl" in flow
    assert "vivado-rs2-split-fold-write-impl" in makefile
    assert "vivado-rs2-split-fold-write-report" in makefile


def test_startpoint_origin_classifier_accounts_for_all_paths() -> None:
    text = "\n".join(
        [
            "grp_commit_primary_fold_block_fu_1/state_reg/C",
            "grp_commit_residual_fold_block_fu_2/state_reg/C",
            "grp_commit_fold_block_fu_3/state_reg/C",
            "grp_load_snapshot_fu_4/state_reg/C",
            "grp_read_snapshot_fu_5/ram_reg/CLK",
            "grp_reset_slot_fu_6/state_reg/C",
            "grp_gdn_rs2_top_impl_fu_7/trunc_ln1150_reg/C",
            "grp_gdn_rs2_top_impl_fu_8/ram_reg_uram/CLK",
            "grp_dot_base_column_fu_9/state_reg/C",
            "grp_fold_log_if_full_fu_10/state_reg/C",
            "grp_gdn_rs2_top_impl_fu_11/ap_CS_fsm_reg[2]/C",
            "grp_gdn_rs2_top_impl_fu_12/state_reg/C",
            "unclassified/state_reg/C",
            "  endpoint/D",
        ]
    )

    assert _startpoint_origins(text) == {
        "combined_commit_fold_block": 1,
        "commit_primary_fold_block": 1,
        "commit_residual_fold_block": 1,
        "dot_base": 1,
        "fold": 1,
        "layer_address_control": 1,
        "load_snapshot": 1,
        "other": 1,
        "read_snapshot": 1,
        "reset_slot": 1,
        "resident_uram_read_clock": 1,
        "top_fsm": 1,
        "top_impl": 1,
    }


def test_split_fold_write_archive_is_complete_and_source_is_immutable() -> None:
    import json

    summary = json.loads((ARCHIVE / "summary.json").read_text(encoding="utf-8"))
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

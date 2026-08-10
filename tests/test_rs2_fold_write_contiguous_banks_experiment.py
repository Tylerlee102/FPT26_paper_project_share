from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.rs2_fold_write_contiguous_banks_experiment import generate
from scripts.rs2_fold_write_contiguous_banks_report import (
    OUTPUT as ARCHIVE,
    _origins,
)
from scripts.rs2_fold_write_experiment import SOURCE


def test_generator_adds_two_contiguous_banks_to_fold_write_parent(
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
        "fold_control_helpers": 1,
        "fold_control_replacements": 1,
        "fold_write_helpers": 1,
        "fold_write_replacements": 1,
    }
    assert result["partition_factor"] == 2
    assert result["partition_style"] == "block"
    assert result["layers_per_bank"] == 18
    assert text.count("block factor=2 dim=2") == 2
    assert "cyclic factor=6 dim=2" not in text
    assert not (tmp_path / ".fold_write_manifest.json").exists()


def test_contiguous_bank_hls_flow_is_isolated_and_registered() -> None:
    root = Path(__file__).resolve().parents[1]
    csim = (root / "hls/rs2/tcl/run_fold_write_contiguous_banks_csim.tcl").read_text()
    csynth = (
        root / "hls/rs2/tcl/run_fold_write_contiguous_banks_csynth.tcl"
    ).read_text()
    flow = (root / "scripts/hls_flow.py").read_text()
    makefile = (root / "Makefile").read_text()

    generated = "build/experiments/rs2_fold_write_contiguous_banks/gdn_rs2_top.cpp"
    assert "gdn_rs2_fold_write_contiguous_banks_trace_hls" in csim
    assert "gdn_rs2_fold_write_contiguous_banks_hls" in csynth
    assert generated in csim
    assert generated in csynth
    assert "rs2-fold-write-contiguous-banks-csim" in flow
    assert "rs2-fold-write-contiguous-banks-csynth" in flow
    assert "hls-rs2-fold-write-contiguous-banks-csim" in makefile
    assert "hls-rs2-fold-write-contiguous-banks-csynth" in makefile


def test_contiguous_bank_vivado_flow_is_isolated_and_matched() -> None:
    root = Path(__file__).resolve().parents[1]
    create = (
        root / "vivado/tcl/create_rs2_fold_write_contiguous_banks_project.tcl"
    ).read_text()
    impl = (
        root / "vivado/tcl/run_rs2_fold_write_contiguous_banks_impl.tcl"
    ).read_text()
    flow = (root / "scripts/vivado_flow.py").read_text()
    makefile = (root / "Makefile").read_text()

    assert "gdn_rs2_fold_write_contiguous_banks_hls/u55c_250mhz/syn/verilog" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "vivado/constraints/timing.xdc" in create
    assert "vivado/constraints/rs2_ooc.xdc" in create
    assert "reports/vivado/experiments/rs2_fold_write_contiguous_banks_20260810" in impl
    assert "ExploreWithRemap" in impl
    assert "ExtraNetDelay_high" in impl
    assert "AggressiveExplore" in impl
    assert "rs2-fold-write-contiguous-banks-impl" in flow
    assert "vivado-rs2-fold-write-contiguous-banks-impl" in makefile
    assert "vivado-rs2-fold-write-contiguous-banks-report" in makefile


def test_startpoint_origin_classifier_accounts_for_all_paths() -> None:
    text = "\n".join(
        [
            "gmem4_m_axi_U/load_unit_0/full_n_reg/C",
            "grp_load_snapshot_fu_1/state_reg/C",
            "grp_read_snapshot_fu_2/state_reg/C",
            "grp_reset_slot_fu_3/state_reg/C",
            "resident_primary_U/ram_reg_uram_1/CLK",
            "grp_commit_fold_block_fu_4/state_reg/C",
            "grp_fold_log_if_full_fu_5/state_reg/C",
            "grp_gdn_rs2_top_impl_fu_6/ap_CS_fsm_reg[2]/C",
            "grp_gdn_rs2_top_impl_fu_7/state_reg/C",
            "unclassified/state_reg/C",
            "  endpoint/D",
        ]
    )

    assert _origins(text) == {
        "commit_fold_block": 1,
        "fold": 1,
        "gmem4_state_input_load_fifo": 1,
        "load_snapshot": 1,
        "other": 1,
        "read_snapshot": 1,
        "reset_slot": 1,
        "resident_uram_read_clock": 1,
        "top_fsm": 1,
        "top_impl": 1,
    }


def test_contiguous_bank_archive_is_complete_and_source_is_immutable() -> None:
    import json

    summary = json.loads((ARCHIVE / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["source_identity"]["status"] == "PASS"
    assert summary["source_identity"]["selected_source_modified"] is False
    assert summary["verification"]["exact_64_token_csim"] == "PASS"
    assert summary["verification"]["csynth"] == "PASS"
    assert summary["verification"]["route_completion"] == "PASS"
    assert summary["verification"]["worst_100_path_classification"] == "PASS"
    assert summary["verification"]["target_250mhz"] == "FAIL"
    assert summary["decision"]["status"] == "REJECT_CONTIGUOUS_BANKING_TIMING"
    assert summary["postroute"]["drc"]["critical_warning_count"] == 0
    assert summary["postroute"]["drc"]["error_count"] == 0
    assert sum(summary["postroute"]["worst_100_startpoint_origins"].values()) == 100
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() == (
        "87D9D80BD8C2EB1DA665D195EADF0536FEE455F4E246B61BD2ABD3523382647E"
    )

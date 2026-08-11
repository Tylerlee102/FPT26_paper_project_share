from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.rs2_fold_write_address_fanout_experiment import (
    SOURCE_ROOT,
    TARGET_NAME,
    TRANSFORMS,
    generate,
)
from scripts.rs2_fold_write_address_fanout_report import OUTPUT as ARCHIVE, _origins


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_generator_changes_only_fold_write_address_attributes(tmp_path: Path) -> None:
    output = tmp_path / "rtl"
    manifest_path = tmp_path / "manifest.json"
    result = generate(output, manifest_path)

    assert result["status"] == "PASS"
    assert result["hls_cpp_modified"] is False
    assert result["generated_rtl_modified"] is True
    assert result["transform"]["declaration_replacements"] == 2
    assert result["source_target_sha256"] == _sha256(SOURCE_ROOT / TARGET_NAME)
    source_text = (SOURCE_ROOT / TARGET_NAME).read_text(encoding="utf-8")
    output_text = (output / TARGET_NAME).read_text(encoding="utf-8")
    for old, new in TRANSFORMS.items():
        assert source_text.count(old) == 1
        assert output_text.count(new) == 1
    for source in SOURCE_ROOT.iterdir():
        if source.name == TARGET_NAME:
            continue
        assert _sha256(source) == _sha256(output / source.name)


def test_fold_write_address_fanout_vivado_flow_is_isolated_and_registered() -> None:
    root = Path(__file__).resolve().parents[1]
    create = (
        root / "vivado/tcl/create_rs2_fold_write_address_fanout_project.tcl"
    ).read_text()
    impl = (
        root / "vivado/tcl/run_rs2_fold_write_address_fanout_impl.tcl"
    ).read_text()
    flow = (root / "scripts/vivado_flow.py").read_text()
    makefile = (root / "Makefile").read_text()

    assert "build/experiments/rs2_fold_write_address_fanout16/rtl" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "vivado/constraints/timing.xdc" in create
    assert "vivado/constraints/rs2_ooc.xdc" in create
    assert "rs2_fold_write_address_fanout16_20260810" in impl
    assert "ExploreWithRemap" in impl
    assert "ExtraNetDelay_high" in impl
    assert "AggressiveExplore" in impl
    assert "rs2-fold-write-address-fanout16-impl" in flow
    assert "vivado-rs2-fold-write-address-fanout16-impl" in makefile
    assert "vivado-rs2-fold-write-address-fanout16-report" in makefile


def test_startpoint_origin_classifier_accounts_for_all_paths() -> None:
    text = "\n".join(
        [
            "grp_commit_fold_block_fu_1/lshr_ln9_reg_369_reg[2]/C",
            "grp_reset_slot_fu_2/state_reg/C",
            "resident_primary_U/ram_reg_uram_3/CLK",
            "grp_fold_log_if_full_fu_4/state_reg/C",
            "grp_gdn_rs2_top_impl_fu_5/ap_CS_fsm_reg[2]/C",
            "grp_gdn_rs2_top_impl_fu_6/state_reg/C",
            "unclassified/state_reg/C",
            "  endpoint/D",
        ]
    )

    assert _origins(text) == {
        "commit_fold_address": 1,
        "fold_control": 1,
        "other": 1,
        "reset_control": 1,
        "resident_uram_read_clock": 1,
        "top_fsm": 1,
        "top_impl": 1,
    }


def test_address_fanout_archive_is_complete_and_parent_source_is_immutable() -> None:
    import json

    summary = json.loads((ARCHIVE / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["source_identity"]["status"] == "PASS"
    assert summary["source_identity"]["hls_cpp_modified"] is False
    assert summary["source_identity"]["generated_rtl_modified"] is True
    assert summary["source_identity"]["parent_generated_rtl_immutable"] is True
    assert summary["verification"]["parent_exact_64_token_csim"] == "PASS"
    assert summary["verification"]["synthesis_only_transform"] == "PASS"
    assert summary["verification"]["route_completion"] == "PASS"
    assert summary["verification"]["physical_replication_observed"] == "PASS"
    assert summary["verification"]["worst_100_path_classification"] == "PASS"
    assert summary["verification"]["target_250mhz"] == "FAIL"
    assert summary["decision"]["status"] == "REJECT_ADDRESS_FANOUT16_TIMING"
    assert summary["postroute"]["drc"]["critical_warning_count"] == 0
    assert summary["postroute"]["drc"]["error_count"] == 0
    assert sum(summary["postroute"]["worst_100_startpoint_origins"].values()) == 100
    assert summary["postroute"]["worst_100_startpoint_origins"]["commit_fold_address"] == 4
    assert _sha256(SOURCE_ROOT / TARGET_NAME) == (
        "CC8724C06A2A369D30055E43DE6FA2EA8CB2B200DA385674EC81AB0175D8E5FF"
    )

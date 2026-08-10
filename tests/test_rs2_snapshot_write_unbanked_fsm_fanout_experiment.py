from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.rs2_snapshot_write_unbanked_fsm_fanout_experiment import (
    NEW_DECLARATION,
    OLD_DECLARATION,
    SOURCE_ROOT,
    TARGET_NAME,
    generate,
)
from scripts.rs2_snapshot_write_unbanked_fsm_fanout_report import (
    OUTPUT as ARCHIVE,
    _origins,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_generator_changes_only_the_top_fsm_synthesis_attribute(tmp_path: Path) -> None:
    output = tmp_path / "rtl"
    manifest_path = tmp_path / "manifest.json"
    result = generate(output, manifest_path)

    assert result["status"] == "PASS"
    assert result["hls_cpp_modified"] is False
    assert result["generated_rtl_modified"] is True
    assert result["transform"] == {
        "attribute": "max_fanout",
        "value": 16,
        "declaration_replacements": 1,
    }
    assert result["source_impl_sha256"] == _sha256(SOURCE_ROOT / TARGET_NAME)
    assert OLD_DECLARATION in (SOURCE_ROOT / TARGET_NAME).read_text(encoding="utf-8")
    assert NEW_DECLARATION in (output / TARGET_NAME).read_text(encoding="utf-8")
    for source in SOURCE_ROOT.iterdir():
        if source.name == TARGET_NAME:
            continue
        assert _sha256(source) == _sha256(output / source.name)


def test_max_fanout_vivado_flow_is_isolated_and_registered() -> None:
    root = Path(__file__).resolve().parents[1]
    create = (
        root / "vivado/tcl/create_rs2_snapshot_write_unbanked_fsm_fanout_project.tcl"
    ).read_text()
    impl = (
        root / "vivado/tcl/run_rs2_snapshot_write_unbanked_fsm_fanout_impl.tcl"
    ).read_text()
    flow = (root / "scripts/vivado_flow.py").read_text()
    makefile = (root / "Makefile").read_text()

    assert "build/experiments/rs2_snapshot_write_unbanked_fsm_fanout16/rtl" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "vivado/constraints/timing.xdc" in create
    assert "vivado/constraints/rs2_ooc.xdc" in create
    assert "rs2_snapshot_write_unbanked_fsm_fanout16_20260810" in impl
    assert "ExploreWithRemap" in impl
    assert "ExtraNetDelay_high" in impl
    assert "AggressiveExplore" in impl
    assert "rs2-snapshot-write-unbanked-fsm-fanout16-impl" in flow
    assert "vivado-rs2-snapshot-write-unbanked-fsm-fanout16-impl" in makefile
    assert "vivado-rs2-snapshot-write-unbanked-fsm-fanout16-report" in makefile


def test_startpoint_origin_classifier_accounts_for_all_paths() -> None:
    text = "\n".join(
        [
            "grp_commit_snapshot_block_fu_1/state_reg/C",
            "grp_load_snapshot_fu_2/state_reg/C",
            "grp_read_snapshot_fu_3/state_reg/C",
            "grp_reset_slot_fu_4/state_reg/C",
            "resident_primary_U/ram_reg_uram_1/CLK",
            "grp_commit_fold_block_fu_5/state_reg/C",
            "grp_fold_log_if_full_fu_6/state_reg/C",
            "grp_gdn_rs2_top_impl_fu_7/ap_CS_fsm_reg[2]/C",
            "grp_gdn_rs2_top_impl_fu_8/state_reg/C",
            "unclassified/state_reg/C",
            "  endpoint/D",
        ]
    )

    assert _origins(text) == {
        "commit_fold_block": 1,
        "commit_snapshot_block": 1,
        "fold": 1,
        "load_snapshot": 1,
        "other": 1,
        "read_snapshot": 1,
        "reset_slot": 1,
        "resident_uram_read_clock": 1,
        "top_fsm": 1,
        "top_impl": 1,
    }


def test_max_fanout_archive_is_complete_and_parent_source_is_immutable() -> None:
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
    assert summary["verification"]["replication_observed"] == "PASS"
    assert summary["verification"]["worst_100_path_classification"] == "PASS"
    assert summary["verification"]["target_250mhz"] == "FAIL"
    assert summary["decision"]["status"] == "REJECT_FSM_FANOUT16_TIMING"
    assert summary["postroute"]["drc"]["critical_warning_count"] == 0
    assert summary["postroute"]["drc"]["error_count"] == 0
    assert sum(summary["postroute"]["worst_100_startpoint_origins"].values()) == 100
    assert _sha256(SOURCE_ROOT / TARGET_NAME) == (
        "9F36AC91B9DEE21D906996960A13D8A1C0F6193C96C9C5C0E63B7CACA1DE1C5A"
    )

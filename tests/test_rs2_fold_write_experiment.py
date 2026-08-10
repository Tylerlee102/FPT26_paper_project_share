from __future__ import annotations

from pathlib import Path

from scripts.rs2_fold_write_experiment import generate
from scripts.rs2_fold_write_report import OUTPUT


def test_generator_localizes_fold_control_and_state_writes(tmp_path: Path) -> None:
    output = tmp_path / "gdn_rs2_top.cpp"
    manifest_path = tmp_path / "manifest.json"
    result = generate(output, manifest_path)
    text = output.read_text(encoding="utf-8")

    assert result["status"] == "PASS"
    assert result["selected_source_modified"] is False
    assert result["transform"] == {
        "fold_control_helpers": 1,
        "fold_control_replacements": 1,
        "fold_write_helpers": 1,
        "fold_write_replacements": 1,
    }
    assert text.count("void fold_log_if_full(") == 1
    assert text.count("void commit_fold_block(") == 1
    assert text.count("  commit_fold_block(\n") == 1
    assert "if (old_live + 1 == LOG_CAPACITY)" not in text


def test_fold_write_tcl_uses_isolated_projects_and_generated_source() -> None:
    root = Path(__file__).resolve().parents[1]
    csim = (root / "hls/rs2/tcl/run_fold_write_csim.tcl").read_text()
    csynth = (root / "hls/rs2/tcl/run_fold_write_csynth.tcl").read_text()

    assert "gdn_rs2_fold_write_trace_hls" in csim
    assert "gdn_rs2_fold_write_hls" in csynth
    assert "build/experiments/rs2_fold_write/gdn_rs2_top.cpp" in csim
    assert "build/experiments/rs2_fold_write/gdn_rs2_top.cpp" in csynth


def test_fold_write_vivado_flow_is_isolated_and_matched() -> None:
    root = Path(__file__).resolve().parents[1]
    create = (root / "vivado/tcl/create_rs2_fold_write_project.tcl").read_text()
    impl = (root / "vivado/tcl/run_rs2_fold_write_impl.tcl").read_text()
    flow = (root / "scripts/vivado_flow.py").read_text()

    assert "gdn_rs2_fold_write_hls/u55c_250mhz/syn/verilog" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "vivado/constraints/timing.xdc" in create
    assert "vivado/constraints/rs2_ooc.xdc" in create
    assert "reports/vivado/experiments/rs2_fold_write_20260809" in impl
    assert "ExploreWithRemap" in impl
    assert "ExtraNetDelay_high" in impl
    assert "AggressiveExplore" in impl
    assert "rs2-fold-write-impl" in flow


def test_archived_fold_write_route_is_best_but_not_promoted() -> None:
    import hashlib
    import json

    summary = json.loads((OUTPUT / "summary.json").read_text())
    assert summary["status"] == "PASS"
    assert summary["verification"]["exact_64_token_csim"] == "PASS"
    assert summary["verification"]["csynth"] == "PASS"
    assert summary["verification"]["route_completion"] == "PASS"
    assert summary["verification"]["target_250mhz"] == "FAIL"
    assert summary["decision"]["status"] == "BEST_ISOLATED_TIMING_REJECT_250MHZ"
    assert summary["decision"]["promoted"] is False
    assert summary["postroute"]["experiment_timing"]["wns_ns"] == -1.294
    assert summary["postroute"]["delta_experiment_minus_selected"]["wns_ns"] > 0
    assert summary["postroute"]["delta_experiment_minus_prior"]["wns_ns"] > 0
    assert summary["postroute"]["experiment_path_characteristics"]["high_fanout"] == 307

    for name, expected in summary["artifact_sha256"].items():
        observed = hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest().upper()
        assert observed == expected

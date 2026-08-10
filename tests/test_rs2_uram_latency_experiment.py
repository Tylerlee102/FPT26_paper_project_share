from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.rs2_uram_latency_experiment import URAM_VARIABLES, generate
from scripts.rs2_uram_latency_report import DEFAULT_OUTPUT


def test_generator_changes_only_registered_uram_bindings(tmp_path: Path) -> None:
    output = tmp_path / "gdn_rs2_top.cpp"
    manifest_path = tmp_path / "manifest.json"
    result = generate(output, manifest_path)
    text = output.read_text(encoding="utf-8")

    assert result["status"] == "PASS"
    assert result["selected_source_modified"] is False
    assert len(result["replacements"]) == len(URAM_VARIABLES)
    for variable in URAM_VARIABLES:
        assert (
            f"#pragma HLS BIND_STORAGE variable={variable} "
            "type=ram_t2p impl=uram latency=2"
        ) in text
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "PASS"


def test_experiment_tcl_uses_isolated_project_and_generated_source() -> None:
    root = Path(__file__).resolve().parents[1]
    csim = (root / "hls/rs2/tcl/run_uram_latency2_csim.tcl").read_text()
    csynth = (root / "hls/rs2/tcl/run_uram_latency2_csynth.tcl").read_text()

    assert "gdn_rs2_uram_latency2_trace_hls" in csim
    assert "gdn_rs2_uram_latency2_hls" in csynth
    assert "build/experiments/rs2_uram_latency2/gdn_rs2_top.cpp" in csim
    assert "build/experiments/rs2_uram_latency2/gdn_rs2_top.cpp" in csynth


def test_archived_experiment_is_exact_and_not_promoted() -> None:
    summary = json.loads((DEFAULT_OUTPUT / "summary.json").read_text())
    assert summary["status"] == "PASS"
    assert summary["verification"]["exact_64_token_csim"] == "PASS"
    assert summary["verification"]["csynth"] == "PASS"
    assert summary["verification"]["explicit_loop_constraints"] == "PASS"
    assert summary["verification"]["route"] == "NOT_RUN"
    assert summary["decision"]["status"] == "REJECT_BEFORE_ROUTE"
    assert summary["decision"]["promoted"] is False
    assert summary["source_identity"]["selected_source_modified"] is False
    assert summary["delta_experiment_minus_selected"]["FF"] == 1145
    assert summary["delta_experiment_minus_selected"]["LUT"] == 72
    assert summary["delta_experiment_minus_selected"]["latency_cycles_max"] == 20480
    assert summary["physical_path_evidence"]["reported_paths"] == 100
    assert summary["physical_path_evidence"]["resident_residual_mentions"] == 94

    for name, expected in summary["artifact_sha256"].items():
        observed = hashlib.sha256((DEFAULT_OUTPUT / name).read_bytes()).hexdigest().upper()
        assert observed == expected

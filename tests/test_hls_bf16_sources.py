from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bf16_baseline_keeps_controlled_boundary_and_dataflow() -> None:
    header = (ROOT / "hls/bf16/include/gdn_bf16_kernel.hpp").read_text(
        encoding="utf-8"
    )
    source = (ROOT / "hls/bf16/src/gdn_bf16_top.cpp").read_text(
        encoding="utf-8"
    )
    assert "ap_float_bf16" in header
    assert "ap_float_single" in header
    assert "state_tensor_t" in header
    assert "phase1_validate_token" in source
    assert "phase2_decay_predict_tile" in source
    assert "phase3_delta_tile" in source
    assert "phase4_update_state_tile" in source
    assert "phase5_output_tile" in source
    assert "constexpr int URAM_LAYER_COUNT = 29" in source
    assert "constexpr int BRAM_LAYER_COUNT = gdn::NUM_LAYERS - URAM_LAYER_COUNT" in source
    assert "resident_state_uram_lower" in source
    assert "resident_state_uram_upper" in source
    assert "resident_state_bram_lower" in source
    assert "resident_state_bram_upper" in source
    assert "BIND_STORAGE variable=resident_state_uram_lower type=ram_t2p impl=uram" in source
    assert "BIND_STORAGE variable=resident_state_bram_lower type=ram_t2p impl=bram" in source
    assert "join_state_halves" in source
    assert "qk_head = head / (gdn::NUM_VALUE_HEADS / gdn::NUM_QK_HEADS)" in source


def test_bf16_baseline_has_bounded_csim_and_csynth_entrypoints() -> None:
    csim = (ROOT / "hls/bf16/tcl/run_csim.tcl").read_text(encoding="utf-8")
    csynth = (ROOT / "hls/bf16/tcl/run_csynth.tcl").read_text(encoding="utf-8")
    testbench = (ROOT / "hls/bf16/tb/tb_gdn_bf16_top.cpp").read_text(
        encoding="utf-8"
    )
    assert "csim_design -clean" in csim
    assert "csynth_design" in csynth
    assert "xcu55c-fsvh2892-2L-e" in csim
    assert "create_clock -period 4.0" in csynth
    assert "BF16_HLS_CSIM PASS" in testbench
    assert "commands=6 bank_classes=2" in testbench
    assert "gdn::NUM_LAYERS - 1" in testbench

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_rs2_is_native_two_term_mxfp4_with_r3_log() -> None:
    header = (ROOT / "hls/rs2/include/gdn_rs2_kernel.hpp").read_text(
        encoding="utf-8"
    )
    top = (ROOT / "hls/rs2/src/gdn_rs2_top.cpp").read_text(encoding="utf-8")
    arithmetic = (ROOT / "hls/rs2/src/rs2_arithmetic.cpp").read_text(
        encoding="utf-8"
    )
    assert "constexpr int LOG_CAPACITY = 3" in header
    assert "constexpr int STACK_DEPTH = 2" in header
    assert "using state_primary_word_t = ap_uint<4 * gdn::BLOCK_SIZE>" in header
    assert "using state_residual_word_t = ap_uint<4 * gdn::BLOCK_SIZE>" in header
    assert "using e2m0_t" not in header + top + arithmetic
    assert "quantize_e2m0" not in top + arithmetic
    assert "product_e2m1" in arithmetic
    assert "resident_primary" in top and "resident_residual" in top
    assert "impl=uram" in top
    assert "float " not in top + arithmetic
    assert "double " not in top + arithmetic


def test_rs2_scale_selection_is_resource_bounded_and_ii1() -> None:
    arithmetic = (ROOT / "hls/rs2/src/rs2_arithmetic.cpp").read_text(
        encoding="utf-8"
    )
    normalize = arithmetic.index("select_e2m1_normalize:")
    maximum = arithmetic.index("select_e2m1_max:")
    assert "normalized_magnitudes" in arithmetic
    assert "top_exponents" in arithmetic
    assert "#pragma HLS PIPELINE II=1" in arithmetic[normalize:maximum]
    assert "#pragma HLS PIPELINE II=1" in arithmetic[maximum:]
    selector = arithmetic[arithmetic.index("int select_e2m1_scale_power(") :]
    assert "#pragma HLS UNROLL" not in selector.split("e2m1_t quantize_e2m1(", 1)[0]


def test_rs2_element_scale_and_output_streams_have_independent_axi_ports() -> None:
    top = (ROOT / "hls/rs2/src/gdn_rs2_top.cpp").read_text(encoding="utf-8")
    expected = {
        "q_elements": "gmem0",
        "q_scales": "gmem16",
        "k_elements": "gmem1",
        "k_scales": "gmem17",
        "v_elements": "gmem2",
        "v_scales": "gmem18",
        "output_mantissas": "gmem9",
        "output_exponents": "gmem19",
    }
    for port, bundle in expected.items():
        assert f"port={port} offset=slave bundle={bundle}" in top


def test_rs2_flows_target_u55c_at_four_nanoseconds() -> None:
    standalone = (
        "run_arithmetic_csim.tcl",
        "run_csim.tcl",
        "run_csynth.tcl",
        "run_trace_csim.tcl",
        "run_trace_cosim.tcl",
    )
    for name in standalone:
        text = (ROOT / "hls/rs2/tcl" / name).read_text(encoding="utf-8")
        assert "xcu55c-fsvh2892-2L-e" in text
        assert "create_clock -period 4.0" in text
    trace_csim = (ROOT / "hls/rs2/tcl/run_trace_csim.tcl").read_text(
        encoding="utf-8"
    )
    assert "rs2_resident_trace64.bin" in trace_csim
    assert "rs2_resident_trace8.bin" not in trace_csim
    control = (ROOT / "hls/rs2/tcl/run_control_cosim.tcl").read_text(
        encoding="utf-8"
    )
    assert 'open_solution "u55c_250mhz"' in control
    assert "cosim_design -rtl verilog -tool xsim" in control


def test_rs2_trace_generator_freezes_capacity_and_counter_count() -> None:
    generator = (ROOT / "scripts/generate_rs2_hls_trace.py").read_text(
        encoding="utf-8"
    )
    assert "CAPACITY = 3" in generator
    assert "COUNTER_COUNT = 7" in generator
    manifest = (ROOT / "data/vectors/rs2_resident_trace64_manifest.json").read_text(
        encoding="utf-8"
    )
    assert '"tokens": 64' in manifest


def test_rs2_direct_rtl_harness_matches_split_axi_interface() -> None:
    harness = (ROOT / "hls/rtl_tb/tb_gdn_rs2_top_direct.sv").read_text(
        encoding="utf-8"
    )
    flow = (ROOT / "scripts/rs2_direct_rtl_flow.py").read_text(encoding="utf-8")
    assert "module tb_gdn_rs2_top_direct" in harness
    assert "gdn_rs2_top dut (.*);" in harness
    assert "localparam integer COUNTERS = 7" in harness
    assert "localparam integer LOG_KEY_ELEMENTS = 3 * 2 * 16 * 128" in harness
    for bundle in range(20):
        assert f"`DECL_AXI({bundle}," in harness
        assert f"`CONNECT_MEM({bundle}," in harness
    assert "mem16.mem[token_item] = trace_q_scales" in harness
    assert "mem17.mem[token_item] = trace_k_scales" in harness
    assert "mem18.mem[token_item] = trace_v_scales" in harness
    assert "mem19_u16(2*token_item)" in harness
    assert "tb_gdn_rs2_top_direct" in flow


def test_rs2_vivado_flows_use_selected_generated_rtl_and_u55c() -> None:
    create = (ROOT / "vivado/tcl/create_rs2_project.tcl").read_text(
        encoding="utf-8"
    )
    synth = (ROOT / "vivado/tcl/run_rs2_synth.tcl").read_text(encoding="utf-8")
    impl = (ROOT / "vivado/tcl/run_rs2_impl.tcl").read_text(encoding="utf-8")
    sweep = (ROOT / "vivado/tcl/run_rs2_postroute_sweep.tcl").read_text(
        encoding="utf-8"
    )
    explore = (
        ROOT / "vivado/tcl/run_rs2_postroute_explore_opt.tcl"
    ).read_text(encoding="utf-8")
    aggressive_explore = (
        ROOT / "vivado/tcl/run_rs2_postroute_aggressive_explore_opt.tcl"
    ).read_text(encoding="utf-8")
    flow = (ROOT / "scripts/vivado_flow.py").read_text(encoding="utf-8")
    assert "gdn_rs2_hls/u55c_250mhz/syn/verilog" in create
    assert "build/vivado/rs2_ooc_rtl/gdn_rs2_top.v" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "set_property top gdn_rs2_top" in create
    assert "synth_design -top gdn_rs2_top" in synth
    assert "route_design" in impl
    assert "phys_opt_design -directive Explore" in explore
    assert "phys_opt_design -directive AggressiveExplore" in aggressive_explore
    assert "report_timing_summary" in impl
    assert "report_power" in impl
    assert "rs2_post_impl.dcp" in sweep
    assert "prepare_rs2_ooc_rtl" in flow
    assert '"rs2-synth"' in flow
    assert '"rs2-impl"' in flow
    assert '"rs2-postroute-sweep"' in flow
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "vivado-rs2-report:" in makefile
    assert "scripts.rs2_vivado_report" in makefile

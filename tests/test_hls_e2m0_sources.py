import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_corrected_e2m0_constants_and_integer_datapath_are_frozen() -> None:
    header = (ROOT / "hls" / "e2m0" / "include" / "gdn_e2m0_kernel.hpp").read_text()
    arithmetic = (ROOT / "hls" / "e2m0" / "src" / "e2m0_arithmetic.cpp").read_text()
    top = (ROOT / "hls" / "e2m0" / "src" / "gdn_e2m0_top.cpp").read_text()
    assert "constexpr int STACK_DEPTH = 2;" in header
    assert "constexpr int LOG_CAPACITY = 7;" in header
    assert "constexpr int ACCUMULATOR_GUARD_BITS = 5;" in header
    assert "using e2m1_t = ap_uint<4>;" in header
    assert "using e2m0_t = ap_uint<3>;" in header
    assert "using mantissa_t = ap_int<32>;" in header
    assert "product_e2m1_e2m0" in arithmetic
    assert "static resident_primary_slot_t resident_primary" in top
    assert "static resident_update_log_t resident_updates" in top
    assert re.search(r"\bfloat\b", arithmetic) is None
    assert re.search(r"\bdouble\b", arithmetic) is None
    assert re.search(r"\bfloat\b", top) is None
    assert re.search(r"\bdouble\b", top) is None


def test_corrected_e2m0_flows_target_u55c_at_four_ns() -> None:
    for name in (
        "run_arithmetic_csim.tcl",
        "run_csim.tcl",
        "run_trace_csim.tcl",
        "run_csynth.tcl",
    ):
        text = (ROOT / "hls" / "e2m0" / "tcl" / name).read_text()
        assert "xcu55c-fsvh2892-2L-e" in text
        assert "create_clock -period 4.0" in text
    flow = (ROOT / "scripts" / "hls_flow.py").read_text()
    for command in (
        "e2m0-arithmetic-csim",
        "e2m0-csim",
        "e2m0-trace-csim",
        "e2m0-csynth",
    ):
        assert command in flow
    trace_tcl = (ROOT / "hls" / "e2m0" / "tcl" / "run_trace_csim.tcl").read_text()
    assert "E2M0_TRACE_PATH" in trace_tcl
    assert "e2m0_resident_trace8.bin" in trace_tcl


def test_corrected_candidate_has_bounded_generated_rtl_control_smoke() -> None:
    tb = (
        ROOT / "hls" / "e2m0" / "tb" / "tb_gdn_e2m0_rtl_control.cpp"
    ).read_text()
    tcl = (
        ROOT / "hls" / "e2m0" / "tcl" / "run_control_cosim.tcl"
    ).read_text()
    flow = (ROOT / "scripts" / "hls_flow.py").read_text()

    assert "STATUS_INVALID_LAYER_ID" in tb
    assert "STATUS_UNINITIALIZED_STATE" in tb
    assert "two exact commands" in tb
    assert "GDN_COSIM_MINGW" in tcl
    assert "XILINX_VITIS" in tcl
    assert "tps mingw" in tcl
    assert "cosim_design -rtl verilog -tool xsim" in tcl
    assert '"e2m0-control-cosim"' in flow


def test_trace_generator_resolves_cli_paths_against_repository() -> None:
    generator = (ROOT / "scripts" / "generate_e2m0_hls_trace.py").read_text()
    assert "ROOT / args.output" in generator
    assert "ROOT / args.manifest" in generator


def test_corrected_e2m0_vivado_flows_use_generated_rtl_and_u55c() -> None:
    create = (ROOT / "vivado" / "tcl" / "create_e2m0_project.tcl").read_text()
    synth = (ROOT / "vivado" / "tcl" / "run_e2m0_synth.tcl").read_text()
    impl = (ROOT / "vivado" / "tcl" / "run_e2m0_impl.tcl").read_text()
    sweep = (
        ROOT / "vivado" / "tcl" / "run_e2m0_postroute_sweep.tcl"
    ).read_text()
    clock_buffer = (
        ROOT / "vivado" / "tcl" / "insert_ooc_clock_buffer.tcl"
    ).read_text()
    flow = (ROOT / "scripts" / "vivado_flow.py").read_text()

    assert "gdn_e2m0_hls/u55c_250mhz/syn/verilog" in create
    assert "build/vivado/e2m0_ooc_rtl/gdn_e2m0_top.v" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "set_property top gdn_e2m0_top" in create
    assert "synth_design -top gdn_e2m0_top" in synth
    assert "report_drc" in synth
    assert "route_design" in impl
    assert "report_timing_summary" in impl
    assert "report_utilization" in impl
    assert "report_power" in impl
    assert "e2m0_post_impl.dcp" in sweep
    assert "5.600" in sweep
    assert "report_timing_summary" in sweep
    assert "report_power" in sweep
    assert "ooc_ap_clk_bufg" in impl
    assert "prepare_e2m0_ooc_rtl" in flow
    assert '"e2m0-synth"' in flow
    assert '"e2m0-impl"' in flow
    assert '"e2m0-postroute-sweep"' in flow

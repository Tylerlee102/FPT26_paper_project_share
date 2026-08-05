from pathlib import Path

from scripts.prepare_mxfp8_ooc_rtl import generate, transform_top


ROOT = Path(__file__).resolve().parents[1]


def _minimal_top() -> str:
    return """module gdn_mxfp8_top (
        ap_clk
);
input   ap_clk;

initial begin
end
child u_child(.ap_clk(ap_clk));
endmodule
"""


def test_transform_top_inserts_bufg_and_rewires_internal_clock() -> None:
    transformed = transform_top(_minimal_top())
    assert "input   ap_clk;" in transformed
    assert "BUFGCE ooc_ap_clk_bufg" in transformed
    assert ".I(ap_clk)" in transformed
    assert ".ap_clk(ooc_ap_clk_global)" in transformed


def test_generate_writes_hash_locked_manifest(tmp_path: Path) -> None:
    source = tmp_path / "gdn_mxfp8_top.v"
    output = tmp_path / "out" / "gdn_mxfp8_top.v"
    source.write_text(_minimal_top(), encoding="utf-8")
    manifest = generate(source, output)
    assert manifest["status"] == "PASS"
    assert output.exists()
    assert output.with_name("manifest.json").exists()


def test_mxfp8_flows_use_generated_rtl_and_u55c() -> None:
    create = (ROOT / "vivado" / "tcl" / "create_mxfp8_project.tcl").read_text()
    synth = (ROOT / "vivado" / "tcl" / "run_mxfp8_synth.tcl").read_text()
    impl = (ROOT / "vivado" / "tcl" / "run_mxfp8_impl.tcl").read_text()
    vivado_flow = (ROOT / "scripts" / "vivado_flow.py").read_text()
    assert "gdn_mxfp8_hls/u55c_250mhz/syn/verilog" in create
    assert "build/vivado/mxfp8_ooc_rtl/gdn_mxfp8_top.v" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "*_ip.tcl" in create
    assert "synth_design -top gdn_mxfp8_top" in synth
    assert "route_design" in impl
    assert "report_timing_summary" in impl
    assert "report_power" in impl
    assert "ooc_ap_clk_bufg" in impl
    assert "prepare_mxfp8_ooc_rtl" in vivado_flow
    assert '"mxfp8-synth"' in vivado_flow
    assert '"mxfp8-impl"' in vivado_flow

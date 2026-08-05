from pathlib import Path

from scripts.prepare_bf16_ooc_rtl import generate, transform_top


ROOT = Path(__file__).resolve().parents[1]


def _minimal_top() -> str:
    return """module gdn_bf16_top (
        ap_clk
);
input   ap_clk;

initial begin
end
child u_child(.ap_clk(ap_clk));
endmodule
"""


def test_transform_top_inserts_bufg_and_rewires_only_internal_clock() -> None:
    transformed = transform_top(_minimal_top())
    assert "input   ap_clk;" in transformed
    assert "BUFGCE ooc_ap_clk_bufg" in transformed
    assert ".I(ap_clk)" in transformed
    assert ".ap_clk(ooc_ap_clk_global)" in transformed


def test_generate_writes_hash_locked_manifest(tmp_path: Path) -> None:
    source = tmp_path / "gdn_bf16_top.v"
    output = tmp_path / "out" / "gdn_bf16_top.v"
    source.write_text(_minimal_top(), encoding="utf-8")

    manifest = generate(source, output)

    assert manifest["status"] == "PASS"
    assert output.exists()
    assert output.with_name("manifest.json").exists()
    assert manifest["source_sha256"]
    assert manifest["output_sha256"]


def test_bf16_flows_use_generated_rtl_and_u55c() -> None:
    create = (ROOT / "vivado" / "tcl" / "create_bf16_project.tcl").read_text()
    synth = (ROOT / "vivado" / "tcl" / "run_bf16_synth.tcl").read_text()
    impl = (ROOT / "vivado" / "tcl" / "run_bf16_impl.tcl").read_text()
    hls_flow = (ROOT / "scripts" / "hls_flow.py").read_text()
    vivado_flow = (ROOT / "scripts" / "vivado_flow.py").read_text()

    assert "gdn_bf16_hls/u55c_250mhz/syn/verilog" in create
    assert "build/vivado/bf16_ooc_rtl/gdn_bf16_top.v" in create
    assert "xcu55c-fsvh2892-2L-e" in create
    assert "set_property top gdn_bf16_top" in create
    assert "*_ip.tcl" in create
    assert "source $ip_script" in create
    assert "synth_design -top gdn_bf16_top" in synth
    assert "route_design" in impl
    assert "report_timing_summary" in impl
    assert "report_utilization" in impl
    assert "report_power" in impl
    assert "ooc_ap_clk_bufg" in impl
    assert '"bf16-csynth"' in hls_flow
    assert "prepare_bf16_ooc_rtl" in vivado_flow
    assert '"bf16-synth"' in vivado_flow
    assert '"bf16-impl"' in vivado_flow

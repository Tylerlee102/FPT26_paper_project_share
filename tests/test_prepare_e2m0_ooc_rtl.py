from pathlib import Path

from scripts.prepare_e2m0_ooc_rtl import generate, transform_top


def test_transform_top_inserts_bufg_and_rewires_only_internal_clock() -> None:
    source = """module gdn_e2m0_top (
        ap_clk
);
input   ap_clk;
wire x;

initial begin
end
child u_child(.ap_clk(ap_clk));
endmodule
"""
    transformed = transform_top(source)
    assert "input   ap_clk;" in transformed
    assert "BUFGCE ooc_ap_clk_bufg" in transformed
    assert ".I(ap_clk)" in transformed
    assert ".ap_clk(ooc_ap_clk_global)" in transformed


def test_generate_writes_hash_locked_manifest(tmp_path: Path) -> None:
    source = tmp_path / "gdn_e2m0_top.v"
    output = tmp_path / "out" / "gdn_e2m0_top.v"
    source.write_text(
        """module gdn_e2m0_top (
        ap_clk
);
input   ap_clk;

initial begin
end
child u_child(.ap_clk(ap_clk));
endmodule
""",
        encoding="utf-8",
    )
    manifest = generate(source, output)
    assert manifest["status"] == "PASS"
    assert output.exists()
    assert output.with_name("manifest.json").exists()

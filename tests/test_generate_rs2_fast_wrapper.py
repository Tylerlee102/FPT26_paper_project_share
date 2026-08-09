from pathlib import Path

from scripts.generate_rs2_fast_wrapper import generate


def test_fast_wrapper_keeps_dut_and_axi_models_but_removes_delay_scheduler(
    tmp_path: Path,
) -> None:
    output = tmp_path / "rs2_fast_wrapper.sv"
    result = generate(output)
    text = output.read_text(encoding="utf-8")
    assert result["status"] == "PASS"
    assert "module rs2_fast_wrapper;" in text
    assert "gdn_rs2_top dut (.*);" in text
    assert text.count("`CONNECT_MEM(") == 20
    assert "`CONNECT_MEM(0," in text
    assert "`CONNECT_MEM(19," in text
    assert "always #2" not in text
    assert "initial begin" not in text
    assert "fast_ap_done" in text
    assert text.count("/* verilator public_flat_rw */") == 30
    memory = tmp_path / "axi_memory_model_fast.sv"
    assert memory.is_file()
    assert "mem [0:MEM_BYTES-1] /* verilator public_flat_rw */" in memory.read_text(
        encoding="utf-8"
    )

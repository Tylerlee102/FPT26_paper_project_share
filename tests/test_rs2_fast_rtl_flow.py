from pathlib import Path

from scripts.rs2_fast_rtl_flow import _build_key


ROOT = Path(__file__).resolve().parents[1]


def test_fast_rtl_build_key_is_content_and_thread_sensitive(tmp_path: Path) -> None:
    source = tmp_path / "source.v"
    source.write_text("module source; endmodule\n", encoding="utf-8")
    first = _build_key([source], "Verilator test", 4)
    assert first == _build_key([source], "Verilator test", 4)
    assert first != _build_key([source], "Verilator test", 8)
    source.write_text("module source; wire x; endmodule\n", encoding="utf-8")
    assert first != _build_key([source], "Verilator test", 4)


def test_fast_rtl_flow_freezes_scheduler_free_contract() -> None:
    text = (ROOT / "scripts" / "rs2_fast_rtl_flow.py").read_text(encoding="utf-8")
    assert "--no-timing" in text
    assert "--public-flat-rw" not in text
    assert 'harness_mode="scheduler_free_cpp"' in text
    assert "RS2_MODEL_THREADS" in text

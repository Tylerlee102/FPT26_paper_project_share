from pathlib import Path

from scripts.bf16_hls_report import (
    DEFAULT_CSIM,
    DEFAULT_CSYNTH,
    generate_report,
    parse_csim,
    parse_step_cycles,
)


def test_parsers() -> None:
    assert parse_csim(
        "BF16_HLS_CSIM PASS reset_steps_readback=4 generation=2\n"
        "CSim done with 0 errors"
    ) == {"commands": 4, "generation": 2}
    assert parse_step_cycles("|- step_bf16_heads | 4225728| 4225728| x|") == {
        "minimum": 4_225_728,
        "maximum": 4_225_728,
    }


def test_real_bf16_hls_evidence(tmp_path: Path) -> None:
    report = generate_report(DEFAULT_CSIM, DEFAULT_CSYNTH, tmp_path)
    assert report["status"] == "PASS"
    assert report["csim"]["status"] == "PASS"
    assert report["csynth"]["step_loop_latency_cycles"]["maximum"] == 4_225_728
    assert report["csynth"]["metrics"]["resources"]["LUT"] == 84_919
    assert report["rtl_cosimulation_64_token"] == "NOT_RUN"
    assert (tmp_path / "bf16_hls_summary.json").exists()

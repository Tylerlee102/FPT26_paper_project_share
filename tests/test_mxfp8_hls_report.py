from pathlib import Path

from scripts.mxfp8_hls_report import (
    DEFAULT_ARITHMETIC_CSIM,
    DEFAULT_CSIM,
    DEFAULT_CSYNTH,
    generate_report,
)


def test_real_mxfp8_hls_evidence(tmp_path: Path) -> None:
    report = generate_report(
        DEFAULT_CSIM, DEFAULT_ARITHMETIC_CSIM, DEFAULT_CSYNTH, tmp_path
    )
    assert report["status"] == "PASS"
    assert report["csim"]["arithmetic"]["all_code_validity_and_decode_cases"] == 256
    assert report["csim"]["persistent_kernel"]["final_generation"] == 1
    assert report["csynth"]["step_loop_latency_cycles"]["maximum"] == 6_287_680
    assert report["csynth"]["metrics"]["resources"]["LUT"] == 143_084
    assert report["csynth"]["metrics"]["resources"]["DSP"] == 3
    assert report["rtl_cosimulation_long_trace"] == "NOT_RUN"
    assert (tmp_path / "mxfp8_hls_summary.json").exists()

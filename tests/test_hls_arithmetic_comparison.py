from pathlib import Path

from scripts.bf16_hls_report import DEFAULT_CSIM, DEFAULT_CSYNTH, generate_report
from scripts.hls_arithmetic_comparison import (
    DEFAULT_MX,
    DEFAULT_MX_IMPL,
    generate_comparison,
    parse_step_cycles,
)


def test_mxfp4_step_parser() -> None:
    assert parse_step_cycles("|- step_heads | 4972864| 6070592| x|") == {
        "minimum": 4_972_864,
        "maximum": 6_070_592,
    }


def test_controlled_hls_comparison(tmp_path: Path) -> None:
    hls_dir = tmp_path / "hls"
    bf16 = generate_report(DEFAULT_CSIM, DEFAULT_CSYNTH, hls_dir)
    assert bf16["status"] == "PASS"
    report = generate_comparison(
        DEFAULT_MX,
        hls_dir / "bf16_hls_summary.json",
        DEFAULT_MX_IMPL,
        tmp_path / "comparison",
    )
    assert report["status"] == "PASS"
    assert report["hls_lut_and_step_cost_advantage"] == "FAIL"
    assert report["energy_comparison"] == "BLOCKED_EXTERNAL_NO_U55C_DEVICE_OR_XRT"
    assert report["ratios"]["mxfp4_to_bf16_lut"] > 1.6
    assert report["ratios"]["mxfp4_to_bf16_step_cycles_max"] > 1.4
    assert report["ratios"]["mxfp8_to_bf16_lut"] > 1.6
    assert {row["variant"] for row in report["rows"]} == {
        "BF16",
        "uniform_mxfp4",
        "native_mxfp8",
    }

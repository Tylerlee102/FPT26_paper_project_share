from pathlib import Path

from scripts.bf16_hls_report import DEFAULT_CSIM, DEFAULT_CSYNTH, generate_report as generate_bf16
from scripts.hls_arithmetic_comparison import DEFAULT_MX
from scripts.state_capacity_lower_bound import generate_report


def test_all_layer_capacity_lower_bound(tmp_path: Path) -> None:
    bf16_dir = tmp_path / "bf16"
    generate_bf16(DEFAULT_CSIM, DEFAULT_CSYNTH, bf16_dir)
    report = generate_report(
        tmp_path / "capacity",
        DEFAULT_MX,
        bf16_dir / "bf16_hls_summary.json",
        DEFAULT_CSYNTH / "report" / "gdn_bf16_top_csynth.xml",
    )
    assert report["status"] == "PASS"
    rows = {row["variant"]: row for row in report["rows"]}
    assert rows["BF16"]["logical_state_bits"] == 301_989_888
    assert rows["BF16"]["per_layer_logical_state_bytes"] == 1_048_576
    assert rows["BF16"]["ideal_min_uram_for_mantissas"] == 1_024
    assert rows["BF16"]["raw_bit_capacity_necessary_condition"] == "FAIL"
    assert rows["uniform_mxfp4_e2m1_e8m0_b32"]["logical_state_bits"] == 80_216_064
    assert rows["uniform_mxfp4_e2m1_e8m0_b32"]["per_layer_logical_state_bytes"] == 278_528
    assert rows["uniform_mxfp4_e2m1_e8m0_b32"]["ideal_min_uram_for_mantissas"] == 256
    assert rows["uniform_mxfp4_e2m1_e8m0_b32"]["ideal_min_bram18k_for_scales"] == 256
    assert rows["BF16"]["physical_banked_fit"] == "PASS"
    assert rows["mxfp8_e4m3_e8m0_b32"]["reported_hls_uram"] == 64
    assert rows["mxfp8_e4m3_e8m0_b32"]["reported_hls_counts_cover_ideal_lower_bound"] == "FAIL"
    assert report["physical_all_layer_state_bank_fit"] == "SEE_PHYSICAL_FIT_BY_VARIANT"

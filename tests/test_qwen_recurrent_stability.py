from scripts.qwen_recurrent_stability import FLOATING_VARIANTS, RS2_VARIANT, VARIANTS


def test_real_trace_variants_include_controlled_comparators() -> None:
    assert FLOATING_VARIANTS == (
        "bf16_qdq_fp32_accum_state_bf16",
        "mxfp4_qdq_state_mxfp4_b32",
        "mxfp4_qdq_state_mxfp8_b32",
        "flat_int4_qdq",
    )
    assert RS2_VARIANT in VARIANTS
    assert set(VARIANTS) == set(FLOATING_VARIANTS) | {RS2_VARIANT}

from scripts.qwen_recurrent_stability import VARIANTS


def test_real_trace_variants_include_controlled_comparators() -> None:
    assert VARIANTS == (
        "bf16_qdq_fp32_accum_state_bf16",
        "mxfp4_qdq_state_mxfp4_b32",
        "mxfp4_qdq_state_mxfp8_b32",
        "flat_int4_qdq",
    )

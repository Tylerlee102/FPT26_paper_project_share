# Corrected Synthetic Long-Sequence Diagnostic

Generated: 2026-08-04T00:03:00.829465+00:00
Status: `PASS` for synthetic floating Q/DQ stability diagnostics only
Seed/split: `0xfb72` / `development`
Trace family: `dynamic_range`
Shape: value_heads=32, qk_heads=16, K=128, V=128, orientation=KxV
Tokens: 64
Checkpoints: 64
Token CSV: `reports/benchmark/corrected/stress/dynamic_range_64_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/stress/dynamic_range_64_checkpoints.csv`
Manifest: `reports/benchmark/corrected/stress/dynamic_range_64_manifest.json`

The run uses the corrected alpha-decayed Qwen recurrence and paired Q/K heads. MX rows are floating Q/DQ diagnostics, not encoded-oracle, HLS, RTL, board, or closed-loop model evidence.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs error |
|---:|---|---:|---:|---:|---:|
| 64 | bf16_qdq_fp32_accum_state_bf16 | 0.999906 | 0.013689 | 0.013926 | 0.001451 |
| 64 | flat_int4_qdq | 0.738762 | 2.041331 | 2.131726 | 0.107663 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 64 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.935044 | 0.610358 | 0.629195 | 0.121151 |
| 64 | mxfp4_qdq_act_b32_state_b32 | 0.775836 | 3.313158 | 3.465006 | 0.216050 |

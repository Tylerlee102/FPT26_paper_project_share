# Corrected Synthetic Long-Sequence Diagnostic

Generated: 2026-08-04T00:19:05.790334+00:00
Status: `PASS` for synthetic floating Q/DQ stability diagnostics only
Seed/split: `0xfb72` / `development`
Trace family: `dynamic_range`
Shape: value_heads=32, qk_heads=16, K=128, V=128, orientation=KxV
Tokens: 8192
Checkpoints: 64, 256, 1024, 4096, 8192
Token CSV: `reports/benchmark/corrected/stress/dynamic_range_8192_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/stress/dynamic_range_8192_checkpoints.csv`
Manifest: `reports/benchmark/corrected/stress/dynamic_range_8192_manifest.json`

The run uses the corrected alpha-decayed Qwen recurrence and paired Q/K heads. MX rows are floating Q/DQ diagnostics, not encoded-oracle, HLS, RTL, board, or closed-loop model evidence.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs error |
|---:|---|---:|---:|---:|---:|
| 64 | bf16_qdq_fp32_accum_state_bf16 | 0.999906 | 0.013689 | 0.013926 | 0.001451 |
| 64 | flat_int4_qdq | 0.738762 | 2.041331 | 2.131726 | 0.107663 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 64 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.935044 | 0.610358 | 0.629195 | 0.121151 |
| 64 | mxfp4_qdq_act_b32_state_b32 | 0.775836 | 3.313158 | 3.465006 | 0.216050 |
| 256 | bf16_qdq_fp32_accum_state_bf16 | 0.999967 | 0.008137 | 0.007952 | 0.031028 |
| 256 | flat_int4_qdq | 0.677015 | 1.225045 | 1.263538 | 2.151824 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 256 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.976307 | 0.222512 | 0.202373 | 0.953272 |
| 256 | mxfp4_qdq_act_b32_state_b32 | 0.917390 | 0.465525 | 0.487977 | 2.213688 |
| 1024 | bf16_qdq_fp32_accum_state_bf16 | 0.999962 | 0.008699 | 0.008976 | 0.004387 |
| 1024 | flat_int4_qdq | 0.413994 | 2.002488 | 2.049381 | 0.529369 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 1024 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.811766 | 0.775249 | 0.813318 | 2.263001 |
| 1024 | mxfp4_qdq_act_b32_state_b32 | 0.160222 | 15.580150 | 16.547146 | 8.053771 |
| 4096 | bf16_qdq_fp32_accum_state_bf16 | 0.999820 | 0.019163 | 0.018356 | 0.031880 |
| 4096 | flat_int4_qdq | 0.613616 | 4.621927 | 4.623472 | 3.145891 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 4096 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.901987 | 1.154517 | 1.111879 | 3.962812 |
| 4096 | mxfp4_qdq_act_b32_state_b32 | 0.695127 | 6.917095 | 6.874076 | 8.179366 |
| 8192 | bf16_qdq_fp32_accum_state_bf16 | 0.999875 | 0.015835 | 0.016476 | 0.006755 |
| 8192 | flat_int4_qdq | 0.402932 | 4.618249 | 4.810968 | 0.813795 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 8192 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.698070 | 2.269514 | 2.314652 | 2.231458 |
| 8192 | mxfp4_qdq_act_b32_state_b32 | 0.410379 | 25.033459 | 26.772181 | 11.991051 |

# Corrected Synthetic Long-Sequence Diagnostic

Generated: 2026-08-06T13:02:34.868964+00:00
Status: `PASS` for synthetic floating Q/DQ stability diagnostics only
Seed/split: `0xfb72` / `development`
Trace family: `high_retention`
Shape: value_heads=32, qk_heads=16, K=128, V=128, orientation=KxV
Tokens: 8192
Checkpoints: 64, 256, 1024, 4096, 8192
Token CSV: `reports/benchmark/corrected/rs2_controlled/high_retention_random_baselines_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/rs2_controlled/high_retention_random_baselines_checkpoints.csv`
Manifest: `reports/benchmark/corrected/rs2_controlled/high_retention_random_baselines_manifest.json`

The run uses the corrected alpha-decayed Qwen recurrence and paired Q/K heads. MX rows are floating Q/DQ diagnostics, not encoded-oracle, HLS, RTL, board, or closed-loop model evidence.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs error |
|---:|---|---:|---:|---:|---:|
| 64 | bf16_qdq_fp32_accum_state_bf16 | 0.999939 | 0.011475 | 0.011382 | 0.016382 |
| 64 | flat_int4_qdq | 0.596227 | 1.602732 | 1.595326 | 1.072564 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 64 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.966908 | 0.257153 | 0.222288 | 0.240712 |
| 64 | mxfp4_qdq_act_b32_state_b32 | 0.858245 | 0.524688 | 0.514852 | 0.476668 |
| 256 | bf16_qdq_fp32_accum_state_bf16 | 0.999842 | 0.019527 | 0.018909 | 0.032969 |
| 256 | flat_int4_qdq | 0.229780 | 3.122124 | 3.253407 | 3.071876 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 256 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.954358 | 0.301277 | 0.285436 | 0.457339 |
| 256 | mxfp4_qdq_act_b32_state_b32 | 0.723672 | 0.756235 | 0.741886 | 1.060105 |
| 1024 | bf16_qdq_fp32_accum_state_bf16 | 0.999815 | 0.021049 | 0.020935 | 0.029921 |
| 1024 | flat_int4_qdq | 0.073600 | 5.121459 | 5.088272 | 5.505537 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 1024 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.950803 | 0.315328 | 0.300345 | 0.523942 |
| 1024 | mxfp4_qdq_act_b32_state_b32 | 0.662794 | 0.875184 | 0.880347 | 1.270876 |
| 4096 | bf16_qdq_fp32_accum_state_bf16 | 0.999810 | 0.021683 | 0.021515 | 0.035727 |
| 4096 | flat_int4_qdq | 0.031689 | 7.451903 | 7.518989 | 8.164949 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 4096 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.953532 | 0.309658 | 0.300994 | 0.502278 |
| 4096 | mxfp4_qdq_act_b32_state_b32 | 0.667069 | 0.897994 | 0.898157 | 1.345301 |
| 8192 | bf16_qdq_fp32_accum_state_bf16 | 0.999812 | 0.020768 | 0.020998 | 0.041461 |
| 8192 | flat_int4_qdq | 0.121427 | 2.654673 | 2.736632 | 2.891224 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 8192 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.950258 | 0.318446 | 0.301757 | 0.443426 |
| 8192 | mxfp4_qdq_act_b32_state_b32 | 0.672818 | 0.870688 | 0.903408 | 1.287642 |

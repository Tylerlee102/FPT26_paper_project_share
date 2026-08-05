# Corrected Synthetic Long-Sequence Diagnostic

Generated: 2026-08-04T00:30:58.851106+00:00
Status: `PASS` for synthetic floating Q/DQ stability diagnostics only
Seed/split: `0xfb72` / `development`
Trace family: `cancellation`
Shape: value_heads=32, qk_heads=16, K=128, V=128, orientation=KxV
Tokens: 8192
Checkpoints: 64, 256, 1024, 4096, 8192
Token CSV: `reports/benchmark/corrected/stress/cancellation_8192_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/stress/cancellation_8192_checkpoints.csv`
Manifest: `reports/benchmark/corrected/stress/cancellation_8192_manifest.json`

The run uses the corrected alpha-decayed Qwen recurrence and paired Q/K heads. MX rows are floating Q/DQ diagnostics, not encoded-oracle, HLS, RTL, board, or closed-loop model evidence.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs error |
|---:|---|---:|---:|---:|---:|
| 64 | bf16_qdq_fp32_accum_state_bf16 | 0.999997 | 0.002606 | 0.009426 | 0.003222 |
| 64 | flat_int4_qdq | 0.969741 | 0.273287 | 1.480188 | 0.227680 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 64 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.996756 | 0.080508 | 0.264028 | 0.098314 |
| 64 | mxfp4_qdq_act_b32_state_b32 | 0.988435 | 0.158928 | 1.010532 | 0.351078 |
| 256 | bf16_qdq_fp32_accum_state_bf16 | 0.999997 | 0.002436 | 0.008783 | 0.002524 |
| 256 | flat_int4_qdq | 0.974662 | 0.241199 | 1.453180 | 0.209990 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 256 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.996834 | 0.080710 | 0.260810 | 0.099561 |
| 256 | mxfp4_qdq_act_b32_state_b32 | 0.985130 | 0.178560 | 1.369974 | 0.480251 |
| 1024 | bf16_qdq_fp32_accum_state_bf16 | 0.999997 | 0.002486 | 0.008737 | 0.002791 |
| 1024 | flat_int4_qdq | 0.968991 | 0.267180 | 1.698275 | 0.260979 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 1024 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.996610 | 0.082300 | 0.257955 | 0.087053 |
| 1024 | mxfp4_qdq_act_b32_state_b32 | 0.983098 | 0.190557 | 1.512507 | 0.530845 |
| 4096 | bf16_qdq_fp32_accum_state_bf16 | 0.999997 | 0.002624 | 0.008903 | 0.003562 |
| 4096 | flat_int4_qdq | 0.975872 | 0.241308 | 1.451181 | 0.200032 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 4096 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.996888 | 0.078868 | 0.257315 | 0.101932 |
| 4096 | mxfp4_qdq_act_b32_state_b32 | 0.979559 | 0.214937 | 1.698711 | 0.747296 |
| 8192 | bf16_qdq_fp32_accum_state_bf16 | 0.999997 | 0.002408 | 0.008844 | 0.003362 |
| 8192 | flat_int4_qdq | 0.975327 | 0.235514 | 1.332802 | 0.195261 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 8192 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.997011 | 0.077912 | 0.255859 | 0.097232 |
| 8192 | mxfp4_qdq_act_b32_state_b32 | 0.981307 | 0.204315 | 1.667123 | 0.765504 |

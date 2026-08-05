# Corrected Synthetic Long-Sequence Diagnostic

Generated: 2026-08-02T03:26:31.205057+00:00
Status: `PASS` for synthetic floating Q/DQ stability diagnostics only
Seed/split: `0xfb72` / `development`
Trace family: `nominal`
Shape: value_heads=32, qk_heads=16, K=128, V=128, orientation=KxV
Tokens: 8192
Checkpoints: 64, 256, 1024, 4096, 8192
Token CSV: `reports/benchmark/corrected/long_trace_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/long_trace_checkpoints.csv`
Manifest: `reports/benchmark/corrected/long_trace_manifest.json`

The run uses the corrected alpha-decayed Qwen recurrence and paired Q/K heads. MX rows are floating Q/DQ diagnostics, not encoded-oracle, HLS, RTL, board, or closed-loop model evidence.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs error |
|---:|---|---:|---:|---:|---:|
| 64 | bf16_qdq_fp32_accum_state_bf16 | 0.999964 | 0.008534 | 0.008532 | 0.004901 |
| 64 | flat_int4_qdq | 0.638114 | 1.455261 | 1.507220 | 0.346371 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 64 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.972135 | 0.243198 | 0.220722 | 0.159600 |
| 64 | mxfp4_qdq_act_b32_state_b32 | 0.864884 | 0.659743 | 0.697283 | 0.393287 |
| 256 | bf16_qdq_fp32_accum_state_bf16 | 0.999962 | 0.008760 | 0.009048 | 0.006116 |
| 256 | flat_int4_qdq | 0.554967 | 1.777732 | 1.804924 | 0.470826 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 256 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.970755 | 0.254718 | 0.235070 | 0.151208 |
| 256 | mxfp4_qdq_act_b32_state_b32 | 0.767398 | 1.031823 | 1.082337 | 0.591019 |
| 1024 | bf16_qdq_fp32_accum_state_bf16 | 0.999959 | 0.009045 | 0.008735 | 0.004005 |
| 1024 | flat_int4_qdq | 0.509439 | 1.930365 | 1.873922 | 0.458476 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 1024 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.969225 | 0.254064 | 0.229081 | 0.154873 |
| 1024 | mxfp4_qdq_act_b32_state_b32 | 0.726945 | 1.117041 | 1.131784 | 1.053724 |
| 4096 | bf16_qdq_fp32_accum_state_bf16 | 0.999957 | 0.009288 | 0.008976 | 0.004979 |
| 4096 | flat_int4_qdq | 0.558447 | 1.523382 | 1.526303 | 0.339850 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 4096 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.970592 | 0.250591 | 0.229964 | 0.139956 |
| 4096 | mxfp4_qdq_act_b32_state_b32 | 0.734925 | 1.127432 | 1.138261 | 0.787032 |
| 8192 | bf16_qdq_fp32_accum_state_bf16 | 0.999955 | 0.009542 | 0.008988 | 0.006128 |
| 8192 | flat_int4_qdq | 0.525403 | 1.846115 | 1.862013 | 0.479394 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| 8192 | mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32 | 0.968498 | 0.262453 | 0.232133 | 0.157263 |
| 8192 | mxfp4_qdq_act_b32_state_b32 | 0.729275 | 1.106857 | 1.103841 | 0.789244 |

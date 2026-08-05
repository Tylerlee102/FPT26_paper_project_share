# Dense E2M0 Fold-Residual Development Diagnostic

Generated: 2026-08-02T07:59:12.483398+00:00
Engineering gate at executed length: `FAIL`
Variant: `mxfp4_rs3_act_mxfp4_e2m0rs2_base_b32_mxfp8_log_fixed_b32_r7`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Tokens/checkpoints: 1024 / 64, 256, 1024
Logical recurrent-state bytes: 536912
Input-stream SHA256: `f36cdb646f79095ebc6b2eb93f2231b7f4f3fea58cd5c1e58f51314e7552a656`
Token CSV: `reports/benchmark/corrected/e2m0_residual/development_high_retention_1024_actrs3/development_seed0000fb72_high_retention_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/e2m0_residual/development_high_retention_1024_actrs3/development_seed0000fb72_high_retention_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/e2m0_residual/development_high_retention_1024_actrs3/development_seed0000fb72_high_retention_random_manifest.json`

The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The MXFP8 write log, fold schedule, recurrence boundary, and activation stack are unchanged.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs3_act_mxfp4_e2m0rs2_base_b32_mxfp8_log_fixed_b32_r7 | 0.997401 | 0.072097 | 0.071120 | 0.091530 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs3_act_mxfp4_e2m0rs2_base_b32_mxfp8_log_fixed_b32_r7 | 0.995260 | 0.097374 | 0.095612 | 0.196925 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs3_act_mxfp4_e2m0rs2_base_b32_mxfp8_log_fixed_b32_r7 | 0.994802 | 0.101834 | 0.101707 | 0.170993 | 146 | 0 | 536912 |

This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.

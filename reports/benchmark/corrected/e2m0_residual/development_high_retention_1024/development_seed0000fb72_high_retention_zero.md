# Dense E2M0 Fold-Residual Development Diagnostic

Generated: 2026-08-02T07:58:31.441585+00:00
Engineering gate at executed length: `FAIL`
Variant: `mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp8_log_fixed_b32_r7`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `zero`
Tokens/checkpoints: 1024 / 64, 256, 1024
Logical recurrent-state bytes: 536912
Input-stream SHA256: `1084e695938e2e38ecfd16802a18bf8cb1d2b2431c70fd98d059fc2b70312d86`
Token CSV: `reports/benchmark/corrected/e2m0_residual/development_high_retention_1024/development_seed0000fb72_high_retention_zero_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/e2m0_residual/development_high_retention_1024/development_seed0000fb72_high_retention_zero_checkpoints.csv`
Manifest: `reports/benchmark/corrected/e2m0_residual/development_high_retention_1024/development_seed0000fb72_high_retention_zero_manifest.json`

The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The MXFP8 write log, fold schedule, recurrence boundary, and activation stack are unchanged.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp8_log_fixed_b32_r7 | 0.997007 | 0.077349 | 0.074512 | 0.070231 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp8_log_fixed_b32_r7 | 0.994680 | 0.103019 | 0.099846 | 0.165156 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp8_log_fixed_b32_r7 | 0.994554 | 0.104309 | 0.105812 | 0.158530 | 146 | 0 | 536912 |

This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.

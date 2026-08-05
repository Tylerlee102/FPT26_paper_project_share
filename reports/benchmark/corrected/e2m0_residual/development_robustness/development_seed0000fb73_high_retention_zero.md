# Dense E2M0 Fold-Residual Development Diagnostic

Generated: 2026-08-02T08:11:20.310816+00:00
Engineering gate at executed length: `PASS`
Variant: `mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7`
Split/seed/family: `development` / `0xfb73` / `high_retention`
Initial state: `zero`
Tokens/checkpoints: 1024 / 64, 256, 1024
Logical recurrent-state bytes: 538256
Input-stream SHA256: `ce2fce14f7ff5c05df1a1f51893b338541365b55c020a38a2c9b0daaff555fba`
Token CSV: `reports/benchmark/corrected/e2m0_residual/development_robustness/development_seed0000fb73_high_retention_zero_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/e2m0_residual/development_robustness/development_seed0000fb73_high_retention_zero_checkpoints.csv`
Manifest: `reports/benchmark/corrected/e2m0_residual/development_robustness/development_seed0000fb73_high_retention_zero_manifest.json`

The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The write log uses two residual-stacked MXFP4 terms; fold schedule, recurrence boundary, and activation stack are unchanged.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.997944 | 0.064102 | 0.062214 | 0.075463 | 9 | 0 | 538256 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.995870 | 0.090923 | 0.089102 | 0.139124 | 36 | 0 | 538256 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.995473 | 0.095094 | 0.095412 | 0.163824 | 146 | 0 | 538256 |

This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.

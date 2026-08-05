# Dense E2M0 Fold-Residual Development Diagnostic

Generated: 2026-08-02T08:09:13.145907+00:00
Engineering gate at executed length: `PASS`
Variant: `mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `zero`
Tokens/checkpoints: 1024 / 64, 256, 1024
Logical recurrent-state bytes: 538256
Input-stream SHA256: `1084e695938e2e38ecfd16802a18bf8cb1d2b2431c70fd98d059fc2b70312d86`
Token CSV: `reports/benchmark/corrected/e2m0_residual/development_robustness/development_seed0000fb72_high_retention_zero_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/e2m0_residual/development_robustness/development_seed0000fb72_high_retention_zero_checkpoints.csv`
Manifest: `reports/benchmark/corrected/e2m0_residual/development_robustness/development_seed0000fb72_high_retention_zero_manifest.json`

The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The write log uses two residual-stacked MXFP4 terms; fold schedule, recurrence boundary, and activation stack are unchanged.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.997876 | 0.065190 | 0.062327 | 0.078236 | 9 | 0 | 538256 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.995964 | 0.089777 | 0.088998 | 0.190405 | 36 | 0 | 538256 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.995207 | 0.097792 | 0.095490 | 0.139255 | 146 | 0 | 538256 |

This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.

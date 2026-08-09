# Dense E2M0 Fold-Residual Development Diagnostic

Generated: 2026-08-06T08:22:06.168927+00:00
Engineering gate at executed length: `FAIL`
Variant: `mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r6`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Tokens/checkpoints: 1024 / 64, 256, 1024
Logical recurrent-state bytes: 531600
Input-stream SHA256: `f36cdb646f79095ebc6b2eb93f2231b7f4f3fea58cd5c1e58f51314e7552a656`
Token CSV: `reports/benchmark/corrected/e2m0_capacity_sweep/high_retention_random_r6_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/e2m0_capacity_sweep/high_retention_random_r6_checkpoints.csv`
Manifest: `reports/benchmark/corrected/e2m0_capacity_sweep/high_retention_random_r6_manifest.json`

The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The write log uses two residual-stacked MXFP4 terms; fold schedule, recurrence boundary, and activation stack are unchanged.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r6 | 0.997642 | 0.068642 | 0.064978 | 0.075790 | 10 | 0 | 531600 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r6 | 0.995141 | 0.098465 | 0.095242 | 0.194504 | 42 | 0 | 531600 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r6 | 0.994695 | 0.102904 | 0.100602 | 0.188232 | 170 | 0 | 531600 |

This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.

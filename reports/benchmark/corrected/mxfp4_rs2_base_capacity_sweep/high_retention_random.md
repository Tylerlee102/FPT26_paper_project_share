# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-06T08:25:38.938705+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 1.0
Tokens/checkpoints: 1024 / 64, 256, 1024
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `f36cdb646f79095ebc6b2eb93f2231b7f4f3fea58cd5c1e58f51314e7552a656`
Token CSV: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r1 | 0.995825 | 0.091594 | 0.089635 | 0.081247 | 64 | 0 | 563664 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r2 | 0.997286 | 0.073632 | 0.072641 | 0.064994 | 32 | 0 | 570128 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r3 | 0.997739 | 0.067220 | 0.064961 | 0.053269 | 21 | 0 | 576592 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r4 | 0.998070 | 0.062098 | 0.061810 | 0.052746 | 16 | 0 | 583056 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r1 | 0.991894 | 0.127065 | 0.124613 | 0.197896 | 256 | 0 | 563664 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r2 | 0.995091 | 0.099429 | 0.097353 | 0.127809 | 128 | 0 | 570128 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r3 | 0.996165 | 0.087654 | 0.085168 | 0.105352 | 85 | 0 | 576592 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r4 | 0.996845 | 0.079412 | 0.078854 | 0.092378 | 64 | 0 | 583056 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r1 | 0.991188 | 0.132561 | 0.131320 | 0.154150 | 1024 | 0 | 563664 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r2 | 0.994837 | 0.101661 | 0.101969 | 0.120122 | 512 | 0 | 570128 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r3 | 0.995958 | 0.089905 | 0.089065 | 0.137650 | 341 | 0 | 576592 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r4 | 0.996531 | 0.083278 | 0.082369 | 0.083146 | 256 | 0 | 583056 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

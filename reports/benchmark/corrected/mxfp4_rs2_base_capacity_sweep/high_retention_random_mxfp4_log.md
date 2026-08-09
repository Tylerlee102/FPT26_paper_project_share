# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-06T08:31:32.072743+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 1.0
Tokens/checkpoints: 1024 / 64, 256, 1024
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `f36cdb646f79095ebc6b2eb93f2231b7f4f3fea58cd5c1e58f51314e7552a656`
Token CSV: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_random_mxfp4_log_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_random_mxfp4_log_checkpoints.csv`
Manifest: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_random_mxfp4_log_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r1 | 0.996754 | 0.080735 | 0.079625 | 0.084636 | 64 | 0 | 563856 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.998091 | 0.061848 | 0.060475 | 0.060614 | 32 | 0 | 570512 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r3 | 0.998590 | 0.053162 | 0.051235 | 0.045499 | 21 | 0 | 577168 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r4 | 0.998869 | 0.047577 | 0.047089 | 0.044147 | 16 | 0 | 583824 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r1 | 0.993236 | 0.118311 | 0.117470 | 0.202304 | 256 | 0 | 563856 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.996334 | 0.085711 | 0.086259 | 0.127809 | 128 | 0 | 570512 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r3 | 0.997298 | 0.073470 | 0.072264 | 0.082420 | 85 | 0 | 577168 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r4 | 0.997785 | 0.066556 | 0.064796 | 0.075385 | 64 | 0 | 583824 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r1 | 0.992730 | 0.122370 | 0.125387 | 0.169465 | 1024 | 0 | 563856 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.995913 | 0.090453 | 0.091227 | 0.129677 | 512 | 0 | 570512 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r3 | 0.996982 | 0.077713 | 0.076072 | 0.096806 | 341 | 0 | 577168 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r4 | 0.997692 | 0.067935 | 0.068259 | 0.097451 | 256 | 0 | 583824 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

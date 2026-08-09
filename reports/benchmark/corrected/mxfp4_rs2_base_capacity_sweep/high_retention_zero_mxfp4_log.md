# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-06T08:33:43.559678+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `zero`
Base residual-block fraction: 1.0
Tokens/checkpoints: 1024 / 64, 256, 1024
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `1084e695938e2e38ecfd16802a18bf8cb1d2b2431c70fd98d059fc2b70312d86`
Token CSV: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_zero_mxfp4_log_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_zero_mxfp4_log_checkpoints.csv`
Manifest: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_zero_mxfp4_log_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r1 | 0.996952 | 0.078287 | 0.077116 | 0.080414 | 64 | 0 | 563856 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.998206 | 0.059938 | 0.058824 | 0.069677 | 32 | 0 | 570512 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r1 | 0.993239 | 0.117929 | 0.116798 | 0.165380 | 256 | 0 | 563856 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.996120 | 0.088298 | 0.086091 | 0.130991 | 128 | 0 | 570512 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r1 | 0.992575 | 0.123028 | 0.125295 | 0.176921 | 1024 | 0 | 563856 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.995955 | 0.089950 | 0.091135 | 0.123981 | 512 | 0 | 570512 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

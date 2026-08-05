# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T07:44:49.073775+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 256 / 1, 7, 8, 14, 28, 64, 128, 256
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `e4a093eebba9fd78149c9bc2369043a7fc1eb33bc5c39a63ffcb36d760860e1d`
Token CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_fp32log_r7_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_fp32log_r7_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_fp32log_r7_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1 | mxfp4_rs2_act_rs2_sparse75_base_b32_fp32_log_fixed_b32_r7 | 0.998584 | 0.053205 | 0.049335 | 0.016663 | 0 | 0 | 664592 |
| 7 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 7 | mxfp4_rs2_act_rs2_sparse75_base_b32_fp32_log_fixed_b32_r7 | 0.999129 | 0.041744 | 0.064399 | 0.037880 | 1 | 0 | 664592 |
| 8 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8 | mxfp4_rs2_act_rs2_sparse75_base_b32_fp32_log_fixed_b32_r7 | 0.998081 | 0.061935 | 0.062099 | 0.038060 | 1 | 0 | 664592 |
| 14 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 14 | mxfp4_rs2_act_rs2_sparse75_base_b32_fp32_log_fixed_b32_r7 | 0.998618 | 0.052577 | 0.073767 | 0.056727 | 2 | 0 | 664592 |
| 28 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 28 | mxfp4_rs2_act_rs2_sparse75_base_b32_fp32_log_fixed_b32_r7 | 0.997200 | 0.074897 | 0.088592 | 0.075415 | 4 | 0 | 664592 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_fp32_log_fixed_b32_r7 | 0.993239 | 0.116273 | 0.112249 | 0.118391 | 9 | 0 | 664592 |
| 128 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 128 | mxfp4_rs2_act_rs2_sparse75_base_b32_fp32_log_fixed_b32_r7 | 0.989668 | 0.143761 | 0.141212 | 0.186120 | 18 | 0 | 664592 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_fp32_log_fixed_b32_r7 | 0.986009 | 0.166936 | 0.165040 | 0.202721 | 36 | 0 | 664592 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

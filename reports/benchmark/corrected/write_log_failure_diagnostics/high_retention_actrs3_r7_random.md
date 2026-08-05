# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T07:45:25.011767+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 256 / 1, 7, 8, 14, 28, 64, 128, 255, 256
Residual-stack depths (activation/base): 3/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `e4a093eebba9fd78149c9bc2369043a7fc1eb33bc5c39a63ffcb36d760860e1d`
Token CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_actrs3_r7_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_actrs3_r7_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_actrs3_r7_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1 | mxfp4_rs3_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998655 | 0.051862 | 0.050871 | 0.023177 | 0 | 0 | 536912 |
| 7 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 7 | mxfp4_rs3_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998909 | 0.046693 | 0.069001 | 0.042101 | 1 | 0 | 536912 |
| 8 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8 | mxfp4_rs3_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.997822 | 0.065977 | 0.067176 | 0.041068 | 1 | 0 | 536912 |
| 14 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 14 | mxfp4_rs3_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998233 | 0.059421 | 0.079152 | 0.057499 | 2 | 0 | 536912 |
| 28 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 28 | mxfp4_rs3_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.996810 | 0.079857 | 0.093821 | 0.075298 | 4 | 0 | 536912 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs3_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.993041 | 0.117878 | 0.117087 | 0.115977 | 9 | 0 | 536912 |
| 128 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 128 | mxfp4_rs3_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.989416 | 0.145163 | 0.145578 | 0.176168 | 18 | 0 | 536912 |
| 255 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 255 | mxfp4_rs3_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.984822 | 0.173759 | 0.170585 | 0.244999 | 36 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs3_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.985012 | 0.172909 | 0.169481 | 0.240946 | 36 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

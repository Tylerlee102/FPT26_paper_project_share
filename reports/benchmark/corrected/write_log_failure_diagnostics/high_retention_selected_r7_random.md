# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T07:45:14.792567+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 256 / 1, 7, 8, 14, 28, 64, 128, 255, 256
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `e4a093eebba9fd78149c9bc2369043a7fc1eb33bc5c39a63ffcb36d760860e1d`
Token CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_selected_r7_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_selected_r7_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_selected_r7_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998487 | 0.055003 | 0.051737 | 0.029468 | 0 | 0 | 536912 |
| 7 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 7 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998670 | 0.051558 | 0.071323 | 0.041190 | 1 | 0 | 536912 |
| 8 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.997561 | 0.069807 | 0.069734 | 0.041714 | 1 | 0 | 536912 |
| 14 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 14 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998007 | 0.063143 | 0.081919 | 0.057972 | 2 | 0 | 536912 |
| 28 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 28 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.996318 | 0.085758 | 0.096726 | 0.082814 | 4 | 0 | 536912 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.992194 | 0.125003 | 0.119674 | 0.129397 | 9 | 0 | 536912 |
| 128 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 128 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.988663 | 0.150233 | 0.148245 | 0.166019 | 18 | 0 | 536912 |
| 255 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 255 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.984336 | 0.176749 | 0.172804 | 0.208102 | 36 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.984675 | 0.174908 | 0.171711 | 0.207100 | 36 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

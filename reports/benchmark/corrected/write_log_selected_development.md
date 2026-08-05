# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-01T23:48:27.998782+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `nominal`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `b7a5d7fc701d308e0a06b1feedd83a2a908d3b1962a839cecbae33c04fa26f80`
Token CSV: `reports/benchmark/corrected/write_log_selected_development_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_selected_development_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_selected_development_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995454 | 0.095256 | 0.097481 | 0.046963 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995698 | 0.092665 | 0.094493 | 0.040757 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995161 | 0.098258 | 0.096006 | 0.051454 | 146 | 0 | 536912 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.994591 | 0.104193 | 0.099248 | 0.051750 | 585 | 0 | 536912 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.994926 | 0.100674 | 0.097767 | 0.040272 | 1170 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

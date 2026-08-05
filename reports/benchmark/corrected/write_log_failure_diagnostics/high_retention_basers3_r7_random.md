# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T07:45:30.975121+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 256 / 1, 7, 8, 14, 28, 64, 128, 255, 256
Residual-stack depths (activation/base): 2/3
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `e4a093eebba9fd78149c9bc2369043a7fc1eb33bc5c39a63ffcb36d760860e1d`
Token CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_basers3_r7_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_basers3_r7_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_basers3_r7_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1 | mxfp4_rs2_act_rs3_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999732 | 0.023173 | 0.019012 | 0.025644 | 0 | 0 | 749904 |
| 7 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 7 | mxfp4_rs2_act_rs3_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999319 | 0.036907 | 0.035653 | 0.023115 | 1 | 0 | 749904 |
| 8 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8 | mxfp4_rs2_act_rs3_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999256 | 0.038566 | 0.036641 | 0.023184 | 1 | 0 | 749904 |
| 14 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 14 | mxfp4_rs2_act_rs3_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999144 | 0.041388 | 0.041100 | 0.025272 | 2 | 0 | 749904 |
| 28 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 28 | mxfp4_rs2_act_rs3_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998867 | 0.047585 | 0.045595 | 0.032509 | 4 | 0 | 749904 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs3_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998531 | 0.054195 | 0.050901 | 0.038906 | 9 | 0 | 749904 |
| 128 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 128 | mxfp4_rs2_act_rs3_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998331 | 0.057750 | 0.056221 | 0.050377 | 18 | 0 | 749904 |
| 255 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 255 | mxfp4_rs2_act_rs3_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998156 | 0.060749 | 0.060204 | 0.059510 | 36 | 0 | 749904 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs3_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998071 | 0.062109 | 0.060112 | 0.059147 | 36 | 0 | 749904 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

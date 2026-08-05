# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T07:45:19.801135+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 1.0
Tokens/checkpoints: 256 / 1, 7, 8, 14, 28, 64, 128, 255, 256
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `e4a093eebba9fd78149c9bc2369043a7fc1eb33bc5c39a63ffcb36d760860e1d`
Token CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_densebase_r7_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_densebase_r7_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_densebase_r7_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r7 | 0.999687 | 0.025020 | 0.021467 | 0.025400 | 0 | 0 | 602448 |
| 7 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 7 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r7 | 0.999303 | 0.037340 | 0.038007 | 0.023115 | 1 | 0 | 602448 |
| 8 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r7 | 0.999186 | 0.040343 | 0.038740 | 0.023184 | 1 | 0 | 602448 |
| 14 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 14 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r7 | 0.999095 | 0.042572 | 0.043716 | 0.026248 | 2 | 0 | 602448 |
| 28 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 28 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r7 | 0.998733 | 0.050325 | 0.049162 | 0.032650 | 4 | 0 | 602448 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r7 | 0.998190 | 0.060148 | 0.056230 | 0.044797 | 9 | 0 | 602448 |
| 128 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 128 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r7 | 0.997854 | 0.065474 | 0.063378 | 0.052111 | 18 | 0 | 602448 |
| 255 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 255 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r7 | 0.997459 | 0.071278 | 0.069014 | 0.071436 | 36 | 0 | 602448 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp8_log_fixed_b32_r7 | 0.997453 | 0.071406 | 0.068823 | 0.070884 | 36 | 0 | 602448 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T07:45:43.977296+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 256 / 1, 7, 8, 14, 28, 64, 128, 255, 256
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `e4a093eebba9fd78149c9bc2369043a7fc1eb33bc5c39a63ffcb36d760860e1d`
Token CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_nofolduntil256_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_nofolduntil256_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_failure_diagnostics/high_retention_nofolduntil256_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r256 | 0.998487 | 0.055003 | 0.051737 | 0.029468 | 0 | 0 | 2146448 |
| 7 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 7 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r256 | 0.998670 | 0.051558 | 0.049181 | 0.030158 | 0 | 0 | 2146448 |
| 8 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r256 | 0.998781 | 0.049358 | 0.049003 | 0.029632 | 0 | 0 | 2146448 |
| 14 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 14 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r256 | 0.998779 | 0.049440 | 0.048233 | 0.028355 | 0 | 0 | 2146448 |
| 28 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 28 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r256 | 0.998690 | 0.051174 | 0.047960 | 0.030776 | 0 | 0 | 2146448 |
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r256 | 0.998617 | 0.052572 | 0.049227 | 0.038084 | 0 | 0 | 2146448 |
| 128 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 128 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r256 | 0.998538 | 0.054054 | 0.051688 | 0.046183 | 0 | 0 | 2146448 |
| 255 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 255 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r256 | 0.998492 | 0.054898 | 0.053736 | 0.045924 | 0 | 0 | 2146448 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r256 | 0.998438 | 0.055871 | 0.075595 | 0.090080 | 1 | 0 | 2146448 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

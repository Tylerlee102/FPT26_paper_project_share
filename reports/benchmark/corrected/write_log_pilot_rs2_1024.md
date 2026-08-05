# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-01T23:15:27.088721+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `nominal`
Tokens/checkpoints: 1024 / 64, 256, 1024
Residual-stack depths (activation/base): 2/2
Input-stream SHA256: `024f826e1d807c279fb957950d0167771041f7d0ed71c749d71fa3f36e533332`
Token CSV: `reports/benchmark/corrected/write_log_pilot_rs2_1024_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_pilot_rs2_1024_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_pilot_rs2_1024_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r16 | 0.998821 | 0.048613 | 0.048130 | 0.022476 | 4 | 0 | 660624 |
| 64 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r4 | 0.998493 | 0.054900 | 0.053957 | 0.023845 | 16 | 0 | 583056 |
| 64 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r8 | 0.998724 | 0.050532 | 0.050083 | 0.022476 | 8 | 0 | 608912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r16 | 0.998898 | 0.046945 | 0.049016 | 0.020287 | 16 | 0 | 660624 |
| 256 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r4 | 0.998615 | 0.052627 | 0.055294 | 0.020130 | 64 | 0 | 583056 |
| 256 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r8 | 0.998810 | 0.048785 | 0.051141 | 0.022178 | 32 | 0 | 608912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r16 | 0.998765 | 0.049754 | 0.048785 | 0.020859 | 64 | 0 | 660624 |
| 1024 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r4 | 0.998405 | 0.056471 | 0.054622 | 0.026999 | 256 | 0 | 583056 |
| 1024 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r8 | 0.998628 | 0.052432 | 0.050776 | 0.021153 | 128 | 0 | 608912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

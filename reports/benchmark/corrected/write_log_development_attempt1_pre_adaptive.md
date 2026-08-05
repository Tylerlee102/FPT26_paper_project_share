# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-01T23:23:08.504249+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `nominal`
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Residual-stack depths (activation/base): 2/2
Input-stream SHA256: `6e2a2d9a784da878c71298b6565ac0cff7d06d2b30c262b6f9c37d6bd26fff80`
Token CSV: `reports/benchmark/corrected/write_log_development_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_development_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_development_manifest.json`

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
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r16 | 0.998799 | 0.049079 | 0.048642 | 0.018723 | 256 | 0 | 660624 |
| 4096 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r4 | 0.998473 | 0.055319 | 0.054713 | 0.024781 | 1024 | 0 | 583056 |
| 4096 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r8 | 0.998705 | 0.050947 | 0.050722 | 0.020029 | 512 | 0 | 608912 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r16 | 0.998772 | 0.049594 | 0.049041 | 0.018597 | 512 | 0 | 660624 |
| 8192 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r4 | 0.998398 | 0.056605 | 0.055317 | 0.022331 | 2048 | 0 | 583056 |
| 8192 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_b32_r8 | 0.998651 | 0.051942 | 0.051213 | 0.024283 | 1024 | 0 | 608912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

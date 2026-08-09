# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-06T08:47:30.238112+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 1.0
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `ed053c1383046c2953466d546669041e2d1125381ef136cf20a27548a507aa1a`
Token CSV: `reports/benchmark/corrected/mxfp4_rs2_candidate/extended_development/seed_0000fb72_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/mxfp4_rs2_candidate/extended_development/seed_0000fb72_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/mxfp4_rs2_candidate/extended_development/seed_0000fb72_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.998091 | 0.061848 | 0.060475 | 0.060614 | 32 | 0 | 570512 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.996334 | 0.085711 | 0.086259 | 0.127809 | 128 | 0 | 570512 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.995913 | 0.090453 | 0.091227 | 0.129677 | 512 | 0 | 570512 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.995951 | 0.090260 | 0.091243 | 0.111359 | 2048 | 0 | 570512 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.996034 | 0.089285 | 0.091624 | 0.123389 | 4096 | 0 | 570512 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

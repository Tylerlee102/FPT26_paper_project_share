# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T00:12:57.673945+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `cancellation`
Initial state: `zero`
Base residual-block fraction: 0.75
Tokens/checkpoints: 1024 / 64, 256, 1024
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `d8d655f0ffc7c640345b92b70a69542e1b8b4cad3765bfa87f2b70b9d92c4bc3`
Token CSV: `reports/benchmark/corrected/write_log_development_stress_1024/development_seed0000fb72_cancellation_zero_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_development_stress_1024/development_seed0000fb72_cancellation_zero_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_development_stress_1024/development_seed0000fb72_cancellation_zero_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999829 | 0.018567 | 0.100054 | 0.028808 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999836 | 0.018135 | 0.097598 | 0.021849 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999821 | 0.018908 | 0.098298 | 0.024603 | 146 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

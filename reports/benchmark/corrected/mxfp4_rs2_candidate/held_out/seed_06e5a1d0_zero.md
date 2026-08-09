# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-06T08:41:53.353329+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `held_out` / `0x6e5a1d0` / `high_retention`
Initial state: `zero`
Base residual-block fraction: 1.0
Tokens/checkpoints: 1024 / 64, 256, 1024
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `d80a37b38dd9bc2fdb65d2332d9eaba8cb1136f73b3c68145a09942c1fbec752`
Token CSV: `reports/benchmark/corrected/mxfp4_rs2_candidate/held_out/seed_06e5a1d0_zero_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/mxfp4_rs2_candidate/held_out/seed_06e5a1d0_zero_checkpoints.csv`
Manifest: `reports/benchmark/corrected/mxfp4_rs2_candidate/held_out/seed_06e5a1d0_zero_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.998241 | 0.059329 | 0.058574 | 0.061388 | 32 | 0 | 570512 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.996292 | 0.086163 | 0.086056 | 0.129684 | 128 | 0 | 570512 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_dense_base_b32_mxfp4_rs2_log_fixed_b32_r2 | 0.995633 | 0.093774 | 0.091212 | 0.116355 | 512 | 0 | 570512 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

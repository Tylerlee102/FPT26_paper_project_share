# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-01T23:43:15.040645+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `nominal`
Initial state: `random`
Base residual-block fraction: 0.5
Tokens/checkpoints: 256 / 64, 256
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `4f2c5cf6e2fe90466dcbadfe7144dc79f3d1d0ba1ea9869ad2f658b791eae7c7`
Token CSV: `reports/benchmark/corrected/write_log_sparse50_256_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_sparse50_256_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_sparse50_256_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse50_base_b32_mxfp8_log_fixed_b32_r8 | 0.994449 | 0.105224 | 0.131338 | 0.053045 | 8 | 0 | 473744 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse50_base_b32_mxfp8_log_fixed_b32_r8 | 0.994051 | 0.109017 | 0.135863 | 0.057106 | 32 | 0 | 473744 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T00:15:08.134584+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `adversarial`
Initial state: `zero`
Base residual-block fraction: 0.75
Tokens/checkpoints: 1024 / 64, 256, 1024
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `0cd633ba69b48cac9e0d3d6a153ba2329588387add8acbc5aad7c56e7750e94b`
Token CSV: `reports/benchmark/corrected/write_log_development_stress_1024/development_seed0000fb72_adversarial_zero_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_development_stress_1024/development_seed0000fb72_adversarial_zero_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_development_stress_1024/development_seed0000fb72_adversarial_zero_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 1.000000 | 0.005630 | 0.008149 | 0.005537 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998983 | 0.052486 | 0.087392 | 1.383587 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.998930 | 0.046337 | 0.041390 | 0.762533 | 146 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

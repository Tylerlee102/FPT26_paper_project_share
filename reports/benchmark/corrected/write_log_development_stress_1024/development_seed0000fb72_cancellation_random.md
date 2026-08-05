# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T00:12:35.441226+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `cancellation`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 1024 / 64, 256, 1024
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `0ca7a197a4a6bce4548243b64afc672788e376881e67aa493445c81c23d931e1`
Token CSV: `reports/benchmark/corrected/write_log_development_stress_1024/development_seed0000fb72_cancellation_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_development_stress_1024/development_seed0000fb72_cancellation_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_development_stress_1024/development_seed0000fb72_cancellation_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999810 | 0.019530 | 0.106737 | 0.026556 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999840 | 0.017908 | 0.097435 | 0.026837 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.999825 | 0.018739 | 0.098447 | 0.026587 | 146 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

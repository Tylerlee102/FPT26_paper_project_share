# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T00:09:30.345381+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `held_out` / `0x5eed5` / `nominal`
Initial state: `zero`
Base residual-block fraction: 0.75
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `c70f5b9f8f32f77c81924fb8918f62087ae9ff9c1d61f1378297c79ea113919d`
Token CSV: `reports/benchmark/corrected/write_log_held_out_zero/held_out_seed0005eed5_nominal_zero_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_held_out_zero/held_out_seed0005eed5_nominal_zero_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_held_out_zero/held_out_seed0005eed5_nominal_zero_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995648 | 0.093285 | 0.094360 | 0.042624 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995738 | 0.092251 | 0.092205 | 0.040137 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.994799 | 0.101901 | 0.097418 | 0.043342 | 146 | 0 | 536912 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.994163 | 0.107920 | 0.099165 | 0.040242 | 585 | 0 | 536912 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995108 | 0.098911 | 0.096796 | 0.039349 | 1170 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

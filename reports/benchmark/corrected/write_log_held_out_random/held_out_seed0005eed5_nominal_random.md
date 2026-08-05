# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T00:00:22.164251+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `held_out` / `0x5eed5` / `nominal`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `733d151692403b4af4a7431da4d1d0fecc2ba7b3b48707d6e8f79ce90fa6a936`
Token CSV: `reports/benchmark/corrected/write_log_held_out_random/held_out_seed0005eed5_nominal_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_held_out_random/held_out_seed0005eed5_nominal_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_held_out_random/held_out_seed0005eed5_nominal_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995331 | 0.096780 | 0.096437 | 0.041631 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995673 | 0.092942 | 0.092432 | 0.040293 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.994910 | 0.100855 | 0.097279 | 0.043993 | 146 | 0 | 536912 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.994366 | 0.106001 | 0.099050 | 0.040400 | 585 | 0 | 536912 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995155 | 0.098367 | 0.096628 | 0.041174 | 1170 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

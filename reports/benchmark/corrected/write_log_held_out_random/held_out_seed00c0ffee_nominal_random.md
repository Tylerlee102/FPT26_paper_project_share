# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-01T23:57:24.892398+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `held_out` / `0xc0ffee` / `nominal`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `80db82cb7005aeb14abbf56455238e8e414babc15f6498162dc1e7bc599785e7`
Token CSV: `reports/benchmark/corrected/write_log_held_out_random/held_out_seed00c0ffee_nominal_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_held_out_random/held_out_seed00c0ffee_nominal_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_held_out_random/held_out_seed00c0ffee_nominal_random_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995115 | 0.098946 | 0.097425 | 0.043333 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995438 | 0.095421 | 0.093758 | 0.041417 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995219 | 0.097752 | 0.097360 | 0.038406 | 146 | 0 | 536912 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995407 | 0.095754 | 0.098438 | 0.046367 | 585 | 0 | 536912 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995419 | 0.095618 | 0.096362 | 0.039809 | 1170 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

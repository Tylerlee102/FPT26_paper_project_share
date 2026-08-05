# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-02T00:06:32.989308+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `held_out` / `0xc0ffee` / `nominal`
Initial state: `zero`
Base residual-block fraction: 0.75
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `247856de1a098c5d1623e32c40db5a1134e3729acdb11a09b0432e4ee5212a1c`
Token CSV: `reports/benchmark/corrected/write_log_held_out_zero/held_out_seed00c0ffee_nominal_zero_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_held_out_zero/held_out_seed00c0ffee_nominal_zero_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_held_out_zero/held_out_seed00c0ffee_nominal_zero_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995287 | 0.097102 | 0.095745 | 0.040857 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995550 | 0.094257 | 0.093773 | 0.048821 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995104 | 0.098881 | 0.097534 | 0.041089 | 146 | 0 | 536912 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995540 | 0.094363 | 0.098385 | 0.041221 | 585 | 0 | 536912 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.995603 | 0.093726 | 0.096047 | 0.053598 | 1170 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

# Dense E2M0 Fold-Residual Development Diagnostic

Generated: 2026-08-02T08:32:49.568768+00:00
Engineering gate at executed length: `PASS`
Variant: `mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7`
Split/seed/family: `held_out` / `0xbadc0de` / `nominal`
Initial state: `random`
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Logical recurrent-state bytes: 538256
Input-stream SHA256: `1102387ae2abe32e818edb1e379b104489a6ea6e1636c86323c4d275ccee7e09`
Token CSV: `reports/benchmark/corrected/e2m0_residual/held_out/held_out_seed0badc0de_nominal_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/e2m0_residual/held_out/held_out_seed0badc0de_nominal_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/e2m0_residual/held_out/held_out_seed0badc0de_nominal_random_manifest.json`

The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The write log uses two residual-stacked MXFP4 terms; fold schedule, recurrence boundary, and activation stack are unchanged.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998519 | 0.054415 | 0.051477 | 0.027489 | 9 | 0 | 538256 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998713 | 0.050744 | 0.049178 | 0.024346 | 36 | 0 | 538256 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998458 | 0.055569 | 0.052571 | 0.027325 | 146 | 0 | 538256 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998512 | 0.054562 | 0.052220 | 0.023866 | 585 | 0 | 538256 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998749 | 0.050028 | 0.051088 | 0.026231 | 1170 | 0 | 538256 |

This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.

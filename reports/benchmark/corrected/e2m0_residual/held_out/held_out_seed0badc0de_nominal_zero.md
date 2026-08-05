# Dense E2M0 Fold-Residual Development Diagnostic

Generated: 2026-08-02T08:35:43.997277+00:00
Engineering gate at executed length: `PASS`
Variant: `mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7`
Split/seed/family: `held_out` / `0xbadc0de` / `nominal`
Initial state: `zero`
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Logical recurrent-state bytes: 538256
Input-stream SHA256: `2a346b3cd5f214036e5a09a1fe45309f6816162c69aacab5e432d36eb6007888`
Token CSV: `reports/benchmark/corrected/e2m0_residual/held_out/held_out_seed0badc0de_nominal_zero_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/e2m0_residual/held_out/held_out_seed0badc0de_nominal_zero_checkpoints.csv`
Manifest: `reports/benchmark/corrected/e2m0_residual/held_out/held_out_seed0badc0de_nominal_zero_manifest.json`

The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The write log uses two residual-stacked MXFP4 terms; fold schedule, recurrence boundary, and activation stack are unchanged.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998616 | 0.052602 | 0.050272 | 0.025903 | 9 | 0 | 538256 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998712 | 0.050786 | 0.049140 | 0.019697 | 36 | 0 | 538256 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998476 | 0.055191 | 0.052588 | 0.026419 | 146 | 0 | 538256 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998568 | 0.053527 | 0.052257 | 0.028611 | 585 | 0 | 538256 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.998741 | 0.050178 | 0.051061 | 0.026231 | 1170 | 0 | 538256 |

This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.

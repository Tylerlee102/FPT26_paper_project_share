# Dense E2M0 Fold-Residual Development Diagnostic

Generated: 2026-08-02T08:27:04.546291+00:00
Engineering gate at executed length: `PASS`
Variant: `mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7`
Split/seed/family: `held_out` / `0xd15ea5e` / `high_retention`
Initial state: `random`
Tokens/checkpoints: 8192 / 64, 256, 1024, 4096, 8192
Logical recurrent-state bytes: 538256
Input-stream SHA256: `121c161b0c15034604232c3f0363059044bb50d6a2f650182a302a5928ed6a1b`
Token CSV: `reports/benchmark/corrected/e2m0_residual/held_out/held_out_seed0d15ea5e_high_retention_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/e2m0_residual/held_out/held_out_seed0d15ea5e_high_retention_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/e2m0_residual/held_out/held_out_seed0d15ea5e_high_retention_random_manifest.json`

The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The write log uses two residual-stacked MXFP4 terms; fold schedule, recurrence boundary, and activation stack are unchanged.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.997920 | 0.064462 | 0.064112 | 0.070668 | 9 | 0 | 538256 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.995913 | 0.090314 | 0.089617 | 0.166470 | 36 | 0 | 538256 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.994885 | 0.101026 | 0.095419 | 0.175805 | 146 | 0 | 538256 |
| 4096 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 4096 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.995357 | 0.096247 | 0.096090 | 0.149585 | 585 | 0 | 538256 |
| 8192 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 8192 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.995438 | 0.095473 | 0.095437 | 0.166261 | 1170 | 0 | 538256 |

This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.

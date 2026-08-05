# Dense E2M0 Fold-Residual Development Diagnostic

Generated: 2026-08-02T08:10:16.065781+00:00
Engineering gate at executed length: `PASS`
Variant: `mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7`
Split/seed/family: `development` / `0xfb72` / `adversarial`
Initial state: `random`
Tokens/checkpoints: 1024 / 64, 256, 1024
Logical recurrent-state bytes: 538256
Input-stream SHA256: `2d5049d4ea126f51f7ed77722340189a6a14cecd43551f4bb07964f531f021f2`
Token CSV: `reports/benchmark/corrected/e2m0_residual/development_robustness/development_seed0000fb72_adversarial_random_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/e2m0_residual/development_robustness/development_seed0000fb72_adversarial_random_checkpoints.csv`
Manifest: `reports/benchmark/corrected/e2m0_residual/development_robustness/development_seed0000fb72_adversarial_random_manifest.json`

The base stores one dense E2M1/E8M0 MXFP4 term and one dense 3-bit E2M0-style residual term. Each residual block chooses between adjacent E8M0 scales by squared reconstruction error. The write log uses two residual-stacked MXFP4 terms; fold schedule, recurrence boundary, and activation stack are unchanged.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.999947 | 0.011723 | 0.018493 | 0.022991 | 9 | 0 | 538256 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.999913 | 0.029084 | 0.094668 | 1.134593 | 36 | 0 | 538256 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_mxfp4_e2m0rs2_base_b32_mxfp4rs2_log_fixed_b32_r7 | 0.999851 | 0.031513 | 0.011288 | 0.138772 | 146 | 0 | 538256 |

This is development-only synthetic software evidence. It is not encoded-integer, RTL, physical-fit, energy, board, or closed-loop model evidence.

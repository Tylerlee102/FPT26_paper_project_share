# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-06T08:27:56.094875+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `high_retention`
Initial state: `random`
Base residual-block fraction: 0.75
Tokens/checkpoints: 1024 / 64, 256, 1024
Residual-stack depths (activation/base): 2/2
Fold policy: fixed, minimum entries=1, decay threshold=0.85
Input-stream SHA256: `f36cdb646f79095ebc6b2eb93f2231b7f4f3fea58cd5c1e58f51314e7552a656`
Token CSV: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_random_sparse75_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_random_sparse75_checkpoints.csv`
Manifest: `reports/benchmark/corrected/mxfp4_rs2_base_capacity_sweep/high_retention_random_sparse75_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r3 | 0.985263 | 0.171504 | 0.166666 | 0.171074 | 21 | 0 | 511056 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r4 | 0.989170 | 0.146991 | 0.151002 | 0.217499 | 16 | 0 | 517520 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r5 | 0.991342 | 0.131370 | 0.130482 | 0.123624 | 12 | 0 | 523984 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r6 | 0.992273 | 0.124207 | 0.121752 | 0.125458 | 10 | 0 | 530448 |
| 64 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.992194 | 0.125003 | 0.119674 | 0.129397 | 9 | 0 | 536912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r3 | 0.967943 | 0.253014 | 0.247646 | 0.297374 | 85 | 0 | 511056 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r4 | 0.975132 | 0.223075 | 0.223247 | 0.256431 | 64 | 0 | 517520 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r5 | 0.978808 | 0.205763 | 0.202027 | 0.225632 | 51 | 0 | 523984 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r6 | 0.982773 | 0.185256 | 0.183461 | 0.202965 | 42 | 0 | 530448 |
| 256 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.984675 | 0.174908 | 0.171711 | 0.207100 | 36 | 0 | 536912 |
| 1024 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r3 | 0.966883 | 0.256954 | 0.263898 | 0.311995 | 341 | 0 | 511056 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r4 | 0.973329 | 0.230781 | 0.237212 | 0.289384 | 256 | 0 | 517520 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r5 | 0.977939 | 0.210362 | 0.211032 | 0.236052 | 204 | 0 | 523984 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r6 | 0.980804 | 0.195789 | 0.195394 | 0.209540 | 170 | 0 | 530448 |
| 1024 | mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 0.983090 | 0.184040 | 0.185116 | 0.198672 | 146 | 0 | 536912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

# Write-Log Candidate Selection

Status: **PASS** for a development-only configuration freeze. This is not a paper-readiness or hardware gate.

Selected variant: `mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7`.

| Variant | Tokens | Output cosine | State rel L2 | Logical bytes | vs BF16 | vs MXFP8 | Synthetic gate | Physical evidence |
|---|---:|---:|---:|---:|---:|---:|---|---|
| mxfp4_rs2_act_rs2_base_b32_mxfp8_log_fixed_b32_r16 | 8192 | 0.998772 | 0.049041 | 660624 | 36.998% | -22.186% | PASS | NOT_RUN |
| mxfp4_rs2_act_rs2_base_b32_mxfp8_log_fixed_b32_r4 | 8192 | 0.998398 | 0.055317 | 583056 | 44.395% | -7.839% | PASS | NOT_RUN |
| mxfp4_rs2_act_rs2_base_b32_mxfp8_log_fixed_b32_r8 | 8192 | 0.998651 | 0.051213 | 608912 | 41.930% | -12.621% | PASS | NOT_RUN |
| mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7 | 8192 | 0.994926 | 0.097767 | 536912 | 48.796% | 0.695% | PASS | NOT_RUN |

The selected point is the only tested full-8192 candidate that clears the frozen synthetic checkpoint gate while using fewer logical recurrent-state bytes than uniform MXFP8-B32. The seven-entry capacity is a development-tuned knee and must not be retuned after held-out access.

The dense R=4/8/16 comparison remains required evidence. Sparse 1/4 and 2/4 residual-base variants and sparse 3/4 R=4 failed and remain preserved in the benchmark directory.

Physical allocation, average and p99 service latency, energy, RTL parity, real-model quality, and board measurements remain `NOT_RUN` or `BLOCKED_EXTERNAL`. Logical storage does not establish a hardware Pareto result.

Machine-readable selection: `reports/benchmark/corrected/write_log_selection.json`.
Comparison CSV: `reports/benchmark/corrected/write_log_selection.csv`.

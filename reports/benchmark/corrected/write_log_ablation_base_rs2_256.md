# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-01T23:26:14.273811+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `nominal`
Tokens/checkpoints: 256 / 64, 256
Residual-stack depths (activation/base): 1/2
Input-stream SHA256: `4467ba807789ee33c6167b447abe9d3e280737cc264cc82bd034b49d9e7973bf`
Token CSV: `reports/benchmark/corrected/write_log_ablation_base_rs2_256_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_ablation_base_rs2_256_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_ablation_base_rs2_256_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs1_act_rs2_base_b32_mxfp8_log_b32_r8 | 0.978583 | 0.206128 | 0.170197 | 0.079451 | 8 | 0 | 608912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs1_act_rs2_base_b32_mxfp8_log_b32_r8 | 0.979100 | 0.203813 | 0.172722 | 0.065543 | 32 | 0 | 608912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

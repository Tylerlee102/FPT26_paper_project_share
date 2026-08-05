# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-01T23:28:11.909092+00:00
Engineering gate at executed length: `PASS`
Split/seed/family: `development` / `0xfb72` / `nominal`
Tokens/checkpoints: 256 / 64, 256
Residual-stack depths (activation/base): 2/2
Fold policy: decay_threshold, minimum entries=4, decay threshold=0.85
Input-stream SHA256: `4467ba807789ee33c6167b447abe9d3e280737cc264cc82bd034b49d9e7973bf`
Token CSV: `reports/benchmark/corrected/write_log_adaptive_d850_256_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_adaptive_d850_256_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_adaptive_d850_256_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_adaptive_decay850_b32_r8 | 0.998632 | 0.052309 | 0.050361 | 0.024303 | 9 | 0 | 608912 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_rs2_act_rs2_base_b32_mxfp8_log_adaptive_decay850_b32_r8 | 0.998767 | 0.049672 | 0.050614 | 0.019798 | 36 | 0 | 608912 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

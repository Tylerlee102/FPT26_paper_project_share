# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-01T23:12:02.513423+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `nominal`
Tokens/checkpoints: 256 / 64, 256
Input-stream SHA256: `4467ba807789ee33c6167b447abe9d3e280737cc264cc82bd034b49d9e7973bf`
Token CSV: `reports/benchmark/corrected/write_log_pilot_fp32log_256_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_pilot_fp32log_256_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_pilot_fp32log_256_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_base_b32_fp32_log_b32_r128 | 0.978986 | 0.204171 | 0.167633 | 0.076167 | 0 | 0 | 3440784 |
| 64 | mxfp4_base_b32_fp32_log_b32_r16 | 0.975338 | 0.220970 | 0.222502 | 0.095076 | 4 | 0 | 673936 |
| 64 | mxfp4_base_b32_fp32_log_b32_r32 | 0.977762 | 0.209938 | 0.208528 | 0.095076 | 2 | 0 | 1069200 |
| 64 | mxfp4_base_b32_fp32_log_b32_r64 | 0.978986 | 0.204171 | 0.203322 | 0.095076 | 1 | 0 | 1859728 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_base_b32_fp32_log_b32_r128 | 0.979600 | 0.201380 | 0.204645 | 0.078189 | 2 | 0 | 3440784 |
| 256 | mxfp4_base_b32_fp32_log_b32_r16 | 0.975313 | 0.221418 | 0.226705 | 0.087114 | 16 | 0 | 673936 |
| 256 | mxfp4_base_b32_fp32_log_b32_r32 | 0.978383 | 0.207271 | 0.211158 | 0.078189 | 8 | 0 | 1069200 |
| 256 | mxfp4_base_b32_fp32_log_b32_r64 | 0.979384 | 0.202431 | 0.205349 | 0.078189 | 4 | 0 | 1859728 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

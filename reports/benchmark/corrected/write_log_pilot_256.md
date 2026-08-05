# Lazy MXFP4 Base / MXFP8 Write-Log Development Diagnostic

Generated: 2026-08-01T23:11:08.800995+00:00
Engineering gate at executed length: `FAIL`
Split/seed/family: `development` / `0xfb72` / `nominal`
Tokens/checkpoints: 256 / 64, 256
Input-stream SHA256: `4467ba807789ee33c6167b447abe9d3e280737cc264cc82bd034b49d9e7973bf`
Token CSV: `reports/benchmark/corrected/write_log_pilot_256_tokens.csv`
Checkpoint CSV: `reports/benchmark/corrected/write_log_pilot_256_checkpoints.csv`
Manifest: `reports/benchmark/corrected/write_log_pilot_256_manifest.json`

The candidate uses paired Q/K-head key sharing, per-value-head decay coefficients, no-drop fixed-capacity logs, and atomic all-head folds. Output is evaluated before a full-log fold; resident-state metrics use the post-fold MXFP4 base, matching the output-before-state-requantization boundary.

| Token | Variant | Output cosine | Output rel L2 | State rel L2 | State max abs | Folds | Dropped | Logical bytes |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 64 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 64 | mxfp4_base_b32_mxfp8_log_b32_r16 | 0.974808 | 0.223352 | 0.224015 | 0.095076 | 4 | 0 | 382096 |
| 64 | mxfp4_base_b32_mxfp8_log_b32_r4 | 0.953086 | 0.305953 | 0.313691 | 0.251609 | 16 | 0 | 304528 |
| 64 | mxfp4_base_b32_mxfp8_log_b32_r8 | 0.968876 | 0.248047 | 0.252454 | 0.101063 | 8 | 0 | 330384 |
| 256 | fp32 | 1.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 2097152 |
| 256 | mxfp4_base_b32_mxfp8_log_b32_r16 | 0.974903 | 0.223238 | 0.228140 | 0.096793 | 16 | 0 | 382096 |
| 256 | mxfp4_base_b32_mxfp8_log_b32_r4 | 0.950999 | 0.314410 | 0.329279 | 0.278275 | 64 | 0 | 304528 |
| 256 | mxfp4_base_b32_mxfp8_log_b32_r8 | 0.968419 | 0.250092 | 0.258889 | 0.103678 | 32 | 0 | 330384 |

This is G3 synthetic software evidence only. It is not encoded-integer, RTL, placed-memory, board-energy, or closed-loop model evidence.

# Held-Out Synthetic Write-Log Stability

Status: **PASS** for the preregistered nominal synthetic engineering gate.

Configuration was frozen by `reports/benchmark/corrected/write_log_selection.json` before held-out access. Six traces cover three held-out seeds and both random and zero initial recurrent states.

| Initial state | Seed | Token 8192 cosine | Token 8192 state rel L2 | State max abs | Drops |
|---|---:|---:|---:|---:|---:|
| random | 388821 | 0.995155 | 0.096628 | 0.041174 | 0 |
| random | 659918 | 0.995127 | 0.098545 | 0.040570 | 0 |
| random | 12648430 | 0.995419 | 0.096362 | 0.039809 | 0 |
| zero | 388821 | 0.995108 | 0.096796 | 0.039349 | 0 |
| zero | 659918 | 0.995070 | 0.098834 | 0.038369 | 0 |
| zero | 12648430 | 0.995603 | 0.096047 | 0.053598 | 0 |

Worst output cosine over all 30 required checkpoints: `0.994163`.
Worst token-8192 state relative L2 over six traces: `0.098834`.

This passes the synthetic engineering threshold but does not establish encoded arithmetic parity, physical FPGA fit/energy, perplexity, downstream accuracy, or realistic closed-loop model quality.

Summary CSV: `reports/benchmark/corrected/write_log_held_out_summary.csv`.
Statistics CSV: `reports/benchmark/corrected/write_log_held_out_checkpoint_stats.csv`.
Manifest: `reports/benchmark/corrected/write_log_held_out_manifest.json`.

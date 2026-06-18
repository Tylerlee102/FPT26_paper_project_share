# Long-Token Synthetic State Drift

Generated: 2026-06-18T01:49:13.857171+00:00
Source: deterministic synthetic token stream, seed `0xfb72`
Shape: num_heads=32, head_dim=128
Tokens: 1024
MXFP4 activation block size: 32
State block size: 16
CSV: `reports/benchmark/state_drift.csv`

This run reuses one evolving FP32 state, one evolving MXFP4-state path, and one evolving MXFP8-state path over the same synthetic token stream. It is a stress test for recurrent-state error accumulation, not a Qwen3-Next perplexity result.

| State path | Final output cosine | Final output rel L2 | Final state rel L2 | Worst output cosine | Worst state rel L2 | Mean output cosine | Mean state rel L2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| MXFP4 state | 0.643261 | 0.863224 | 0.864949 | 0.593851 | 0.865468 | 0.720029 | 0.716441 |
| MXFP8 state | 0.932588 | 0.365871 | 0.343599 | 0.922341 | 0.344457 | 0.941956 | 0.301127 |

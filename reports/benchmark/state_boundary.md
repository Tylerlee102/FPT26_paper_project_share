# Recurrent-State Precision Boundary

Generated: 2026-06-18T01:33:31.866499+00:00
Source: deterministic synthetic token stream, seed `0xfb72`
Shape: num_heads=32, head_dim=128
Tokens simulated: 256
Checkpoints: 64, 256
Activation block size: 32
CSV: `reports/benchmark/state_boundary.csv`

This recurrent test compares MXFP4 and MXFP8 state storage at block sizes 16 and 32. It is synthetic fidelity evidence, not a Qwen3-Next perplexity result.

## Token 64

| State config | Output cosine | Output rel L2 | State cosine | State rel L2 |
|---|---:|---:|---:|---:|
| state_mxfp4_b16 | 0.878184 | 0.486293 | 0.887978 | 0.461649 |
| state_mxfp4_b32 | 0.867094 | 0.508570 | 0.881078 | 0.476595 |
| state_mxfp8_b16 | 0.966323 | 0.262271 | 0.978564 | 0.206113 |
| state_mxfp8_b32 | 0.966323 | 0.262271 | 0.978564 | 0.206113 |

## Token 256

| State config | Output cosine | Output rel L2 | State cosine | State rel L2 |
|---|---:|---:|---:|---:|
| state_mxfp4_b16 | 0.747457 | 0.684037 | 0.775063 | 0.646596 |
| state_mxfp4_b32 | 0.734638 | 0.707965 | 0.761473 | 0.670563 |
| state_mxfp8_b16 | 0.945410 | 0.328639 | 0.959690 | 0.281874 |
| state_mxfp8_b32 | 0.945410 | 0.328639 | 0.959690 | 0.281874 |

# Quantization Report

Generated: 2026-06-18T04:07:38.635046+00:00
Source: synthetic
Vectors: 16
Shape: num_heads=32, head_dim=128

This offline Phase 2 run uses deterministic synthetic vectors. Qwen3-Next activation capture and Microsoft microxcaling parity remain external-dependency checks for the full acceptance run.

| Configuration | Output rel L2 | Output max abs | Output cosine | State rel L2 |
|---|---:|---:|---:|---:|
| MXFP4 B=32, state MXFP4 B=16 | 0.191360 | 0.031543 | 0.981823 | 0.117550 |
| MXFP4 B=32, state MXFP8 B=16 | 0.158986 | 0.027094 | 0.987517 | 0.048842 |
| INT4 fallback | 0.266244 | 0.043884 | 0.966696 | 0.207030 |

# Quantization Report

Generated: 2026-05-04T22:03:11.288442+00:00
Source: synthetic
Vectors: 16
Shape: num_heads=32, head_dim=128

This offline Phase 2 run uses deterministic synthetic vectors. Qwen3-Next activation capture and Microsoft microxcaling parity remain external-dependency checks for the full acceptance run.

| Configuration | Output rel L2 | Output max abs | Output cosine | State rel L2 |
|---|---:|---:|---:|---:|
| MXFP4 B=16, state MXFP4 B=16 | 0.188740 | 0.031011 | 0.982292 | 0.117084 |
| MXFP4 B=16, state MXFP8 B=16 | 0.155829 | 0.028010 | 0.987987 | 0.047729 |
| INT4 fallback | 0.266244 | 0.043884 | 0.966696 | 0.207030 |

# Quantization Ablation

Each row quantizes one tensor to MXFP4 while keeping the rest in FP32.

| Tensor | Output rel L2 | Output max abs | Output cosine | State rel L2 |
|---|---:|---:|---:|---:|
| q | 0.118668 | 0.020003 | 0.992969 | 0.000000 |
| k | 0.030455 | 0.010387 | 0.999523 | 0.030405 |
| v | 0.028568 | 0.011100 | 0.999580 | 0.028461 |
| gate | 0.093920 | 0.019111 | 0.995668 | 0.000000 |
| state | 0.110824 | 0.018011 | 0.993845 | 0.109891 |

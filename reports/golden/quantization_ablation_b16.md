# Quantization Ablation

Each row quantizes one tensor to MXFP4 while keeping the rest in FP32.

| Tensor | Output rel L2 | Output max abs | Output cosine | State rel L2 |
|---|---:|---:|---:|---:|
| q | 0.114815 | 0.018934 | 0.993411 | 0.000000 |
| k | 0.028928 | 0.009476 | 0.999568 | 0.029281 |
| v | 0.027903 | 0.011100 | 0.999599 | 0.027772 |
| gate | 0.093920 | 0.019111 | 0.995668 | 0.000000 |
| state | 0.110824 | 0.018011 | 0.993845 | 0.109891 |

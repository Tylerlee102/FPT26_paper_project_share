# Synthetic Stress Accuracy Sweep

Generated: 2026-06-18T01:25:41.972518+00:00
Seeds: 0xfb72, 0xfb73, 0xfb74, 0xfb75, 0xfb76
Vectors per seed/distribution/config: 8
Shape: num_heads=32, head_dim=128
Activation block size: 32
CSV: `reports/benchmark/stress_accuracy.csv`

This is a one-step synthetic stress sweep. It broadens the numerical-fidelity evidence when real Qwen3-Next activation capture is unavailable; it is not a perplexity result.

| Distribution | State config | Mean output cosine | Worst output cosine | Mean output rel L2 | Worst output rel L2 | Mean state rel L2 | Worst state rel L2 |
|---|---|---:|---:|---:|---:|---:|---:|
| combined_stress | state_mxfp4_b16 | 0.973611 | 0.927967 | 0.235440 | 0.390952 | 0.163108 | 0.210992 |
| combined_stress | state_mxfp4_b32 | 0.972003 | 0.925200 | 0.242374 | 0.396185 | 0.172806 | 0.215438 |
| combined_stress | state_mxfp8_b16 | 0.979034 | 0.934722 | 0.210543 | 0.376418 | 0.124285 | 0.195172 |
| combined_stress | state_mxfp8_b32 | 0.979034 | 0.934722 | 0.210543 | 0.376418 | 0.124285 | 0.195172 |
| gaussian | state_mxfp4_b16 | 0.981705 | 0.980621 | 0.191634 | 0.197064 | 0.117438 | 0.119231 |
| gaussian | state_mxfp4_b32 | 0.981361 | 0.980176 | 0.193509 | 0.199572 | 0.120450 | 0.122145 |
| gaussian | state_mxfp8_b16 | 0.987374 | 0.986751 | 0.159559 | 0.163530 | 0.048347 | 0.055282 |
| gaussian | state_mxfp8_b32 | 0.987374 | 0.986751 | 0.159559 | 0.163530 | 0.048347 | 0.055282 |
| high_beta | state_mxfp4_b16 | 0.981071 | 0.978915 | 0.194920 | 0.204685 | 0.122777 | 0.123437 |
| high_beta | state_mxfp4_b32 | 0.980770 | 0.978582 | 0.196523 | 0.206339 | 0.125407 | 0.126046 |
| high_beta | state_mxfp8_b16 | 0.986298 | 0.984216 | 0.166080 | 0.177240 | 0.068290 | 0.069805 |
| high_beta | state_mxfp8_b32 | 0.986298 | 0.984216 | 0.166080 | 0.177240 | 0.068290 | 0.069805 |
| laplace | state_mxfp4_b16 | 0.979029 | 0.976952 | 0.205391 | 0.214675 | 0.128173 | 0.130088 |
| laplace | state_mxfp4_b32 | 0.977995 | 0.975689 | 0.210599 | 0.220780 | 0.136407 | 0.138121 |
| laplace | state_mxfp8_b16 | 0.985755 | 0.984273 | 0.169517 | 0.177756 | 0.053011 | 0.059644 |
| laplace | state_mxfp8_b32 | 0.985755 | 0.984273 | 0.169517 | 0.177756 | 0.053011 | 0.059644 |
| outlier | state_mxfp4_b16 | 0.974671 | 0.967520 | 0.227115 | 0.257322 | 0.149513 | 0.159022 |
| outlier | state_mxfp4_b32 | 0.972567 | 0.965293 | 0.236552 | 0.264594 | 0.163727 | 0.171390 |
| outlier | state_mxfp8_b16 | 0.981290 | 0.973401 | 0.195258 | 0.232971 | 0.094263 | 0.114350 |
| outlier | state_mxfp8_b32 | 0.981290 | 0.973401 | 0.195258 | 0.232971 | 0.094263 | 0.114350 |
| sparse_gate | state_mxfp4_b16 | 0.981709 | 0.978826 | 0.191736 | 0.205912 | 0.117633 | 0.119143 |
| sparse_gate | state_mxfp4_b32 | 0.981389 | 0.978305 | 0.193516 | 0.208433 | 0.120635 | 0.122053 |
| sparse_gate | state_mxfp8_b16 | 0.987305 | 0.984345 | 0.160157 | 0.177245 | 0.049159 | 0.055693 |
| sparse_gate | state_mxfp8_b32 | 0.987305 | 0.984345 | 0.160157 | 0.177245 | 0.049159 | 0.055693 |

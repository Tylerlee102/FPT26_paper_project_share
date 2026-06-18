# Recurrent-State Storage Overhead

Generated: 2026-06-18T00:40:19.103332+00:00
Shape: num_heads=32, head_dim=128, elements=524288
CSV: `reports/benchmark/storage_overhead.csv`

MXFP4 includes E8M0 scale metadata in this accounting. Scales are counted per block along the innermost state dimension.

| Format | Block size | Element bits | Scale bits/block | Total bytes | Relative to MXFP4 B=32 | Reduction vs FP32 | Reduction vs BF16 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FP32 | none | 32.0 | 0 | 2097152 | 7.529x | 0.000% | -100.000% |
| BF16/FP16 | none | 16.0 | 0 | 1048576 | 3.765x | 50.000% | 0.000% |
| INT8 | none | 8.0 | 0 | 524288 | 1.882x | 75.000% | 50.000% |
| Flat INT4 | none | 4.0 | 0 | 262144 | 0.941x | 87.500% | 75.000% |
| MXFP4 | 16 | 4.0 | 8 | 294912 | 1.059x | 85.938% | 71.875% |
| MXFP4 | 32 | 4.0 | 8 | 278528 | 1.000x | 86.719% | 73.438% |

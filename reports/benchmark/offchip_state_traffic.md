# Off-Chip Recurrent-State Traffic Estimate

Generated: 2026-06-18T01:17:59.144095+00:00
Shape: num_heads=32, head_dim=128
CSV: `reports/benchmark/offchip_state_traffic.csv`

This estimate counts recurrent-state traffic only. The naive three-pass case reads old state for prediction, writes updated state, then reads updated state for output. The persistent-state datapath keeps state resident on chip after initialization, so steady-state off-chip recurrent-state traffic is zero.

| Format | Block size | State bytes | Read+write bytes/token | Naive three-pass bytes/token | Persistent steady-state bytes/token |
|---|---:|---:|---:|---:|---:|
| FP32 | none | 2097152 | 4194304 | 6291456 | 0 |
| BF16/FP16 | none | 1048576 | 2097152 | 3145728 | 0 |
| INT8 | none | 524288 | 1048576 | 1572864 | 0 |
| MXFP4 | 16 | 294912 | 589824 | 884736 | 0 |
| MXFP4 | 32 | 278528 | 557056 | 835584 | 0 |

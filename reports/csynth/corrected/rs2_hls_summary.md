# Native MXFP4 RS2/R3 HLS Gate

Generated: `2026-08-06T15:38:25.589986+00:00`
Status: `PASS`

- Exact C simulation: `PASS` (64-token trace)
- Estimated Fmax: `321.96 MHz`
- Explicit II=1 constraints: `PASS` (38 loops)
- Estimated resources: `167082` LUT, `73831` FF, `74` BRAM18K, `88` URAM, `26` DSP
- Single-SLR LUT utilization: `38.45%`
- Phase-4 decision gate: `PASS`
- HLS LUT/latency advantage versus BF16: `FAIL`
- 64-token RTL cosimulation: `NOT_RUN`
- Routed fit/timing/power: `NOT_RUN`

Native MXFP4 RS2/R3 is numerically stable and HLS-feasible, but this stability mitigation does not beat the matched BF16 HLS estimate in LUTs or amortized cycles; routed evidence is required for the final cost answer.

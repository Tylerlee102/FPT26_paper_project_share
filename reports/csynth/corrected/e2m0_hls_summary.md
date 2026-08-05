# Corrected Encoded-MXFP4 HLS Evidence

Generated: `2026-08-02T17:51:40.561013+00:00`
Evidence extraction: `PASS`
Phase 4 decision gate: `FAIL`

- Arithmetic C-sim (267 cases): `PASS`
- Exact resident-state C-sim (64 tokens): `PASS`
- Estimated path: `3.108` ns
- Configured target-minus-uncertainty budget: `2.920` ns (`FAIL`, shortfall `0.188` ns)
- Non-folding STEP: `13276768` to `17954144` cycles
- Fold overhead every 7 tokens: `75342112` to `153952544` cycles
- Estimated logic: `435089` LUT, `124114` FF, `78` DSP
- Inferred BRAM/URAM counts: excluded from capacity conclusions
- Explicit II=1 constraints: `FAIL` (3 failed)
- HLS LUT-and-STEP advantage versus BF16: `FAIL`
- 64-token RTL parity, physical fit, post-route timing, and board energy: `NOT_RUN`

| Variant | Path (ns) | STEP max | Amortized per-layer cycles/STEP | LUT | FF | DSP |
|---|---:|---:|---:|---:|---:|---:|
| BF16 | 2.920 | 4225728 | 4225728.0 | 84919 | 39087 | 0 |
| uniform_mxfp4 | 2.920 | 6070592 | 6070592.0 | 138969 | 43962 | 3 |
| mxfp4_rs2_act_e2m1_e2m0_state_mxfp4rs2_log_r7_q1_15_int32_guard5 | 3.108 | 17954144 | 39947364.6 | 435089 | 124114 | 78 |

The reciprocal-path estimate clears 200 MHz but misses the configured
target-minus-uncertainty margin. The corrected candidate is larger and
slower than BF16 and still misses explicit II=1
constraints. It therefore does not establish an FPGA cost or energy win.
The corrected state/log representation is reported as a drift mitigation,
not as the controlled uniform-MXFP4 replacement.

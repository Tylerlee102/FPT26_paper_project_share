# Matched BF16 HLS Baseline

Generated: `2026-08-06T07:17:36.961870+00:00`
Status: `PASS` for source-locked HLS C-sim and C-synthesis extraction

- C-simulation: `PASS` (6 commands, 2 physical bank classes, generation 2)
- Target: `xcu55c-fsvh2892-2L-e`, `4.000` ns
- Estimated clock: `2.920` ns (`342.47` MHz)
- Estimated STEP loop: `4225856` to `4225856` cycles
- Estimated resources: `85350` LUT, `39270` FF, `269` BRAM18K, `128` URAM, `0` DSP
- Explicit II=1 loop constraints: `PASS` (19 loops)
- 64-token BF16 RTL parity: `NOT_RUN`
- Post-route timing/DRC: see `reports/vivado/baselines/bf16/bf16_vivado_summary.json`
- Measured board energy: `BLOCKED_EXTERNAL`

The baseline keeps the same recurrent boundary, KxV state layout, 36 layer slots,
P_K=16, P_V=8, block size 32, U55C target, and 4 ns constraint as the
uniform-MXFP4 kernel. BF16 operands are accumulated in FP32 and rounded to
BF16 at the persistent-state and output boundaries.

These are HLS estimates. The bounded C-simulation and inferred memory counts
do not establish RTL parity, physical fit, routed timing, or energy on their own.

# Matched BF16 HLS Baseline

Generated: `2026-08-02T03:40:41.656335+00:00`
Status: `PASS` for source-locked HLS C-sim and C-synthesis extraction

- C-simulation: `PASS` (4 commands, generation 2)
- Target: `xcu55c-fsvh2892-2L-e`, `4.000` ns
- Estimated clock: `2.920` ns (`342.47` MHz)
- Estimated STEP loop: `4225728` to `4225728` cycles
- Estimated resources: `84919` LUT, `39087` FF, `13` BRAM18K, `128` URAM, `0` DSP
- Explicit II=1 loop constraints: `PASS` (19 loops)
- 64-token BF16 RTL parity: `NOT_RUN`
- Post-route timing/DRC and energy: `NOT_RUN`

The baseline keeps the same recurrent boundary, KxV state layout, 36 layer slots,
P_K=16, P_V=8, block size 32, U55C target, and 4 ns constraint as the
uniform-MXFP4 kernel. BF16 operands are accumulated in FP32 and rounded to
BF16 at the persistent-state and output boundaries.

These are HLS estimates. The bounded C-simulation and inferred memory counts
do not establish RTL parity, physical fit, routed timing, or energy.

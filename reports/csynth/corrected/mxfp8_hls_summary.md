# Matched Native MXFP8 HLS Baseline

Generated: `2026-08-05T06:24:49.217212+00:00`
Status: `PASS` for source-locked arithmetic C-sim, kernel C-sim, and C-synthesis

- Arithmetic C-sim: `PASS` for 256 code checks, 253 valid coefficient products, 252 nonzero exact round trips, and 2 RNE midpoints
- Kernel C-sim: `PASS` for RESET, one exact nonzero STEP, and READBACK
- Target: `xcu55c-fsvh2892-2L-e`, `4.000` ns
- Estimated clock: `2.920` ns (`342.47` MHz)
- Estimated STEP loop: `5189952` to `6287680` cycles
- Estimated resources: `143084` LUT, `44715` FF, `25` BRAM18K, `64` URAM, `3` DSP
- Explicit II=1 loop constraints: `PASS` (14 loops)
- Long-trace RTL parity: `NOT_RUN`
- Board energy: `BLOCKED_EXTERNAL`

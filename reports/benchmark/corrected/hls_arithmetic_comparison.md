# Controlled HLS Arithmetic Comparison

Generated: `2026-08-05T17:04:12.616401+00:00`
Extraction status: `PASS`
HLS LUT-and-STEP advantage for uniform MXFP4: `FAIL`
Energy comparison: `BLOCKED_EXTERNAL_NO_U55C_DEVICE_OR_XRT`
Physical resource comparison: `NOT_RUN`

| Arithmetic | Estimated clock (ns) | STEP cycles (max) | LUT | FF | BRAM18K | Reported URAM | DSP |
|---|---:|---:|---:|---:|---:|---:|---:|
| BF16 | 2.920 | 4225728 | 84919 | 39087 | 13 | 128 | 0 |
| uniform_mxfp4 | 2.920 | 6070592 | 138969 | 43962 | 24 | 32 | 3 |
| native_mxfp8 | 2.920 | 6287680 | 143084 | 44715 | 25 | 64 | 3 |

Uniform MXFP4 uses `63.65%` more LUTs and its maximum estimated STEP loop is `43.66%` longer than BF16. Native MXFP8 uses `68.49%` more LUTs and `48.80%` more maximum STEP cycles. All three have the same `2.920` ns estimated clock.

This controlled HLS result does not support an FPGA cost or energy reduction
claim for the current uniform-MXFP4 implementation. Reported memory counts
are treated separately because an independent capacity lower bound exposes
under-counting of the declared deep state arrays.

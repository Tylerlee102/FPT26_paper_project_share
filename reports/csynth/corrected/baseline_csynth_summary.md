# Corrected Uniform-MXFP4 Baseline C-Synthesis

> **Historical point-in-time summary.** The synthesis values remain current raw
> HLS evidence for the native encoded uniform baseline, but the RTL sentence at
> the end predates the later direct 64-token generated-Verilog parity `PASS`.
> Raw BRAM/URAM totals are not physical-capacity evidence.

Generated: `2026-08-02T01:06:54.063596+00:00`

- Extraction status: `PASS`
- Target: `xcu55c-fsvh2892-2L-e` at `4.00` ns
- Estimated clock: `2.920` ns (`342.47` MHz)
- Top-level command latency range: `8238` to `12202887` cycles
- Resources: `138969` LUT, `43962` FF, `24` BRAM18K, `32` URAM, `3` DSP
- Reported SLR utilization: `31%` LUT, `5%` FF, `1%` BRAM18K, `10%` URAM
- Explicitly targeted loop II: `PASS` (14 loops)
- Vendor overall loop-constraint summary: `PASS`
- Source freshness: `PASS`
- Source equality with preceding 64-token C-sim: `PASS`

Vitis reports that all loop constraints were satisfied. Automatic
pipelining is disabled for control/transport loops; every explicitly
pipelined arithmetic and state loop reaches II=1.

This is an HLS estimate for the native encoded uniform-MXFP4 baseline. The
legacy Vitis-wrapper smoke failed on simulator memory, while the later bounded
direct harness passed one-token and 64-token RTL parity. Post-route timing/DRC,
physical power, and corrected-candidate RTL remain unverified.

# Vivado Evidence Summary

## Corrected E2M0 Candidate

The current corrected residual/write-log candidate has a source-locked,
out-of-context Vivado 2025.2 implementation on
`xcu55c-fsvh2892-2L-e`.

- Route completion: `PASS`
- Physical fit: `PASS`
- 250 MHz setup: `FAIL`, WNS `-1.540 ns`
- 200 MHz setup: `FAIL`, WNS `-0.540 ns`
- First passing tested fixed-route point: `5.55 ns`, `180.18 MHz`
- Hold at first passing point: `PASS`, WHS `0.010 ns`
- CLB LUTs: `208,523` (`15.99%`)
- FFs: `111,027` (`4.26%`)
- BRAM tiles: `353` (`17.51%`)
- URAMs: `624` (`65.0%`)
- DSPs: `44` (`0.49%`)
- DRC: `PASS_WITH_WARNINGS`, 38 warnings, no critical warnings or errors
- Vectorless power at 5.6 ns: `6.991 W` total, `3.582 W` dynamic,
  `3.410 W` static, `Medium` confidence

The critical path is a resident-state reset/write-enable path into URAM. Its
`4.971 ns` data path is `92.5%` routing and crosses from SLR1 to SLR0; it is not
an E2M1 multiplier path.

Authoritative extraction:
`reports/vivado/corrected/e2m0/e2m0_postroute_summary.json`.

This is an out-of-context implementation. No U55C shell, xclbin, bitstream
execution, XRT parity, board telemetry, or energy-per-token claim is available.
The power result is a vectorless estimate, not measured energy.

## Legacy Phase-5 Snapshot

The following values are preserved only for history. They were produced for an
earlier kernel/arithmetic contract and are not evidence for the corrected BF16,
native encoded MXFP4, or residual/write-log implementations.

- Synthesis WNS: `1.118 ns`
- Implementation WNS: `0.065 ns`
- LUT utilization: `6.64%`
- BRAM utilization: `3.67%`
- DSP utilization: `7.27%`
- Total on-chip power: `8.976 W`

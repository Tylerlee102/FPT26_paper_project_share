# Corrected Candidate Post-Route Evidence

Generated: `2026-08-04T10:22:11.126987+00:00`

- Extraction and integrity: `PASS`
- Device/tool: `xcu55c-fsvh2892-2L-e`, `Vivado v.2025.2 (win64) Build 6299465 Fri Nov 14 19:35:11 GMT 2025`
- Physical fit: `PASS`
- 250 MHz target: `FAIL` (WNS `-1.540` ns)
- 200 MHz: `FAIL` (WNS `-0.540` ns)
- First tested closing point: `5.55` ns (`180.18` MHz), WNS `0.010` ns, WHS `0.010` ns
- Critical path: `4.971` ns, `92.5%` routing, `5` logic levels; resident-state reset/write-enable path into URAM
- Resources: `208,523` CLB LUT, `111,027` FF, `353` BRAM tiles, `624` URAM, `44` DSP
- DRC: `PASS_WITH_WARNINGS` with `38` warnings and no critical warnings or errors
- Vectorless power at 5.60 ns: `6.991` W total, `3.582` W dynamic, `3.410` W static, `Medium` confidence
- Board power, energy per token, bitstream execution, and xclbin execution: `NOT_RUN`

The power row is a post-route vectorless estimate and must not be described as measured energy.

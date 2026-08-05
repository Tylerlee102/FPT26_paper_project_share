# Matched Native MXFP8 Post-Route Evidence

- Extraction and integrity: `PASS`
- Route completion: `PASS`
- Physical fit: `PASS`
- 250 MHz timing: `FAIL` (WNS `-1.355` ns, WHS `0.010` ns)
- First tested closing point: `6.000` ns (`166.67` MHz)
- Resources: `58582` CLB LUT, `39807` FF, `164.5` BRAM tiles, `576` URAM, `2` DSP
- DRC: `PASS_WITH_WARNINGS`
- Vectorless power at the first tested closing point: `4.952` W total (`Medium` confidence)
- Vivado sweep shutdown: `PASS`
- Board execution and measured energy: `BLOCKED_EXTERNAL`

The power result is not converted into energy per token.

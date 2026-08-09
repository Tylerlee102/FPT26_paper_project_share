# Selected Native MXFP4 RS2/R3 Post-Route Evidence

- Extraction and integrity: `PASS`
- Route completion: `PASS`
- Physical fit: `PASS`
- 250 MHz timing: `FAIL` (WNS `-1.736` ns, WHS `0.010` ns)
- First tested closing point: `6.000` ns (`166.67` MHz)
- Resources: `82038` CLB LUT, `69800` FF, `341` BRAM tiles, `598` URAM, `12` DSP
- DRC: `PASS_WITH_WARNINGS`
- Bounded 250 MHz repair attempts: `aggressive_fanout` WNS `-1.656` ns, `retiming` WNS `-1.656` ns, `slr_crossing` WNS `-1.736` ns, `explore` WNS `-1.690` ns, `aggressive_explore` WNS `-1.690` ns
- Vectorless power at the first tested closing point: `5.242` W total (`Medium` confidence)
- Vivado sweep shutdown: `PASS`
- Board execution and measured energy: `BLOCKED_EXTERNAL`

The power result is not converted into energy per token.

# Matched BF16 Post-Route Evidence

- Extraction and integrity: `PASS`
- Synthesis: `PASS`
- Placement: `PASS`
- Route: `PASS`
- Physical fit: `PASS`
- 250 MHz timing: `FAIL` (WNS `-3.020` ns, WHS `0.000` ns)
- First tested closing point: `7.125` ns (`140.35` MHz)
- Resources: `57942` CLB LUT, `38550` FF, `1602.5` BRAM tiles, `928` URAM, `15` DSP
- State banking: `29` layers in paired 256-bit URAM banks and `7` layers in paired 256-bit BRAM banks
- DRC: `PASS_WITH_WARNINGS`
- Vectorless power at first closure: `5.648` W total (`Medium` confidence)
- Board execution and measured energy: `BLOCKED_EXTERNAL`

The URAM-only raw-capacity lower bound still fails; the full 36-layer logical state fits by controlled hybrid URAM/BRAM banking.

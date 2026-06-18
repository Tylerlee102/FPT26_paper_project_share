# Native E2M1 MAC Evidence

Generated: 2026-06-18T00:40:19.033646+00:00
Source: `hls/src/mac_e2m1.cpp`
Testbench: `hls/tb/tb_mac_e2m1.cpp`

This report is source-level evidence for the native LUT-style E2M1 multiply primitive. Full design resource percentages are reported separately from HLS/Vivado synthesis reports because the top-level kernel also contains non-MAC fixed-point arithmetic and memory logic.

| Check | Result |
|---|---:|
| Product lookup table present | yes |
| Lookup table fully partitioned | yes |
| Floating-point keywords in MAC source | no |
| DSP pragma in MAC source | no |
| Exhaustive 16x16 testbench | yes |
| Pseudo-random regression cases | 100000 |

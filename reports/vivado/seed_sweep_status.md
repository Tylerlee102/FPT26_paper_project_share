# Vivado Placement Seed Sweep Status

Generated: 2026-06-18T02:11:28.407548+00:00
Implementation Tcl: `vivado/tcl/run_impl.tcl`

Status: not_run

Reason: the current non-project Vivado implementation flow invokes `place_design` directly and does not expose a verified placement-seed parameter. Re-running the same Tcl multiple times would not provide a controlled seed sweep, so no extra implementation runs were launched for this item.

| Current default implementation metric | Value |
|---|---:|
| Implementation WNS | 0.065 ns |
| LUT utilization | 6.64% |
| BRAM utilization | 3.67% |
| DSP utilization | 7.27% |
| Total on-chip power | 8.976 W |
| Seed parameter found in Tcl | no |

Recommended follow-up: convert the implementation flow to a project-run flow or add a verified Vivado seed parameter before reporting min/mean/max WNS across seeds.

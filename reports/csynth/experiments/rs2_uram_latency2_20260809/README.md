# RS2 two-cycle URAM experiment

This isolated variant adds `latency=2` to the four URAM bindings; it
does not modify or replace the selected RS2 source. Exact 64-token C
simulation and C synthesis pass, including every explicit II=1 constraint.

The HLS estimate remains 3.106 ns. Relative to the selected source, the
variant adds 1,145 FFs, 72 LUTs, and
20,480 worst-case cycles. The archived routed
path list is dominated by `resident_residual` URAM enable/write-control
endpoints, which output latency does not target. Routing was therefore not
run, and the variant is rejected rather than promoted.

## Artifact hashes

| Artifact | SHA256 |
|---|---|
| `csim_report_gdn_rs2_top_csim.log` | `5BA613CB91DF826E1DF06FD1C7CF672FB2E463BAAFCBFA0475460419DEBC3A3B` |
| `csim_solution_log_u55c_250mhz.log` | `48E928289602BC0AECB525C9B3233181528D6B459D55F7CBADFDE4A8150C638B` |
| `csynth_impl_report_gdn_rs2_top_impl_csynth.rpt` | `B64920C1D2DFAED9E2C6E8D4B7B9513F95A3D6E0C2011487154E26323315EB0F` |
| `csynth_solution_log_u55c_250mhz.log` | `FE5DC1227344912ABB8A6C8032975848CC039782D8693336D16EAE778A605851` |
| `csynth_top_report_gdn_rs2_top_csynth.rpt` | `53E8D50094F479C3100D77BCBA88268DA0E06719A098320427F44C1D21E4C103` |
| `csynth_top_xml_gdn_rs2_top_csynth.xml` | `42E964093F7847C5BECD1498BCA06A4874FF69FF0D99CB51C3B6BB79FF7BC5BA` |
| `derived_source_gdn_rs2_top.cpp` | `3027E675605140296A0ACEAFE4F80E408A58A0ECFBFF9A473DB953F0A3249E5B` |
| `generation_manifest_manifest.json` | `1DC638B114DD446EE751C08766F70F6C977D8B49C2C8D20D14E0F2F2A6F661AE` |

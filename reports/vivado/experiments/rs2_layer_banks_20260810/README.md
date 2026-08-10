# RS2 layer-local state-bank experiment

This source-isolated variant completely partitions the primary and
residual state stores by layer while preserving arithmetic, capacity,
commands, fold cadence, and the exact 64-token recurrent-state trace.

The routed result reaches -1.867 ns WNS and
-41,081.309 ns TNS with 54,809
failing setup endpoints. Hold and DRC pass, but 250 MHz setup does not.
The worst path has fanout 3 and runs from bank-local URAM read timing
through selector/fold logic, replacing rather than closing the prior
high-fanout write-enable bottleneck.

The variant adds substantial LUT and selector cost and is not promoted.
Vectorless power at the failed 4 ns constraint is diagnostic only.

## Artifact hashes

| Artifact | SHA256 |
|---|---|
| `csim_report_gdn_rs2_top_csim.log` | `412F00AAD8978C0E8EE61D8DA3E59800CEF19C5CBE3FCE1FEA5D6644DA188EC0` |
| `csim_solution_log_u55c_250mhz.log` | `C08B4A362D60C9A700C1CFD95A0E37231A59AE89A4C7F648DEE22503CF84AA9A` |
| `csynth_impl_report_gdn_rs2_top_impl_csynth.rpt` | `21A9B6ACCEA543480F7A24171E5771F2E611125B44E179DA33C45D5AE9502F31` |
| `csynth_solution_log_u55c_250mhz.log` | `C1B5534D1351C1EA15CF58E721AEDC937AD5D7BECA475112D34CB290AAC2A602` |
| `csynth_top_report_gdn_rs2_top_csynth.rpt` | `D650B110657AA9533E9F2015DA94A2A7275773CDA06571DFDC43BF81CB47F6F4` |
| `csynth_top_xml_gdn_rs2_top_csynth.xml` | `76672663E4E5CA9A8770528F6C65D68D10901577293C285D49D6895527BAD0DA` |
| `derived_source_gdn_rs2_top.cpp` | `CD3EF03E62D8CBE00DD2B8BEA9195D9D6EED1E2E8265D459161C3DCC534F747A` |
| `design_analysis.rpt` | `7F6F72B39973F7A07EA96ED2E96ED360AEE7D0DAF9DBF4BDD8325AE88BBFCA4B` |
| `generation_manifest_manifest.json` | `15B28209C17CE3F73BC20EC4CEA19B4C97B2C5FE7544B1967FD432582149AD3C` |
| `impl_clock_util.rpt` | `629B2A0137341A8F6FD6BC067905F5CE63870A3C9ABB474DEF80286A706968F0` |
| `impl_drc.rpt` | `68002920951A3C6227BF2B361711F4812ED2777B7F111BBAB2176DEAE211925A` |
| `impl_methodology.rpt` | `13B1936D277475CE9970934AF1948015D5E3AEED857D0B65B491342F2C7D6002` |
| `impl_power.rpt` | `8B074CC941209323EFA79B508E9F6F55AD3EC33B7D55E9FD2427901D434C4DC4` |
| `impl_timing.rpt` | `381397DF67746E545AEB47BF2A5DD7A6268A50A51BD973A21C43A8C2B483752A` |
| `impl_util.rpt` | `F8AFAE2B0B82FAB24FB63DC2E3DE08494AA0F546A09FE1FE301485D5C035BEF6` |
| `impl_util_hierarchical.rpt` | `CFF914CFC119F578B80B58C163F5B881115425663D39C398D1D4C85077453048` |
| `ooc_manifest_manifest.json` | `683765A2CC3D3ED7925E31C812BC5F7989024BBA81E09D54928858C305CA848F` |
| `vivado_impl_log_vivado_rs2-layer-banks-impl.log` | `7FE90C9CC328B95AEB92EFC88F447568E2CB6A8562D23F6AA16AE70E525DD761` |
| `worst_100_setup_paths.rpt` | `F91946807D0CBD2CE07DA9CC0B65A4B09F781C42EACC180F0C2B56FF0783BCC1` |

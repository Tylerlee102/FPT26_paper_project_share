# RS2 snapshot-write locality experiment

This source-isolated variant places LOAD-time primary/residual writes
behind a non-inlined helper on top of the matched fold-write plus
factor-six banking parent. Arithmetic, state layout and capacity,
commands, fold cadence, target, and route directives remain fixed.

Exact 64-token C simulation passes. HLS estimates 3.231 ns
and 102,364,909 maximum cycles. The final
route reaches -2.484 ns WNS and -79,337.969 ns TNS
with 72,420 failing setup endpoints.
Hold is +0.010 ns with 0 failures;
DRC has 0 critical warnings and 0 errors.

Relative to the combined parent, WNS changes by +0.273 ns,
TNS by -27,337.989 ns, and failing endpoints by
+18,747. Relative to selected, WNS
changes by -0.748 ns.
The worst path is 5.796 ns, with
0.805 ns logic and
4.991 ns net delay across
1 SLR crossings.

Decision: `RETAIN_SNAPSHOT_WRITE_LOCALITY_FOR_NEXT_ITERATION`. Vectorless power at a failed 4 ns
constraint is diagnostic only.

## Worst-100 startpoint origins

| Origin | Paths |
|---|---:|
| `fold` | 6 |
| `layer_address_control` | 64 |
| `reset_slot` | 1 |
| `resident_uram_read_clock` | 9 |
| `top_fsm` | 20 |

## Artifact hashes

| Artifact | SHA256 |
|---|---|
| `csim_report_gdn_rs2_top_csim.log` | `E60E3E85225EB6C89481E264F7DC81B155830A638AFC28344F53107D0D6612ED` |
| `csim_solution_log_u55c_250mhz.log` | `568691D82B2A143CCCCBA0F89D7952CC3CA1821EE894E8FD24A706DF9A48A4EB` |
| `csynth_impl_report_gdn_rs2_top_impl_csynth.rpt` | `031849AFFA856532C81E5A6D3F8A0939C53AFA0E7BCB3CF52BB34EC10BEA5E36` |
| `csynth_solution_log_u55c_250mhz.log` | `04E5A7C7285FF1B4C28EBB20C2CA86D24F2E4342358F4C044AED1A16DE989657` |
| `csynth_top_report_gdn_rs2_top_csynth.rpt` | `D3CA63CDC190A35E1297DECC99D960623972733ED595C963C5572D3053A7C0E9` |
| `csynth_top_xml_gdn_rs2_top_csynth.xml` | `F269B62B625423943F2E93961743C4528D98AAF62A821991DE9140DD697E0EFF` |
| `derived_source_gdn_rs2_top.cpp` | `A2DF7A1A91B6E388E70D141A5C2D8A75BC649F869AF986FD15EC95CBAE8799DD` |
| `design_analysis.rpt` | `2734286F33401EFAA7F66B3152F85884136F8312A0D28142C676C4B849B5267F` |
| `generation_manifest_manifest.json` | `2E887045AAA4D2E6E80124DC4F8F1D26DD970455BDD1509223EA0629724CB658` |
| `impl_clock_util.rpt` | `E8F4DA4A5104AF295376E685FCD7ECA7776E669F5663FCDBCC3AD588AB0D19EC` |
| `impl_drc.rpt` | `9384788B1BB32776B4646ED30F13DDF3CC04912EE6A7AB30B51DC3C1F0EA90F1` |
| `impl_methodology.rpt` | `178257448A60D85782200BAFB554FAB429AF7B55535523FA364F4A80E655DFE7` |
| `impl_power.rpt` | `D96D1D08348101DDDDE59A7CCE60904483A8260F3C9AA19A781ABC7746402359` |
| `impl_timing.rpt` | `B59949D381605FE8FEBD54718E1C6DC45B75B8404045FFBFD882BB3F2F1807FE` |
| `impl_util.rpt` | `A575E3D20BAFC879CCD121B82754673DAFC179B34480CDC5D6EC357909943D49` |
| `impl_util_hierarchical.rpt` | `23A0606D59AE0133299F349E66FF02E4CD9477BC9A599D85392AFD5C18FDB5E6` |
| `ooc_manifest_manifest.json` | `4B4B04A1C3454A5B6C0F062ECEF46889C17B04EBAC39D0FDA71F48A5AE88EB2A` |
| `vivado_impl_log_vivado_rs2-snapshot-write-partial-banks-impl.log` | `D55E0DCD54E9DDA383141B52681FBE2046BF675E3BB2E743DF2BB188DC450696` |
| `worst_100_setup_paths.rpt` | `4C688D221D4B0ABE87D9A05739189451F313B05C43553C0FD673223E27BDDD3F` |

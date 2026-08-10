# RS2 split fold-write experiment

This source-isolated variant splits the primary and residual folded-state
writes into sequential non-inlined helpers on the matched unbanked
fold-write parent. Arithmetic, state layout and capacity, commands, fold
cadence, target, and route directives remain fixed.

Exact 64-token C simulation passes. HLS estimates 3.106 ns
and 102,377,182 maximum cycles. The final
route reaches -3.091 ns WNS and -67,683.023 ns TNS
with 55,650 failing setup endpoints.
Hold is +0.010 ns with 0 failures;
DRC has 0 critical warnings and 0 errors.

Relative to the fold-write parent, WNS changes by -1.797 ns,
TNS by -54,488.020 ns, and failing endpoints by
+26,482. Relative to selected, WNS
changes by -1.355 ns.
The worst path is 6.973 ns, with
0.458 ns logic and
6.515 ns net delay across
2 SLR crossings.

Decision: `REJECT_SPLIT_FOLD_WRITE_TIMING`. Vectorless power at a failed 4 ns
constraint is diagnostic only.

## Worst-100 startpoint origins

| Origin | Paths |
|---|---:|
| `fold` | 31 |
| `load_snapshot` | 35 |
| `reset_slot` | 25 |
| `top_fsm` | 9 |

## Artifact hashes

| Artifact | SHA256 |
|---|---|
| `csim_report_gdn_rs2_top_csim.log` | `5D654E542E89C51C1EF6805681FAF1368BB7AA67F34BB46722EE65F22D0A37BA` |
| `csim_solution_log_u55c_250mhz.log` | `FEB82F5DC2FC2D21A661ADC78D27FC71B17BDA79534DD2F97500689D19A57DD9` |
| `csynth_impl_report_gdn_rs2_top_impl_csynth.rpt` | `C8FF44ABDB86633B0C8E17B394796DB49E00700E22D985FB842DBB18F913AC72` |
| `csynth_solution_log_u55c_250mhz.log` | `902E76BEA0AE2D4A2F92701F24DD91FDC914A07C678AFE8253EE73A3FD2F329D` |
| `csynth_top_report_gdn_rs2_top_csynth.rpt` | `03535E1FF84A3100119B258E985E42095090CC93B663B8AAFA1A4B425FD55592` |
| `csynth_top_xml_gdn_rs2_top_csynth.xml` | `0AEC3EDB5E951F5DB76A653FE4FCD92724F9BD70965F4E802D764F5C8A2C2A06` |
| `derived_source_gdn_rs2_top.cpp` | `A686EFDCE85BB9277EA728273292F60B4E6716D521160B0A5EA1021F34DDC6B3` |
| `design_analysis.rpt` | `6637D8F7F7A26159516E5AE04944EA7AF05B27A337240C536F400FD2ACDA6017` |
| `generation_manifest_manifest.json` | `8BF5CA373907F92DCE13A3CAFDBDFCFD582C9822BAC884675DFA235E6E7D2739` |
| `impl_clock_util.rpt` | `83567516A571F332DA3C1255F1EEDA03B886F5566DDC4BEA0EEE242E0EDD8E78` |
| `impl_drc.rpt` | `24DF9113718E4651E8D6378407679E614C977AA3CE3D0DE5DC637BBE9BF59E23` |
| `impl_methodology.rpt` | `10782A66B68AE42C9C6306249B04519B36C9CBD09474DA767F85F522C44A0DD1` |
| `impl_power.rpt` | `013A02A3FB2220E2CE3C412F86B8ADAE043487211667EEDC3E139F39C6316794` |
| `impl_timing.rpt` | `0A5914BA94A902FF9D782115984451C8AC249224C5887ECC91091E3AFDA1775E` |
| `impl_util.rpt` | `C1E7F7B33FA2E8620E246B9481CF47B3F6287B80ECD1A91EC931BC1BC884B082` |
| `impl_util_hierarchical.rpt` | `D50827068D8AAEB90830250A5BBD536E50A4C3F05399FD7A62EEA862AFC3E8BE` |
| `ooc_manifest_manifest.json` | `8F979AB41728D22ED0EFBBB9FB81710A9E34A93D43B4B47E5820CF35A8430C24` |
| `vivado_impl_log_vivado_rs2-split-fold-write-impl.log` | `18DB2C5A836708BE9D3027E1114BC812B16A9B5F6E8CDC333D536311A1F98E18` |
| `worst_100_setup_paths.rpt` | `EA55E015836B1BC1A7F51F06D72FBDEE5D030CAD266668B44FDF6773776A7557` |

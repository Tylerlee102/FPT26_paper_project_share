# RS2 localized fold-control timing experiment

This source-isolated variant moves the three-token fold decision into a
non-inlined helper. It preserves the exact 64-token recurrence and every
explicit HLS loop constraint, while the selected source remains unchanged.

Post-route WNS improves from -1.736 ns to -1.371 ns; high fanout falls from 133 to 87,
and net delay falls from 4.745 ns to 4.424 ns. Hold timing passes, but
250 MHz setup timing still fails. The variant is not promoted.

The remaining worst path starts inside the localized fold FSM and ends at
a resident-primary URAM byte-write-enable pin; 90% of its delay is routing.
The reported power is vectorless at a failed timing constraint and is not
used as energy evidence.

## Artifact hashes

| Artifact | SHA256 |
|---|---|
| `csim_report_gdn_rs2_top_csim.log` | `7E597F90144CED02DFB997B55D3C1AE385C604C609495864BD1C2DD343E89949` |
| `csim_solution_log_u55c_250mhz.log` | `9FCF5CD1F7D98B0FB576E7C1A57CC93E77E9DA19A6C92075F0526480716121BC` |
| `csynth_impl_report_gdn_rs2_top_impl_csynth.rpt` | `ADA33F83E5794FAD508A634A449006954C1B652BEBD68301F91B655B0CFDA60D` |
| `csynth_solution_log_u55c_250mhz.log` | `BBF825078E7F79F5734CC94C1F543AEFD697155D7360D2C7718FC076B5480ED9` |
| `csynth_top_report_gdn_rs2_top_csynth.rpt` | `09EDA3449A431FF653A259C651EAA8A17D2099248B7B69DDFDDB7E2A62AE4F55` |
| `csynth_top_xml_gdn_rs2_top_csynth.xml` | `55C07EC44B4B917B0BDC42B434B79298AAC2FD35AB3F8D857353376C411F9F9A` |
| `derived_source_gdn_rs2_top.cpp` | `BE0A2A3C1690D95E3AFC6B2B00D54318BE981C3E9EFDA0E722A5AE2F87C5BE2C` |
| `design_analysis.rpt` | `BC04253DECF9B5485D37E51DAD2F8A96CE8E1B587883B5B6014C631A9DAAFDE0` |
| `generation_manifest_manifest.json` | `1157C2FA0066DBE6BD01103DFB8AE5F86D710027722468F6E50B59BCAB564C98` |
| `impl_clock_util.rpt` | `E43CE68E590D1710AAFF10CD88CF9C72C4036B7352F0BC89BF7779A3DA55D6C1` |
| `impl_drc.rpt` | `CCAB7F13131D01D161F9F70244E976BCCD3763417D21BCB5A5EA865701D49AF4` |
| `impl_methodology.rpt` | `38EADBD1D02BD905741FEE82A09E5970E3F2148BD901D288C988763B1BE7B2DC` |
| `impl_power.rpt` | `2AE4126DB8841600D41922C1356CA77870F1C87199ED0ECBE8346BE2E1449B6E` |
| `impl_timing.rpt` | `AAEF32BACE0F4A837EC9958308FB6F6AFF2964618BD76EDF111D683F980461A4` |
| `impl_util.rpt` | `4DAACC4559DA205693A03E17058531E315271E238F3044FAFCBEECDAFF20FEA6` |
| `impl_util_hierarchical.rpt` | `4E8E607E0530D80AFF867674DA8864C22221A0CC076AF62B37E176A4170D9026` |
| `ooc_manifest_manifest.json` | `21AC24A394F1D30672E5064906ED49262BE07BE6FFEEFAC94BC0DE981068ED9B` |
| `vivado_impl_log_vivado_rs2-fold-control-impl.log` | `131B6F9B73FD7671E0226A2128318658CF904E47A63C1F62B52ED602B33E4CC0` |
| `worst_100_setup_paths.rpt` | `EE972888F78F352D49BD55741D16551782782DADD0DCBBD3A8E75ED220D57E69` |

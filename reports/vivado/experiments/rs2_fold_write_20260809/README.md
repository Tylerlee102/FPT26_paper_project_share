# RS2 localized fold-write timing experiment

This source-isolated variant preserves the localized fold decision and
moves each folded-state write into a separate non-inlined commit helper.
It passes exact 64-token C simulation, synthesis, and matched U55C routing.

Post-route WNS is -1.294 ns, improving on the selected
-1.736 ns and prior helper-only
-1.371 ns results. Hold and DRC pass, but 250 MHz
setup timing still fails, so the variant is not promoted.

The worst path again begins in outer fold control and ends at a
resident-primary URAM enable. The commit helper also increases worst-case
latency. Vectorless power at the failed 4 ns constraint is diagnostic only.

## Artifact hashes

| Artifact | SHA256 |
|---|---|
| `csim_report_gdn_rs2_top_csim.log` | `8EA706ACE230A8842DECB5707D837CD1309EA10990CCFB65BD375C33F4654A99` |
| `csim_solution_log_u55c_250mhz.log` | `771703E1DD11F55685F96B0C5C5186FEE82DCF320DA95E08BC773EFD44228E73` |
| `csynth_impl_report_gdn_rs2_top_impl_csynth.rpt` | `E96F863309BFDE33C62540637C680908609D720AE42EFD880FE8C5FD026A6FC7` |
| `csynth_solution_log_u55c_250mhz.log` | `F08C57220DE0AF8E51A46B934E076679DC2B6B2F38C6EB0C1223B4E1B010EE95` |
| `csynth_top_report_gdn_rs2_top_csynth.rpt` | `DBDF87577A768FAA490FD3D7BC345F1970B734980B5E8E30B63EF8C97E3A9CA3` |
| `csynth_top_xml_gdn_rs2_top_csynth.xml` | `4FAAE5683D574C5E0701473C465208E961F4172D59581300AAE4A3C92EA78861` |
| `derived_source_gdn_rs2_top.cpp` | `B1E12FC52C984FF4DF3CEB545F0ED97A8344FF4F398A404BBE3E8FC07C973E54` |
| `design_analysis.rpt` | `8AF7708812DE48A9FC6295C4EF817338FFFC7FFD6B397C82572DA092DBD6DC9C` |
| `generation_manifest_manifest.json` | `88FF98FF6EF2033D7086F26649B86596913615B59B623A172C06DC9EA3DAF9F1` |
| `impl_clock_util.rpt` | `65A0610BB3024C476B83C64A0A0CB9C6D7BAD52BCDA8000AE3BB0B5A7F9DCE25` |
| `impl_drc.rpt` | `3F7321EF2DF193EA06F9F11A0D72A8C41F58DE3CDD1F5E5AD3E62B0DB2449738` |
| `impl_methodology.rpt` | `C69A22E95E859E4E9F337CEDF4F3188D46104F37CCBB12FCD31EE39781BB19CD` |
| `impl_power.rpt` | `F77DADC02D2F3CDD9147677E80BEAFBCA87F1BA10E91696588F1ED48A6FA64DF` |
| `impl_timing.rpt` | `996FE85D57494029AE37ACD04E376AF8813D2454F525B8DF1E89525C2BCD5D48` |
| `impl_util.rpt` | `3D4939FC131192F16C929C490CE6617F5B13525E7428317CE0E9230B0840BAB0` |
| `impl_util_hierarchical.rpt` | `D7C26C5364B444F3B5FFCE446A182909ED7A7A874F4D9C6252962BDDE61923D6` |
| `ooc_manifest_manifest.json` | `37E26BEB8A6E69B61917CFADB0D318378CFD9D139117ED80AEB493E1D610F8B5` |
| `vivado_impl_log_vivado_rs2-fold-write-impl.log` | `0B1842C7D25058998EBB0EAE1DF702514EA70730AC0B2FF8DFEA01F65C5230C7` |
| `worst_100_setup_paths.rpt` | `B518FD390FF0D0FE4988090BFAE7689B0A31C949D8304A123EB8D99DB1D18CB4` |

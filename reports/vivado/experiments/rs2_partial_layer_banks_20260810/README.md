# RS2 six-way cyclic layer-bank experiment

This source-isolated variant cyclically partitions the primary and
residual state stores into six banks while preserving arithmetic,
capacity, commands, fold cadence, and the exact recurrent-state trace.

The routed result reaches -1.621 ns WNS and
-24,890.834 ns TNS with 44,629
failing setup endpoints. Hold and DRC pass, but 250 MHz setup does not.
Relative to selected, WNS changes by +0.115 ns, TNS
by -26.008 ns, and failing endpoints by
+1,036. Routed LUTs change by
+5,744, registers by
+2,377, and DSPs by
+2.

The worst path crosses one SLR and has high fanout 41 on URAM control.
The variant is not promoted. Vectorless power at the failed 4 ns
constraint is diagnostic only.

## Artifact hashes

| Artifact | SHA256 |
|---|---|
| `csim_report_gdn_rs2_top_csim.log` | `76E239667ED241A2069CDB085371B5E410C03BCE257FE7E1BCE00D70B9AD1DA6` |
| `csim_solution_log_u55c_250mhz.log` | `3FD5091ED5E418BA7E7E8F92637B2D61B3DB003B89166884076BF7C09608E6AD` |
| `csynth_impl_report_gdn_rs2_top_impl_csynth.rpt` | `493EB288B720ABA46BDE5375460E190A20A9D36FEC02BA5B529D535EDBBBCFF2` |
| `csynth_solution_log_u55c_250mhz.log` | `69E7CFD260C08A213C8AED238878F8240CD3F5AE07C9BF20A737AD354A3921F3` |
| `csynth_top_report_gdn_rs2_top_csynth.rpt` | `4A952265402A2C9C33C62F270A8997E502589A1ED2BD461973D61F09CFB0EAF2` |
| `csynth_top_xml_gdn_rs2_top_csynth.xml` | `F253EB5D6F55FCDA7C104D0E06F0B534A627EB5DCB72EAA2EEA1CAB384805EC4` |
| `derived_source_gdn_rs2_top.cpp` | `C1ABD8E3BAE38867416DC781CF3C320C4A6A729CA7537EA95795F8970041D104` |
| `design_analysis.rpt` | `2D9FBC00FD3D1586424D9CADDEBA68365FBEF5D57DCEF69FB7AA1C254CADE021` |
| `generation_manifest_manifest.json` | `2220B99EC417364898F9C594B107A2DD02BF4E3D57F590E1C841725F4DE86B2F` |
| `impl_clock_util.rpt` | `4CCBD86C6C13CD5C189863F3FE94986D440D9440C75EC3A0BFE631696348488C` |
| `impl_drc.rpt` | `7C12295C341ED3C99CF25B6077E67208044B70FCD8D562EF7C48057923C9387B` |
| `impl_methodology.rpt` | `25BFDCAFB434AD2A4B7DF27571D8B2AAE1ED4BA8A1BF561D61D62952B83040F7` |
| `impl_power.rpt` | `6D80512562C98ADDBE115CA10902FEB47F79426C243C2756063EAE20E1EBCAA5` |
| `impl_timing.rpt` | `AA4BFAC781CC224DBCF7E272233210D01F43C5DC2426EA3C40D8B7B20976B87B` |
| `impl_util.rpt` | `A52BD53B6768310375EFD6881962DD221915CF02A053CDA3ACD8DC9B49F33BBA` |
| `impl_util_hierarchical.rpt` | `271F3F4C60F4DB7F93019AB01490170D607B2A94278872A34426387B8BF8B998` |
| `ooc_manifest_manifest.json` | `BEC5020FA0B91815AD5869B6B4BB0F1EAFF128D2759F5A50FFB02E08100EB185` |
| `vivado_impl_log_vivado_rs2-partial-layer-banks-impl.log` | `A67329E31FC0CB14E83B9FB4DD69C3A03D5E4408EEAEE49AAB0AF58B694A1EE8` |
| `worst_100_setup_paths.rpt` | `D008991899DA9360C9B2851EFEED76C24073478A97AE51EB571984A1872CCD95` |

# RS2 fold-write plus six-way layer-bank experiment

This source-isolated variant composes localized fold-write helpers
with factor-six cyclic primary/residual layer banking. Arithmetic,
state capacity and layout, commands, fold cadence, target, and route
directives remain matched to the selected design.

Exact 64-token C simulation passes. HLS estimates 3.231 ns
and 102,364,909 maximum cycles. The final
route reaches -2.757 ns WNS and -51,999.980 ns TNS
with 53,673 failing setup endpoints.
Hold passes at +0.010 ns; DRC has 0 critical warnings
and 0 errors.

Relative to selected, WNS changes by -1.021 ns,
TNS by -27,135.154 ns, and failing endpoints by
+10,080. Relative to fold-write-only,
WNS changes by -1.463 ns and TNS by
-38,804.977 ns. Relative to banking-only, WNS changes
by -1.136 ns and TNS by -27,109.146 ns.
Routed LUTs change by +6,939, registers by
+2,638, and DSPs by +2
versus selected.

The worst path is 6.226 ns, with
0.237 ns logic and
5.989 ns net delay across
2 SLR crossings. The variant is
rejected and not promoted. Vectorless power at the failed 4 ns
constraint is diagnostic only.

## Artifact hashes

| Artifact | SHA256 |
|---|---|
| `csim_report_gdn_rs2_top_csim.log` | `1CF7398C7120D51B27A1B12145E6F6A9DDC7CD1D8663B1B2ED2CCEE91EA5399A` |
| `csim_solution_log_u55c_250mhz.log` | `59CCD6CBE05750B4F29B74518150D7740A99BC87444F5D6124B2DF7C0284ACC6` |
| `csynth_impl_report_gdn_rs2_top_impl_csynth.rpt` | `373C445AA3100040D99ABA4CDEC2D97F91CC8EE3EDECBAF20CABF332615F76E0` |
| `csynth_solution_log_u55c_250mhz.log` | `A0E4383A6993A76701A944D1188030E5D80369BF5CC4884AC7C3C3761A160F6F` |
| `csynth_top_report_gdn_rs2_top_csynth.rpt` | `4A4BC65F22CA6F714C9B853B54EB3A3080C5D0B19141C2FE14935F207380466B` |
| `csynth_top_xml_gdn_rs2_top_csynth.xml` | `682C71298C9C02D6371F42D5C6F2B3B085277994A3AC30D50293B1C358955FD5` |
| `derived_source_gdn_rs2_top.cpp` | `F323C342106C72CD79EE6D21185DAC4E95D90D1B5D8F37AEB0299EE61808A525` |
| `design_analysis.rpt` | `F4A6D03D648787E065E866218B261A63CDE8F9185CE6A9905DDE56C2FA2DC030` |
| `generation_manifest_manifest.json` | `A3D838F3BE4B70CB00F1BD0FC1F2F3A9F3E106D4B58AE513DAC3E1B18FFB5FB8` |
| `impl_clock_util.rpt` | `82DB5C19DA42C966507EE9AB1BB43959BA5D32B5C1E0833DB59BDDADE809A94C` |
| `impl_drc.rpt` | `2EB8F68E71D8520FD53A207B9B9A4CAAA5A2273ACFD96454B60BB9D57FF4FB12` |
| `impl_methodology.rpt` | `6B473518E37D0279ADCC2682A4EA6C055283A66012CE081D83C12AEAA80A6B8A` |
| `impl_power.rpt` | `C358FD93462A5BCEB590B51CAD0542CFB7EF1662995B982AB49A4E55AD2690B4` |
| `impl_timing.rpt` | `3720BACB503046D513FB249A638C298EADA870B54C1E7EC2C34BBCEAD54DE93F` |
| `impl_util.rpt` | `533A0638D2DFA2690E4A1C29AF608F4419BAD460D3E6196753E99268BB0E1EDD` |
| `impl_util_hierarchical.rpt` | `2768088C939D71791FF0623701C65FD2FAA1BA35647028E62B35F9ADFDEB25D0` |
| `ooc_manifest_manifest.json` | `3408DD079ECB38071485FA5978F02E02F98C6F985FDB39A2B8EC7BC6B313C9B8` |
| `vivado_impl_log_vivado_rs2-fold-write-partial-banks-impl.log` | `AF28B631A2A21F5A1867657784B4F989A79D7D25F8B060CE15E8D80C401BC217` |
| `worst_100_setup_paths.rpt` | `0B93D9C6B358C8DA2EBC8F4D5956385C51D8AF87D7D8B90969F5E5F662AA5589` |

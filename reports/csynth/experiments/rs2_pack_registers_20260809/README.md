# RS2 packed-word scheduling experiment

This rejected experiment replaced each pipelined loop-carried 128-bit output
word with 32 four-bit lane registers followed by an unrolled wiring-only pack.
It preserved every explicit II=1 constraint, the existing cycle counts, and the
321.96 MHz HLS estimate. The top-level estimate changed from 167,082 LUTs and
73,831 FFs to 166,712 LUTs and 73,859 FFs: 370 fewer LUTs (0.22%) and 28 more
FFs. The result cannot change the selected-method Pareto failure and was not
selected because doing so would invalidate the completed source-locked RTL and
post-route evidence for negligible benefit.

The raw Vitis HLS 2025.2 reports in this directory are the evidence. Their
SHA256 values are:

| Artifact | SHA256 |
|---|---|
| `gdn_rs2_top_csynth.rpt` | `D33CECFA38ED9E683883B6A157C68053EDE3A1F82BC92A1C97375F4A5C518111` |
| `gdn_rs2_top_impl_csynth.rpt` | `5563A99B8769A75D5EAB87E1E96948367D222EDC4B7E841019501EB645C5A315` |
| `p_anonymous_namespace_quantize_fold_block_Pipeline_quantize_fold_residual_csynth.rpt` | `FB3C3C7E899A7995174A2DA0DB6EBAB0534A69B7826EFEAEE04CDE392002D022` |
| `p_anonymous_namespace_quantize_update_block_Pipeline_quantize_update_second_csynth.rpt` | `9D688C271CB00D4CDF6DDB2425B27E45CAB825C31B542173244EF21E2C386310` |
| `u55c_250mhz.log` | `D12C7F0E46F0D3571746BBCEF0B38C099BCDAE6E25862815EF1694E75BB53C22` |

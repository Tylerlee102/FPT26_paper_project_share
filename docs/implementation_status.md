# Implementation Status

Repository revision: see `reports/final_completion_gate.json`.

Selected encoded candidate:

```text
mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5
```

Generated-RTL recurrent STEPs through the first R3 fold boundary pass exactly.
The complete 64-token generated-RTL and official XSIM traces remain governed by
the machine completion gate; shorter parity is not promoted to that claim.

## Controlled Answer

The current evidence gives a negative answer to the paper's research question:

> Native encoded MXFP4 does not replace BF16 in this persistent-state GDN
> recurrence-core kernel. Uniform MXFP4 fails the long-sequence synthetic
> stability criteria and increases both LUT count and estimated STEP cycles.
> The recurrence-aware correction restores bounded synthetic fidelity, but its
> HLS cost exceeds BF16 and its routed implementation misses the target clocks.

Persistent state and the five-phase schedule are inherited baseline dataflow,
not contributions. The contribution is the native E2M1/E8M0 arithmetic study,
long-horizon recurrent-state analysis, and the resulting scoped negative result.

## Evidence Summary

The controlled comparison fixes one GDN recurrence core, K-by-V state layout,
36 runtime layer slots, U55C target, 4.0 ns HLS constraint, `P_K=16`, `P_V=8`,
and block size 32.

| Evidence | Status | Result |
|---|---|---|
| Official recurrence parity | PASS | Independent FP64/FP32 and pinned recurrent/chunk/cache comparisons agree at the controlled boundary. |
| Floating uniform MXFP4 Q/DQ long trace | FAIL outcome | In the controlled random-state trace at 8,192 tokens, output cosine is 0.672818 and state relative L2 is 0.903408. |
| BF16 long trace | PASS outcome | In the same trace, output cosine is 0.999812 and state relative L2 is 0.020998. |
| MXFP8-state fallback | FAIL outcome | It is the strongest low-precision fallback at cosine 0.950258 and state relative L2 0.301757, but still misses the registered state-error criterion; its matched native HLS and routed hardware baselines are complete. |
| Scale-policy ablation | FAIL outcome | Fixed, every-token, periodic, and threshold-triggered refresh all fail at least one stability criterion. |
| Corrected test conditions | PASS | Three test seed blocks crossed with random/zero state pass after deterministic recomputation. |
| Corrected 8,192-token development | PASS | Random- and zero-state conditions and both independent full recomputations pass; minimum all-token cosine is 0.995974 and worst all-token state relative L2 is 0.082737. |
| Corrected 64-token HLS C simulation | PASS | Outputs, counters, folds, and final snapshot match exactly. |
| Corrected generated-RTL control smoke | PASS | Official Vitis HLS/XSIM completes two exact early-return commands. No recurrent transition is covered. |
| Corrected candidate recurrent RTL parity | PASS (direct generated RTL) | The exact Vitis-generated DUT and its 20 generated AXI memory models pass all 64 recurrent tokens, every output and counter, and the complete final resident-state snapshot in the direct Verilator harness. The separately hash-bound official-XSim diagnostic records PASS C transaction generation, PASS xelab, XSIM launch, and 0/10 completed transactions at the bounded stop; official-XSim completion remains incomplete. |
| Corrected out-of-context physical fit | PASS | 82,038 CLB LUTs, 69,800 FFs, 341 BRAM tiles, 598 URAMs, and 12 DSPs. |
| Corrected target timing | FAIL outcome | WNS is -1.736 ns at 250 MHz and -0.736 ns at 200 MHz; aggressive-fanout, retiming, and SLR-crossing post-route optimizations also fail. The first passing tested fixed-route point is 166.67 MHz. |
| Corrected DRC | PASS_WITH_WARNINGS | 26 warnings, zero critical warnings, and zero errors. |
| Post-route power | ESTIMATE | Vivado reports 5.242 W vectorless total power at the timing-closed 6.0 ns point with Medium confidence. This is not measured energy. |
| Native MXFP8 out-of-context route | PASS with timing failure | The image fits at 58,582 LUTs and 576 URAMs, fails 250 MHz, first closes at the tested 166.67 MHz point, and has a 4.952 W vectorless estimate. |
| Matched BF16 out-of-context route | PASS with timing failure | The unchanged 36-layer state layout fits by splitting state across 928 URAMs and 1,602.5 BRAM tiles, fails 250 MHz, first closes at the tested 140.35 MHz point, and has a 5.648 W vectorless estimate. |
| Real-input Qwen recurrence | PARTIAL | Matching checkpoint projections reconstruct q/k/v/alpha/beta for four layer-12 traces totaling 60 valid tokens; each prompt has only 12--18 tokens and is not closed-loop model inference. |
| Board execution and energy | BLOCKED_EXTERNAL | No attached U55C, U55C XRT platform, shell/xclbin, telemetry, or energy-per-token result is available or claimed. |

The older E2M0-residual/R7 candidate is retained only as superseded evidence.

Its logical payload is 537,744 bytes per layer, only 2,928 bytes below uniform
MXFP8-E4M3-B32. HLS estimates 435,089 LUTs, 17,954,144 maximum non-fold STEP
cycles, and 39,947,365 amortized cycles per layer/STEP. Three targeted II=1
constraints finish at II=2. The method is therefore not Pareto-superior to
BF16, even though its declared state bank physically fits out of context.

## Real-Capture Boundary

`data/calibration/qwen3_next_80b_a3b_layer12.npz` is a genuine pinned
Qwen3-Next capture. Matching checkpoint projections reconstruct q, k, v,
alpha, and beta at the declared recurrence boundary for four short prompt
traces. This supports a 12--18-token floating-Q/DQ recurrence diagnostic, not
long-horizon, closed-loop, perplexity, downstream-accuracy, or full-model
quality claims.

## Release Gates

The completion gate distinguishes release requirements from research outcomes.
A negative cost/stability outcome can be publishable; an unsupported claim,
stale provenance record, or unaudited PDF cannot.

The release gate keeps completed evidence separate from research outcomes.
Corrected-candidate 64-token direct generated-RTL parity passes all 66 commands,
262,144 output values, counters, and final recurrent state. Official recurrent
XSim remains separately `NOT_RUN`; the direct Verilator result and C simulation
do not silently fill that missing simulator path.

All eleven completion-gate rows are release-required. Any `FAIL`, `NOT_RUN`,
or `BLOCKED_EXTERNAL` row keeps the project `NOT PAPER READY`; no negative
outcome or external limitation is silently waived.

The current nonpassing outcomes include:

| Research outcome or limitation | Status |
|---|---|
| Selected-method Pareto advantage | FAIL |
| Corrected-candidate direct generated-RTL parity | PASS |
| Corrected-candidate official 64-token XSim parity | NOT_RUN |
| Controlled wider physical baselines | BF16 and MXFP8 fit, but miss 250 MHz |
| Closed-loop real-model quality | BLOCKED_EXTERNAL |
| Board parity and measured energy | BLOCKED_EXTERNAL |

The authoritative machine-readable status is
`reports/final_completion_gate.json`.

## Paper Assets

`paper/corrected/paper.tex` imports generated macros and tables from
`paper/corrected/numbers.json` and `paper/corrected/provenance.json`. Physical,
control-cosim, and Qwen-capture values are sourced from:

- `reports/vivado/corrected/rs2_current/rs2_vivado_summary.json`
- `reports/vivado/baselines/bf16/bf16_vivado_summary.json`
- `reports/vivado/baselines/mxfp8/mxfp8_vivado_summary.json`
- `reports/cosim/corrected/rs2_current/control/gdn_rs2_top_cosim.rpt`
- `reports/cosim/corrected/rs2_current/trace64_direct/rs2_trace64_direct_summary.json`
- `reports/cosim/corrected/rs2_current/xsim_diagnostic/rs2_xsim_diagnostic.json`
- `reports/golden/qwen_capture_characterization.json`
- `reports/benchmark/qwen_recurrent_stability_manifest.json`

The manuscript makes no full-Qwen accuracy, perplexity-preservation, GPU
speedup, board-energy, or five-phase/persistent-state novelty claim. A visibly
watermarked working draft may be built while release gates remain nonpassing;
the canonical submission PDF is not permitted until all eleven machine gates
are `PASS`.

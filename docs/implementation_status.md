# Implementation Status

Repository revision: `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`

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
| Uniform native MXFP4 long trace | FAIL outcome | At 8,192 tokens, output cosine is 0.429834 and state relative L2 is 2.580730. |
| BF16 long trace | PASS outcome | At 8,192 tokens, output cosine is 0.999955 and state relative L2 is 0.008988. |
| MXFP8-state fallback | FAIL outcome | It is the strongest low-precision numerical comparator but still misses the registered state-error criterion; its matched native HLS and routed hardware baselines are complete. |
| Scale-policy ablation | FAIL outcome | Fixed, every-token, periodic, and threshold-triggered refresh all fail at least one stability criterion. |
| Corrected test conditions | PASS | Three test seed blocks crossed with random/zero state pass after deterministic recomputation. |
| Corrected 8,192-token development | PASS | Two fully recomputed conditions pass; worst all-token state relative L2 is 0.099057. |
| Corrected 64-token HLS C simulation | PASS | Outputs, counters, folds, and final snapshot match exactly. |
| Corrected generated-RTL control smoke | PASS | Official Vitis HLS/XSIM completes two exact early-return commands. No recurrent transition is covered. |
| Corrected candidate recurrent RTL parity | NOT_ESTABLISHED | Two isolated official XSIM runs exhaust host memory before transaction one. Verilator 5.050 compiles the generated RTL and completes one exact LOAD in 4,797,322 cycles, but no candidate recurrent STEP completes; no 64-token RTL parity claim is made. |
| Corrected out-of-context physical fit | PASS | 208,523 CLB LUTs, 111,027 FFs, 353 BRAM tiles, 624 URAMs, and 44 DSPs. |
| Corrected target timing | FAIL outcome | WNS is -1.540 ns at 250 MHz and -0.540 ns at 200 MHz; the first passing tested fixed-route point is 180.18 MHz. |
| Corrected DRC | PASS_WITH_WARNINGS | 38 warnings, zero critical warnings, and zero errors. |
| Post-route power | ESTIMATE | Vivado reports 6.991 W vectorless total power at 5.6 ns with Medium confidence. This is not measured energy. |
| Native MXFP8 out-of-context route | PASS with timing failure | The image fits at 58,582 LUTs and 576 URAMs, fails 250 MHz, first closes at the tested 166.67 MHz point, and has a 4.952 W vectorless estimate. |
| Real-input Qwen recurrence | PARTIAL | Matching checkpoint projections reconstruct q/k/v/alpha/beta for four layer-12 traces totaling 60 valid tokens; each prompt has only 12--18 tokens and is not closed-loop model inference. |
| Board execution and energy | BLOCKED_EXTERNAL | No attached U55C, U55C XRT platform, shell/xclbin, telemetry, or energy-per-token result is available or claimed. |

The frozen corrected candidate remains:

```text
mxfp4_rs2_act_e2m1_e2m0_state_mxfp4rs2_log_r7_q1_15_int32_guard5
```

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
Corrected-candidate 64-token RTL parity is a scoped nonblocking failure because
the manuscript reports it as not established; it is not silently filled by the
uniform-MXFP4 RTL trace or by C simulation.

All eight release-required gates now pass. The remaining non-PASS rows below
are reported research outcomes or external limitations, not missing support for
the scoped paper claims.

The following scoped rows are deliberately nonblocking:

| Research outcome or limitation | Status |
|---|---|
| Selected-method Pareto advantage | FAIL |
| Corrected-candidate 64-token RTL parity | FAIL / NOT_ESTABLISHED |
| Controlled wider physical baselines | FAIL (BF16 capacity) |
| Closed-loop real-model quality | BLOCKED_EXTERNAL |
| Board parity and measured energy | BLOCKED_EXTERNAL |

The authoritative machine-readable status is
`reports/final_completion_gate.json`.

## Paper Assets

`paper/corrected/paper.tex` imports generated macros and tables from
`paper/corrected/numbers.json` and `paper/corrected/provenance.json`. Physical,
control-cosim, and Qwen-capture values are sourced from:

- `reports/vivado/corrected/e2m0/e2m0_postroute_summary.json`
- `reports/vivado/baselines/mxfp8/mxfp8_vivado_summary.json`
- `reports/cosim/corrected/e2m0_control_smoke/e2m0_control_smoke_summary.json`
- `reports/cosim/corrected/e2m0_trace64/e2m0_trace64_cosim_summary.json`
- `reports/golden/qwen_capture_characterization.json`
- `reports/benchmark/qwen_recurrent_stability_manifest.json`

The manuscript makes no full-Qwen accuracy, perplexity-preservation, GPU
speedup, board-energy, or five-phase/persistent-state novelty claim. Compilation,
page rendering, visual inspection, reviewer traceability, and exact-byte
finalization have completed for `paper/corrected/paper.pdf`.

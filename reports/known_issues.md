# Known Issues

The current paper is a supported negative result. These limitations and failed
hypotheses remain visible; none is silently promoted to a positive claim.

## Numerical Scope

- Uniform MXFP4, native encoded MXFP4, flat INT4, the MXFP8-state software
  fallback, and every tested MXFP4 scale policy fail at least one registered
  long-trace criterion.
- The corrected residual/write-log candidate passes the bounded synthetic test
  and development conditions, but the 0.10 state-relative-L2 threshold is an
  engineering choice rather than a model-calibrated accuracy bound.
- Pinned layer-12 hidden states plus matching checkpoint projections provide
  q, k, v, alpha, and beta for four model-derived recurrence traces, but each
  prompt has only 12--18 valid tokens. They do not establish long-horizon or
  closed-loop model behavior.
- No perplexity, downstream-task, or full-Qwen quality claim is supported.

## Hardware Scope

- The corrected candidate physically fits out of context, but fails setup at
  250 MHz and 200 MHz. The first passing point in the tested fixed-route sweep
  is 180.18 MHz; this is not a binary-searched maximum frequency.
- The critical path is dominated by routing into resident-state URAM control,
  not the E2M1 multiplier.
- The implementation has 38 DRC warnings. It has no critical warnings or
  errors, but shell integration may change placement and timing.
- The official candidate generated-RTL control smoke passes two early-return
  commands. Two isolated 64-token recurrent XSIM attempts exhaust host memory
  before transaction 1. Verilator 5.050 compiles the same 151 generated modules
  and completes one exact snapshot LOAD in 4,797,322 cycles, but no candidate
  recurrent STEP completes; candidate 64-token RTL parity is not established.
- BF16, uniform MXFP4, and native MXFP8 have matched HLS comparisons. The
  all-layer BF16 physical attempt fails capacity before placement, so there is
  no matched routed BF16 timing or power result.
- Native MXFP8 physically fits out of context at 58,582 LUTs and 576 URAMs,
  fails 250 MHz, and first closes at the tested 166.67 MHz point. Its 4.952 W
  vectorless result is not measured energy.
- Vitis and Vivado are installed, but no attached U55C, U55C XRT platform,
  xbutil/xrt-smi, shell/xclbin, or board telemetry is available. The host GPU is
  an RTX 3070 without native FP4 tensor-core support.
- The 6.991 W post-route value is a Medium-confidence vectorless Vivado
  estimate at 5.6 ns. It is not measured power and is not converted to energy
  per token.

## Method Outcome

- Native encoded MXFP4 fails the synthetic stability gate and is larger/slower
  than BF16 in the matched HLS comparison.
- The corrected candidate restores bounded synthetic fidelity but uses 5.124x
  the BF16 LUT estimate, 4.249x the maximum non-fold STEP cycles, and 9.453x the
  amortized per-layer cycles. Three targeted II=1 constraints finish at II=2.
- Consequently, the selected-method Pareto hypothesis is `FAIL`. This is the
  paper's result, not a release-system error.

## Release Verification

- Reviewer traceability passes for all 93 rows against the exact audited PDF.
- The US-Letter PDF uses eight content pages plus one reference-only page and
  passes compilation, embedded-font, metadata, unresolved-reference,
  page-render, and page-by-page visual checks. The final PDF is byte-identical
  to that audited candidate.
- The final regression records 303 passed, 1 skipped, and 0 failed tests in
  `reports/test_results/final_pytest_20260805.log` and
  `final_pytest_20260805.xml`.
- The one skip,
  `tests.test_reports.TestReports.test_current_hls_cosim_report_passes_when_present`,
  is intentional: the preserved legacy HLS cosim report predates the current
  HLS sources and is not accepted as current evidence.
- Corrected evidence includes exact 64-token HLS C simulation, the two-command
  generated-RTL control smoke, and one direct generated-RTL LOAD; no corrected
  recurrent RTL parity is inferred.
- The Phase-7 submission pack and every pack-integrity check pass. The scoped
  research outcomes that remain `FAIL` or `NOT_RUN` are preserved as
  limitations and do not become positive claims.

Legacy HLS, RTL, Vivado, benchmark, power, and paper PDFs remain preserved for
historical reproducibility. They do not support current claims unless a
corrected evidence manifest explicitly imports them.

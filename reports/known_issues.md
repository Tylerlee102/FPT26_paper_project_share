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
  is 166.67 MHz; this is not a binary-searched maximum frequency.
- Six post-route repair attempts fail 250 MHz. Chaining AggressiveExplore after
  fanout is best at -1.655 ns WNS, only 0.001 ns better than fanout alone;
  Vivado reports that the violation is too large for likely post-route repair.
- The critical path is dominated by routing into resident-state URAM control,
  not the E2M1 multiplier. Further timing work requires an architecture-level
  control-path or floorplanning change and complete revalidation.
- The implementation has 26 DRC warnings. It has no critical warnings or
  errors, but shell integration may change placement and timing.
- The official candidate generated-RTL control smoke passes two early-return
  commands. Two isolated 64-token recurrent XSIM attempts exhaust host memory
  before transaction 1. A lean official XSIM LOAD benchmark completes
  4,447,475 cycles in 502 seconds and projects 90.16 hours for the known
  2,875,491,178-cycle 64-token command sequence. The direct Verilator harness
  compiles the same generated RTL and passes all 66 commands, 262,144 output
  values, counters, and the final recurrent state exactly. Official 64-token
  XSIM parity remains `NOT_RUN`; direct generated-RTL parity is established.
- BF16, uniform MXFP4, and native MXFP8 have matched HLS comparisons. The
  all-layer BF16 implementation physically fits, first closes at the tested
  140.35 MHz point, and has a 5.648 W vectorless estimate.
- Native MXFP8 physically fits out of context at 58,582 LUTs and 576 URAMs,
  fails 250 MHz, and first closes at the tested 166.67 MHz point. Its 4.952 W
  vectorless result is not measured energy.
- Vitis and Vivado are installed, but no attached U55C, U55C XRT platform,
  xbutil/xrt-smi, shell/xclbin, or board telemetry is available. The host GPU is
  an RTX 3070 without native FP4 tensor-core support.
- The 5.242 W post-route value is a Medium-confidence vectorless Vivado
  estimate at 6.0 ns. It is not measured power and is not converted to energy
  per token.

## Method Outcome

- Uniform native MXFP4 fails the synthetic stability gate and is larger/slower
  than BF16 in the matched HLS comparison.
- The corrected candidate restores bounded synthetic fidelity but uses 1.958x
  the BF16 LUT estimate, 3.200x the maximum non-fold STEP cycles, and 10.191x
  the amortized per-layer cycles. Every explicitly targeted loop reaches II=1.
- Consequently, the selected-method Pareto hypothesis is `FAIL`. This is the
  paper's result, not a release-system error.

## Release Verification

- All 93 reviewer/comment and remediation-directive rows are mapped to source
  evidence. The canonical unwatermarked audit remains guarded: its builder
  correctly refuses to run while official XSim parity, closed-loop model
  quality, Pareto advantage, 250 MHz closure, or board evidence is nonpassing.
- The nine-page US-Letter working draft passes compilation, embedded-font,
  unresolved-reference, page-render, and page-by-page visual checks. It is
  watermarked `WORKING DRAFT - NOT SUBMISSION READY` and is not promoted to a
  final submission PDF.
- The latest full regression records 359 passed, 2 skipped, and 0 failed tests.
- One skip,
  `tests.test_reports.TestReports.test_current_hls_cosim_report_passes_when_present`,
  is intentional: the preserved legacy HLS cosim report predates the current
  HLS sources and is not accepted as current evidence.
- The second skip,
  `tests.test_paper_provenance.test_current_paper_pack_validates`, is
  intentional: no Phase-7 submission pack may be generated for the current
  revision while the final completion gate is nonpassing.
- Corrected evidence includes exact 64-token HLS C simulation, the two-command
  generated-RTL control smoke, full direct generated-RTL 64-token parity, and
  the bounded official-XSim runtime benchmark. Official full-trace XSim parity
  remains distinct and incomplete.
- The scoped research outcomes that remain `FAIL`, `NOT_RUN`, or
  `BLOCKED_EXTERNAL` are preserved as limitations and do not become positive
  claims or a submission-ready release.

Legacy HLS, RTL, Vivado, benchmark, power, and paper PDFs remain preserved for
historical reproducibility. They do not support current claims unless a
corrected evidence manifest explicitly imports them.

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
- Six checkpoint-local post-route repair attempts fail 250 MHz. Chaining
  AggressiveExplore after fanout is best among them at -1.655 ns WNS, only
  0.001 ns better than fanout alone;
  Vivado reports that the violation is too large for likely post-route repair.
- The critical path is dominated by routing into resident-state URAM control,
  not the E2M1 multiplier. Further timing work requires an architecture-level
  control-path or floorplanning change and complete revalidation.
- A source-isolated two-cycle URAM-output experiment passes the exact 64-token
  C simulation and every explicit synthesis loop constraint, but leaves the
  3.106 ns HLS estimate unchanged while adding 1,145 FFs, 72 LUTs, and 20,480
  worst-case cycles. It is rejected before route because 94 of the reported
  100 worst routed paths already terminate in `resident_residual` URAM control;
  output latency does not target those enable/write-control endpoints.
- A second source-isolated experiment localizes the fold decision in a
  non-inlined helper. It passes exact 64-token C simulation and synthesis, then
  improves routed WNS from -1.736 ns to -1.371 ns, reduces high fanout from 133
  to 87, and reduces route delay from 4.745 ns to 4.424 ns. It still fails
  250 MHz, adds 700 HLS-estimated FFs and 137 LUTs, and leaves a 90%-routing
  path from the local fold FSM to resident-primary URAM byte-write control.
  The selected source and completed generated-RTL validation remain unchanged.
- A third source-isolated experiment retains localized fold control and moves
  folded-state writes into a non-inlined commit helper. It passes exact
  64-token C simulation, every explicit synthesis constraint, and matched U55C
  routing. Routed WNS improves to -1.294 ns, TNS to -13,195.003 ns, and setup
  failures to 29,168 endpoints, the best isolated result so far. It still fails
  250 MHz, adds 654 HLS-estimated FFs, 108 LUTs, and 32,765 worst-case cycles,
  and its worst path has fanout 307 from outer fold control to a
  resident-primary URAM enable. It is not promoted.
- A fourth source-isolated experiment completely partitions the primary and
  residual state stores by layer. Exact 64-token C simulation, every explicit
  synthesis constraint, full all-layer capacity, routing, hold, and DRC pass.
  The partition removes the monolithic high-fanout write-enable path, but the
  worst path becomes a bank-local URAM read/selector path into fold logic.
  Routed WNS is -1.867 ns, TNS is -41,081.309 ns, and 54,809 setup endpoints
  fail. Relative to the selected route, it worsens WNS by 0.131 ns, TNS by
  16,216.483 ns, and failing endpoints by 11,216 while adding 27,797 routed
  LUTs and two DSPs. It is rejected and not promoted.
- A fifth source-isolated experiment cyclically partitions the same state stores
  into six layer banks. Exact 64-token C simulation, all explicit synthesis
  constraints, routing, hold, and DRC pass. Routed WNS improves from -1.736 ns
  to -1.621 ns, but TNS worsens from -24,864.826 ns to -24,890.834 ns and the
  failing setup endpoints increase from 43,593 to 44,629. The route adds 5,744
  LUTs, 2,377 registers, and two DSPs; its worst path crosses one SLR with
  fanout 41 into URAM control. It still fails 250 MHz and is not promoted.
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
- A full installed-platform inventory finds seven XPFMs, all for non-U55C
  targets. Windows and Ubuntu WSL contain no xbutil, xrt-smi, or xbmgmt, and
  neither environment exposes a Xilinx PCI device.
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
- The latest full regression records 379 passed, 2 skipped, and 0 failed tests.
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

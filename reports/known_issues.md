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
- A sixth source-isolated experiment composes factor-six cyclic layer banking
  with the strongest localized fold-write hierarchy. Exact 64-token C
  simulation, every explicit synthesis constraint, routing, hold, and DRC
  pass, but the final route is dominated by both parent experiments: WNS is
  -2.757 ns, TNS is -51,999.980 ns, and 53,673 setup endpoints fail. The
  6.226 ns worst path contains 5.989 ns of net delay and crosses two SLRs.
  Relative to selected, the route adds 6,939 LUTs, 2,638 registers, and two
  DSPs. The composition is rejected and not promoted.
- A seventh source-isolated experiment adds a non-inlined snapshot-write
  commit boundary to the sixth composition. Exact 64-token C simulation, every
  explicit synthesis constraint, routing, hold, and DRC pass. Routed WNS
  improves by 0.273 ns versus the sixth experiment to -2.484 ns, but TNS
  worsens to -79,337.969 ns and 72,420 setup endpoints fail. The 5.796 ns worst
  path contains 4.991 ns of net delay, seven logic levels, one SLR crossing,
  and fanout 83. Of the 100 worst setup paths, 64 start in shared layer/address
  control, 20 in the top FSM, nine at resident URAM clocks, six in fold control,
  and one in reset control; none starts in snapshot-load or its commit helper.
  The route uses 88,830 LUTs, 72,540 registers, 341 BRAM tiles, 598 URAMs, and
  14 DSPs. Snapshot-write locality is retained only as a clue for a smaller
  unbanked experiment; the composed variant is not promoted.
- An eighth source-isolated experiment returns to the strongest unbanked
  fold-write parent and splits its primary and residual commits into sequential
  non-inlined helpers. Exact 64-token C simulation, every explicit synthesis
  constraint, routing, hold, and DRC pass. HLS estimates 3.106 ns with 74 BRAM,
  26 DSP, 74,489 FFs, 167,279 LUTs, 88 URAMs, and 102,377,182 worst-case cycles.
  The final route regresses to -3.091 ns WNS, -67,683.023 ns TNS, and 55,650
  failing setup endpoints. Its 6.973 ns worst path contains 6.515 ns of net
  delay, five logic levels, two SLR crossings, and fanout 103. Of the 100 worst
  setup paths, 35 start in snapshot-load control, 31 in fold control, 25 in
  reset control, and nine in the top FSM. The route uses 82,155 LUTs, 70,464
  registers, 341 BRAM tiles, 598 URAMs, and 12 DSPs. The split is rejected and
  not promoted.
- A ninth source-isolated experiment applies the snapshot-write commit boundary
  directly to the strongest unbanked fold-write parent. Exact 64-token C
  simulation, every explicit synthesis constraint, routing, hold, and DRC pass.
  HLS retains the parent's 3.106 ns estimate and 102,360,798-cycle worst-case
  latency while adding 128 FFs and 88 LUTs. The final route reaches -1.494 ns
  WNS, -26,161.480 ns TNS, and 43,246 failing setup endpoints, which is 0.200 ns
  worse in WNS, 12,966.477 ns worse in TNS, and 14,078 more failing endpoints
  than the parent. Its 5.226 ns worst path contains 4.863 ns of net delay, five
  logic levels, one SLR crossing, and fanout 569. Of the 100 worst setup paths,
  70 start in the top FSM, 15 at resident URAM read clocks, 11 in fold control,
  two in top-level implementation control, one in snapshot-read control, and
  one in reset control; none starts in snapshot-load or snapshot-commit logic.
  The route uses 83,269 LUTs, 70,679 registers, 341 BRAM tiles, 598 URAMs, and
  12 DSPs. The boundary changes the origin mix but does not close 250 MHz, so
  the variant is rejected and not promoted.
- A tenth source-isolated experiment combines the strongest fold-write parent
  with two contiguous layer banks. Exact 64-token C simulation, every explicit
  synthesis constraint, routing, hold, and DRC pass. HLS retains the parent's
  3.106 ns estimate and adds four worst-case cycles, 9,649 LUTs, 2,385 FFs, two
  DSPs, and 64 HLS-reported URAMs. The final route reaches -2.966 ns WNS,
  -66,301.594 ns TNS, and 64,439 failing setup endpoints, which is 1.672 ns
  worse in WNS, 53,106.591 ns worse in TNS, and 35,271 more failing endpoints
  than the parent. Its 6.377 ns worst path contains 6.174 ns of net delay,
  three logic levels, two SLR crossings, and fanout 97. Of the 100 worst setup
  paths, 80 start in the `gmem4` state-input AXI load FIFO, 19 in snapshot-load
  control, and one at a resident URAM read clock. The route uses 85,951 LUTs,
  72,275 registers, 341 BRAM tiles, 598 URAMs, and 14 DSPs. Contiguous banking
  exposes a new load-to-banked-URAM control cone and is rejected, not promoted.
- An eleventh source-isolated experiment adds snapshot-write locality to the
  two-contiguous-bank parent. Exact 64-token C simulation, every explicit
  synthesis constraint, routing, hold, and DRC pass. HLS retains the parent's
  3.106 ns estimate and 102,360,802-cycle worst-case latency while using 43
  fewer FFs and 46 fewer LUTs. The final route reaches -3.623 ns WNS,
  -86,731.445 ns TNS, and 67,782 failing setup endpoints, which is 0.657 ns
  worse in WNS, 20,429.851 ns worse in TNS, and 3,343 more failing endpoints
  than the two-bank parent. Its 7.152 ns worst path contains 6.825 ns of net
  delay, five logic levels, two SLR crossings, and fanout 96. Snapshot and AXI
  load origins disappear, but all 100 worst setup paths move to the top FSM.
  The route uses 86,263 LUTs, 72,215 registers, 341 BRAM tiles, 598 URAMs, and
  14 DSPs. Local snapshot-write isolation therefore displaces the banked-memory
  control bottleneck without improving timing; the composition is rejected and
  not promoted.
- A twelfth RTL-only experiment adds `max_fanout=16` to the stronger unbanked
  snapshot-write parent's explicit top-FSM declaration. All RTL logic and HLS
  evidence remain unchanged, and Vivado creates 326 replicated instances across
  134 replication events. The matched route nevertheless reaches -2.686 ns WNS,
  -58,498.117 ns TNS, and 58,993 failing setup endpoints: 1.192 ns worse WNS,
  32,336.637 ns worse TNS, and 15,747 more failing endpoints than the parent.
  The 6.676 ns worst path contains 6.166 ns of net delay, five logic levels,
  two SLR crossings, and fanout 97. Of the 100 worst setup paths, 58 begin at
  replicated top-FSM registers, 21 in reset control, 14 in the snapshot commit
  helper, five in fold control, and two at resident URAM clocks. The route uses
  83,210 LUTs, 71,391 registers, 341 BRAM tiles, 598 URAMs, and 12 DSPs.
  Pre-synthesis controller
  replication therefore increases register cost and worsens every setup metric;
  it is rejected and not promoted.
- A thirteenth RTL-only experiment adds `max_fanout=16` only to the two
  registered primary/residual addresses in the strongest fold-write parent.
  Parent behavior and exact 64-token C-simulation evidence remain unchanged;
  the matched route, hold, and DRC complete. The hint reduces targeted
  address-register origins from 47 to four of the 100 worst setup paths, but
  reaches -1.453 ns WNS, -18,473.637 ns TNS, and 35,126 failing endpoints.
  Relative to the parent this is 0.159 ns worse WNS, 5,278.634 ns worse TNS,
  and 5,958 more failing endpoints. The 5.091 ns worst path is 93% net delay,
  has five logic levels, one SLR crossing, and fanout 99. The remaining worst
  paths begin at 59 resident-URAM read clocks, 23 fold-control registers, and
  14 reset-control registers. The route uses 82,425 LUTs, 70,619 registers,
  341 BRAM tiles, 598 URAMs, and 12 DSPs. Local address fanout reduction
  displaces the bottleneck without closing timing; it is rejected and not
  promoted.
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
- The latest full regression records 416 passed, 2 skipped, and 0 failed tests;
  its JUnit artifact is
  `reports/test_results/final_pytest_20260810_paper_refresh.xml`
  (SHA256 `A26FC01DC91A2801DB1F96518526344C5A3153890CF11ED40183446E2EF753F0`).
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

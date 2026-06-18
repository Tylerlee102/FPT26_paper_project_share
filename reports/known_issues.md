# Known Issues

No waived test failures.

Open Phase 6 verification items:

- Fresh HLS C-sim is complete for the current tile-streamed sources:
  `tb_gdn_top PASS vectors=64/64`.
- Current 128-token C/RTL cosim for the final packed-output RTL completed through
  the official Vitis wrapper report: Verilog PASS, `128/128` transactions.
- Non-default Phase 6 sweep points now have Vivado implementation reports and
  RTL cosim latency traces. The max-parallel points route but fail 250 MHz
  timing; keep them as failing Pareto points unless the hardware is redesigned
  or the clock target changes.
- Qwen-captured realistic accuracy/PPL data is still unavailable, so accuracy
  tables remain synthetic-only. In the currently activated local toolchain,
  `torch`, `transformers`, and `datasets` are not installed, so
  `reports/golden/qwen_capture_status.md` reports `dependency_blocked`. Even
  after installing those dependencies, the official HuggingFace acceptance model
  is `Qwen/Qwen3-Next-80B-A3B-Instruct` and its repository is about 151.5 GiB
  before runtime overhead. This local machine has an 8 GiB RTX 3070 and no
  cached copy of the model, so the capture cannot be completed here without an
  external larger/offloaded environment or a provided valid `.npz` capture. See
  `reports/golden/qwen_capture_status.md`.
- The persistent-state rewrite and packed output interface clear the Phase 6
  latency/speedup hard floors for the default config. See
  `reports/benchmark/latency_root_cause.md`.
- Additional synthetic stress evidence is available in
  `reports/benchmark/stress_accuracy.md`,
  `reports/benchmark/state_boundary.md`, and
  `reports/benchmark/state_drift.md`. The 1024-token drift result reinforces
  that MXFP8 recurrent state is the safer fallback when accumulated state error
  matters.

Future-phase work remains in the phase plan, but the checked-in tests are active
sanity checks rather than skipped placeholders.

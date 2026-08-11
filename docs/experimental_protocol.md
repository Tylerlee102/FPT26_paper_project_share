# Experimental Protocol

Current selected candidate:
`mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5`.
It uses a fixed three-entry write log and two E2M1/E8M0 terms throughout the
encoded token/state path. Generated RTL has passed recurrent STEPs through the
first R3 fold boundary. Uniform-MXFP4 RTL evidence is not transferred to this
candidate; its own 64-token direct and official XSIM runs define that gate.

Protocol version: `0.3`. Version `0.1` was locally recorded before G1-G6
execution; this revision appends executed results and labels post-selection
stress additions and protocol deviations explicitly. The local record was not
externally timestamped and did not hash the complete execution dependency
closure, so it is not described as independently notarized preregistration.

Current execution status: **SUPPORTED NEGATIVE RESULT; WORKING DRAFT ONLY**.
Official recurrence parity, the independent encoded oracle, matched BF16 HLS
extraction, exact write-log equivalence, and the selected correction's locally
recorded synthetic stability gates are `PASS`. The corrected candidate also has
exact 64-token HLS C simulation, an official two-command generated-RTL control
smoke, exact direct-XSim generated-RTL execution of the complete 64-token trace,
and an out-of-context routed U55C implementation. Candidate-specific direct RTL
parity is `PASS`. The distinct Vitis-generated UVM wrapper reaches transaction
1/66 but exhibits host-memory growth, so wrapper completion remains `NOT_RUN`.
Uniform MXFP4 fails both the 8192-token stability gate and
the matched HLS LUT/STEP-cost gate. The selected correction restores bounded
synthetic fidelity but fails its HLS Pareto criteria and the 250/200 MHz routed
timing points. Four 12--18-token real-input Qwen recurrence traces are complete,
but closed-loop model quality remains unrun. Shell/board execution and measured
energy are externally blocked by the absence of a U55C device and XRT platform.

## Research Question

At a fixed Qwen3-Next GDN recurrence-core boundary, can native OCP MXFP4-B32
replace BF16-style arithmetic while reducing FPGA logic/schedule cost and
limiting empirical recurrent-state drift over long synthetic decode traces?

Physical fit and vectorless power are delivered for the selected candidate,
native MXFP8 baseline, and matched BF16 baseline. All preserve 36 logical state
slots, but none closes 250 MHz. Board energy and closed-loop model quality
remain separate, explicitly unclaimed evidence levels.

Persistent state, the five-stage token organization, state layout, target,
`P_K`, and `P_V` are held constant in the main arithmetic comparison.

## Frozen Inputs

| Input | Revision/version |
|---|---|
| Qwen3-Next-80B-A3B-Instruct | `9c7f2fbe84465e40164a94cc16cd30b6999b0cc7` |
| Transformers | `v4.57.0`, peeled commit `8ac2b916b042b1f78b75c9eb941c0f5d2cdd8e10` |
| flash-linear-attention | `v0.2.1`, `a670dff4c2537fc1a82486584dd9569e18fba833` |
| causal-conv1d | `v1.5.3.post1`, `52949d0891770c65243ed24db8abb66ef37741b7` |
| PyTorch / Triton / CUDA | `2.8.0` / `3.4.0` / `12.8.1` |
| WikiText | `b08601e04326c79dfdd32d625aee71d232d685c3`, `wikitext-103-raw-v1` |
| PG-19 | `4d28bd77e66947ad3835cf78ed7aaeb4dd87ad8b` |
| FPGA target | U55C `xcu55c-fsvh2892-2L-e`, platform `xilinx_u55c_gen3x16_xdma_3_202210_1` |

The actual model, tokenizer, dataset file, sample-selection, and bitstream hashes
must be added to `docs/evidence_manifest.md` before a run can be `PASS`.

## Fixed Kernel Configuration

- Batch: 1.
- One decode token per recurrence-core step.
- Value/state heads: 32.
- Q/K heads: 16, with `p(h) = floor(h/2)`.
- K and V dimensions: 128.
- Logical state orientation: K-by-V.
- OCP block size: 32 along the feature/V-column axis.
- FPGA clock target: 250 MHz.
- Main point: `P_K=16`, `P_V=8`.
- Main comparison changes arithmetic/state format only.
- Gated RMSNorm, projections, convolution, and output projection are excluded
  from every core result.

The `(8,4)` and `(32,16)` parallelism points and B16 custom blocks are secondary
ablations. They cannot be mixed into the main format comparison.

## Reference And Variant Matrix

| Variant | Compute | Resident state | Role |
|---|---|---|---|
| FP64 oracle | FP64 | FP64 | Independent mathematical truth for software tests. |
| Official reference | Pinned implementation dtype | Official cache/state | Recurrence/chunk and cache-faithful parity. |
| FP32 reference | FP32 | FP32 | Long-horizon numerical reference, not bit-exact truth. |
| BF16 baseline | BF16 | BF16 | Required matched wider-arithmetic FPGA baseline. |
| MXFP8 baseline | MXFP8-E4M3-B32 | MXFP8-E4M3-B32 | Required primary low-precision baseline. |
| MXFP4 floating Q/DQ | Floating emulation of OCP MXFP4-B32 boundaries | Floating emulation | Numerical diagnostic only. |
| Native encoded MXFP4 | Integer E2M1/E8M0 B32 | Integer E2M1/E8M0 B32 | Main native four-bit candidate and HLS arithmetic. |
| MXFP4 + MXFP8 state | OCP MXFP4-B32 | MXFP8-E4M3-B32 | Required state-precision fallback. |
| Stochastic MXFP4 | OCP MXFP4-B32 | OCP MXFP4-B32 | Software ablation with recorded RNG stream. |
| Flat INT4 | Symmetric INT4 | Symmetric INT4 | Supplemental fallback only. |
| Fixed write log R=4/8/16 | Selected base format | Higher-precision bounded log | G3 software-only candidates. |
| Adaptive candidate | Selected base format | Empirically controlled log | Evaluated only after exact equivalence. |

A candidate advances to HLS only after its held-out software quality gate
passes, its logical payload improves on the declared low-precision baseline,
and its prior-art gap has been accepted by a human reviewer. HLS then tests the
resource and latency parts of the Pareto hypothesis; physical allocation and
energy remain later evidence gates.

## G1 Correctness Protocol

1. Implement an FP64 recurrence without importing the production recurrence.
2. Compare small hand-computable tensors and finite-difference-style invariants.
3. Extract recurrence inputs/states from the pinned Transformers implementation.
4. Compare one-token recurrent execution with the official recurrent path.
5. Compare recurrent execution with official chunk/WY execution.
6. Compare prefill followed by token-at-a-time decode with contiguous execution.
7. Repeat with random nonzero states, all alpha/beta endpoints, and both K-by-V
   and explicit V-by-K storage conversions.

FP32 acceptance: state and output relative L2 at most `1e-5` and maximum absolute
error at most `5e-5` for non-adversarial finite test tensors. BF16 tolerances are
reported from an unmodified official BF16 run and frozen before candidate
evaluation; BF16 is never described as bit-exact.

## Encoded Arithmetic Protocol

The encoded-integer oracle follows `docs/numerical_contract.md`. Test classes:

- exhaustive E2M1 element pairs and all meaningful scale differences;
- random nonzero resident states;
- alpha and beta equal to zero, one, and adjacent Q1.15 codes;
- scale changes at every token;
- scale-clamp, underflow, largest-finite, and near-tie values;
- cancellation and alternating-sign reductions;
- accumulator saturation and element saturation;
- multi-token persistence across separate calls;
- reset between sequences and failed-command non-mutation;
- interleaved sequence and layer IDs;
- load/readback and generation counters;
- all 36 layer IDs; and
- adversarial independently generated expected results.

HLS C, RTL, and board acceptance is exact equality of output codes, state codes,
scale bytes, counters, statuses, and generation numbers after each command.

## Synthetic Long-Trace Protocol

### Splits And Seeds

The original plan listed development seeds `0xFB72`, `0xFB73`, and `0xFB74`, but
the executed controlled nominal comparison uses only `0xFB72`. The encoded
correction test set uses seed blocks `0xA17E5EED`, `0xC4D3B2A1`, and
`0x06E5A1D0`. Each seed block is crossed with random and zero initial state,
giving three independent token streams and six paired conditions.

The candidate and test seeds were recorded before the test artifacts according
to local timestamps. Because the registration omitted some execution
dependencies and has no external timestamp, it supports a frozen local test-set
account but not an independently auditable no-leakage claim.

### Trace Families

The canonical numeric definitions are in
`docs/synthetic_trace_protocol.json` and are checked against the executed
generator paths by `tests/test_synthetic_trace_protocol.py`.

1. **Nominal:** independent standard-normal q/k followed by the kernel-boundary
   normalization; zero-mean normal v with standard deviation `0.25`; random
   initial state with standard deviation `0.05`; alpha uniform on `[0.95,1]`;
   beta uniform on `[0,1]`.
2. **Decay sweep:** fixed alpha values `{0, 0.5, 0.9, 0.99, 0.999, 1}` and beta
   endpoints/interior values.
3. **Dynamic range:** piecewise changes in v magnitude and state block exponents.
4. **Cancellation:** alternating keys/values designed to cancel updates.
5. **Adversarial:** repeated aligned keys, maximal writes, exponent boundary
   crossings, and saturation-provoking inputs.

Every family starts from both zero and random nonzero state. The controlled
nominal baselines share one generated prefix. Changing to the high-retention
family changes the deterministic RNG stream even at the same seed, so the
correction traces are not paired ablations of the nominal baseline trace.

The **high-retention** family keeps the q/k/v distributions and changes alpha to
`[0.995,1]` and beta to `[0.85,1]`. For the superseded sparse/MXFP8-log
candidate, this family was added only as development stress after its nominal
test gate. The later encoded E2M1/E2M0-residual candidate used this family for
its locally frozen test set. The incomplete dependency lock and local-only
timestamp are retained limitations.

### Lengths And Sampling

Run 64, 256, 1024, 4096, and 8192 tokens. Store metrics at every token and
retain full state snapshots at token 0 and each required length. Use identical
trace prefixes so a 256-token result is the prefix of its 8192-token run.

### Metrics

- Output cosine similarity versus FP32 by token and checkpoint. FP64 is used in
  separate short recurrence-oracle tests; no FP64 long-horizon curve was run.
- Recurrent-state relative L2 error by token and checkpoint.
- Maximum absolute state error by token and checkpoint.
- Output relative L2 and maximum absolute error.
- Element/accumulator saturation, scale clamp, and alignment-underflow counts.
- State block-scale changes and exponent distribution.
- Worst paired condition over the three corrected-candidate seed blocks. The
  originally planned mean/median/percentile report was not produced and no
  population-level inference is made from three seed blocks.

Output metrics flatten all heads and V coordinates; state metrics flatten all
heads, K rows, and V columns. No headwise gate is run. The zero-reference
convention for relative L2 is
`||candidate-reference||_2 / max(||reference||_2, 1e-12)`.

### Scale-Policy Ablation

For uniform MXFP4 state, compare:

- fixed scales from token 0 calibration;
- recompute modified block scales every token;
- recompute every `N in {4,8,16}` tokens; and
- threshold refresh when the maximum normalized magnitude leaves `[0.75, 5.5]`.

Test-set execution uses one frozen policy. If an implementation cannot support a
policy without changing the boundary, report it as `NOT_RUN`; do not move it to
future work while implying it was evaluated.

### Synthetic Engineering Gate

The controlled uniform comparison requires output cosine at least `0.99` at
all required checkpoints, final state relative L2 at most `0.10`, and zero
element saturation, accumulator saturation, or scale clamps. These three are
the locally registered hard-event counters. Alignment underflows and deliberate
E2M0 residual clips are reported but not thresholded. The frozen encoded
candidate uses the same numerical and event thresholds for its local
1,024-token high-retention test conditions and its separate 8,192-token
development extension. These are engineering gates, not claims of model
quality.

Post-hoc sensitivity: the corrected extended maximum is 0.000943 below the
0.10 state ceiling. Tightening only that ceiling to 0.09 would change both the
three-seed-block test aggregate and the extended development result to `FAIL`.

### Executed Uniform-State Diagnostics

Status: `FAIL` for uniform MXFP4 as a BF16 arithmetic replacement on this
development trace. This is not a held-out or model-quality result.

The nominal development prefix for seed `0xFB72` ran once through 8192 tokens
at the fixed kernel dimensions: 32 value heads, 16 Q/K heads, K=V=128,
activation B32, and state B32. It produced 40,960 unique token/variant rows and
25 checkpoint rows with matching manifest hashes. At token 8192:

| Variant | Output cosine vs FP32 | State relative L2 | Status |
|---|---:|---:|---|
| BF16 operands/state, FP32 accumulation | 0.999955 | 0.008988 | PASS |
| Native encoded MXFP4 | 0.429834 | 2.580730 | FAIL |
| Uniform MXFP4 state | 0.729275 | 1.103841 | FAIL |
| MXFP8-E4M3 state fallback | 0.968498 | 0.232133 | FAIL |
| Flat INT4 fallback | 0.525403 | 1.862013 | FAIL |

Across every token, native encoded and floating-Q/DQ uniform MXFP4 violate the
plotted 0.99 cosine and 0.10 state-error limits beginning at token 1. The
MXFP8-E4M3-state fallback first crosses the cosine limit at token 4 and the
state-error limit at token 5; BF16 crosses neither through token 8192. These
crossings are diagnostics and do not alter the locally frozen checkpoint gate.

Raw floating-Q/DQ evidence is in
`reports/benchmark/corrected/long_trace_tokens.csv`,
`long_trace_checkpoints.csv`, and `long_trace_manifest.json`. Event columns for
those candidates remain `NOT_RUN`; they do not claim encoded accumulator or HLS
saturation counts. Separately, the native encoded run records 8192 token rows,
five checkpoint rows, and six full-state snapshots in
`native_encoded_long_trace_*`. Its separate verifier recomputes every
checkpoint metric and counter recurrence. At token 8192 it reports zero element
or accumulator saturation and zero scale clamps, but 2,685,620,693 cumulative
alignment underflows.

Supplemental robustness execution repeats the same 32/16-head, K=V=128, B32
geometry through 8192 tokens for deterministic dynamic-range and cancellation
families. The former cycles value magnitude across nine powers of two; the
latter alternates the sign of absolute-valued q/k/v inputs. A strict aggregator
validates 81,920 token rows, both checkpoint projections, source/output hashes,
commands, seeds, and geometry. BF16 stays inside both full-trace diagnostics.
Every low-precision variant fails at least one threshold, while MXFP8 state is
the least-drifting low-precision comparator in both families. Evidence is in
`reports/benchmark/corrected/stress/long_trace_stress_summary.{csv,md}` and its
manifest. These floating-Q/DQ probes are not native encoded event evidence and
do not substitute for model-derived activation outliers.

Protocol deviation: the earlier floating-Q/DQ execution retained per-token
metrics but not the planned full state snapshots. The native encoded execution
does retain token-0 and all five required full-state snapshots. No missing
floating snapshot is implied to exist.

The scale-policy ablation ran the same full trace for fixed scales,
every-token refresh, periodic refresh at N=4/8/16, and per-block threshold
refresh outside `[0.75, 5.5]`. None passed. Fixed scales were numerically
least-bad at token 8192 (output cosine 0.847089, state relative L2 0.676620) but
incurred 67,980,414 state-element clips. Threshold refresh incurred zero such
clips but reached 0.558410 and 1.724816. The input-stream SHA256 is
`adb9105ce36c702eeb5d72a52145aed951c55752e9a541bafbb549e61679df0e`;
raw evidence is in `scale_policy_tokens.csv`, `scale_policy_checkpoints.csv`,
`scale_policy_ablation.md`, and `scale_policy_manifest.json` in the same report
directory.

The verifier confirms that the long-trace and scale-policy runs use
the identical input stream and initial state, that every checkpoint CSV is an
exact canonical projection of its full token CSV, and that every-token scale
refresh reproduces the uniform-MXFP4 trace at every token. The separately
verified native encoded-integer trace is now complete through 8192 tokens and
fails the same frozen stability gate. Together, these results motivate the
separately frozen residual-stack/write-log study below.

### Executed Fixed-Geometry HLS Arithmetic Comparison

Status: `FAIL` for an HLS-estimated LUT-and-STEP cost advantage. Extraction and
source/provenance checks are `PASS`. Matched BF16, native MXFP4, and native
MXFP8 kernels have HLS evidence. Matched 36-layer BF16, MXFP8, and selected
RS2/R3 routes all fit out of context but miss 250 MHz; measured energy remains
externally blocked.

The BF16 and native encoded-MXFP4 kernels hold the recurrence, K-by-V state,
36 runtime layer slots, five-phase organization, U55C target, 4.0 ns constraint,
`P_K=16`, `P_V=8`, and B32 constant. BF16 uses BF16 operands/state with FP32
accumulation and BF16 state/output rounding. Their command semantics are
equivalent, but their data-plane encodings are not identical: BF16 carries BF16
tensors, while MXFP4 carries element/scale codes and expanded integer output
fields. Packing and token quantization lie outside both kernels, so this is a
fixed-geometry logic/schedule comparison rather than an end-to-end transport or
energy comparison.

| Arithmetic | Estimated path | Maximum STEP cycles | LUT | FF | DSP |
|---|---:|---:|---:|---:|---:|
| BF16 | 2.920 ns | 4,225,728 | 84,919 | 39,087 | 0 |
| Native encoded MXFP4 | 2.920 ns | 6,070,592 | 138,969 | 43,962 | 3 |
| Native MXFP8 E4M3/E8M0 | 2.920 ns | 6,287,680 | 143,084 | 44,715 | 3 |

Native encoded MXFP4 uses 63.65% more LUTs and has a 43.66% longer maximum
estimated STEP loop. All HLS-inferred BRAM/URAM totals are excluded: they are
incompatible with independent bit-capacity lower bounds for the declared deep
arrays. They are not used as physical banking or placement evidence.

### Superseded Write-Log Development

Exact-arithmetic equivalence is `PASS`. With
`u = beta * (v - k^T(alpha S))`, the official recurrence adds the write,
`S_t = alpha S_(t-1) + k u^T`. The exact log therefore represents the state as
`gamma_B B + sum_i lambda_i k_i u_i^T`; a subtractive log would have the wrong
sign under this definition of `u`. Focused tests cover capacities, folds,
paired-key sharing, per-head decay, pure decay, coefficient rebasing, atomic
folding, and zero dropped entries.

Development sweeps evaluated fixed capacities R=4/8/16, FP32 and MXFP8 logs,
two-term MXFP4 activation/state residual stacks, sparse second state terms, and
a decay-triggered policy. The frozen selection is:

```text
mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7
```

It uses two-term MXFP4 activation and state residual stacks, keeps the three
largest residual B32 blocks out of each four-block state row, and maintains a
seven-entry MXFP8-E4M3 log with fixed all-head atomic folds. Its logical state
payload is 536,912 bytes versus 1,048,576 bytes for BF16 and 540,672 bytes for
uniform MXFP8-B32. Physical allocation is `NOT_RUN`; these logical values did
not authorize candidate HLS.

The selection was written to `write_log_selection.json` before held-out access.
The selected row passes all five 64-8192 development checkpoints. Activation-
only and base-only two-term ablations fail, so both residual corrections are
necessary for this tested point. Adaptive threshold schedules showed no clear
quality/storage advantage and were not selected.

### Executed Nominal Held-Out Traces

Status: `PASS` for the locally recorded nominal synthetic engineering gate only.

The frozen candidate ran once for each combination of held-out seed
`{0xA11CE, 0xC0FFEE, 0x5EED5}` and initial state `{random, zero}`, through 8192
tokens with metrics stored at every token. All six paired-condition verifiers and
both matrix manifests are `PASS`, with zero dropped writes.

Across the 30 required checkpoints, the worst output cosine is `0.994163`. At
token 8192, the worst state relative L2 is `0.098834`. Across all 49,152
candidate token rows, the minimum output cosine is `0.993407` and the maximum
state relative L2 is `0.105004`; the latter is a transient above the endpoint
criterion. Raw evidence is rooted at
`reports/benchmark/corrected/write_log_held_out_manifest.json`, and the two
paper figures are generated by `scripts/plot_write_log_held_out.py` only after
all upstream hashes pass.

This PASS permits real-model evaluation under the registered protocol. It does
not establish model quality, encoded candidate behavior, or physical Pareto
advantage.

### Executed Additional Stress

Status: `FAIL` for high-retention robustness.

The superseded candidate ran 1024-token development traces for dynamic range,
cancellation, high retention, decay sweep, and adversarial inputs from random
and zero initial states. Dynamic-range, cancellation, decay-sweep, and
adversarial runs pass the same checkpoint/end-state rule. Both high-retention
runs fail: at token 1024, random initialization reaches cosine `0.983090` and
state relative L2 `0.185116`; zero initialization reaches `0.983534` and
`0.185297`. All runs report zero dropped entries. The configuration remains
frozen; this stress failure is a limitation, not a tuning input.

### Executed Selected-Candidate Development

Further development was completed before a new registration was frozen. The
active candidate is:

~~~text
mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5
~~~

Token vectors, recurrent base state, and live keys/writes each use two E2M1
terms with independent E8M0 B32 scales. Three writes remain live with Q1.15
coefficients and fold atomically at capacity. Alignment uses five guard bits
and signed INT32 accumulation. Logical payload is 576,912 bytes per layer,
55.02% of BF16 and 6.70% above uniform MXFP8-E4M3-B32. The declared all-layer
selected state bank is physically allocated in the
out-of-context U55C result; complete-model and shell integration remain outside
scope.

The development/test split, thresholds, seeds, trace families, initial states,
and candidate identity were locally recorded in
`reports/benchmark/corrected/rs2_encoded_candidate_preregistration.json` before
the held-out artifacts according to local timestamps. The registration binds
the scalar and vectorized RS2, E2M0, and uniform-MXFP4 oracles plus generator,
verifier, and registration scripts. It was not externally timestamped, so it
does not independently prove chronology or absence of leakage.

### Executed Encoded Held-Out Traces

Status: `PASS` for the locally registered 1,024-token synthetic engineering
gate.

Three test seed blocks were crossed with random and zero initial state for six
paired high-retention conditions. Every run manifest passes the recorded
checkpoint-cosine, final-state-error, and three-hard-counter gate. Every artifact
was then deterministically recomputed by the same implementation and compared
field by field; this checks integrity and determinism, not an independent
implementation.

Across all six paired conditions, the minimum registered-checkpoint cosine is
`0.996473`, the minimum all-token cosine is `0.996099`, the maximum final state
relative L2 is `0.081983`, the maximum all-token state relative L2 is
`0.082666`, and the maximum absolute state error is `0.142368`.
Element saturation, accumulator saturation, and scale clamps total zero.
Alignment underflows and state-scale changes remain reported diagnostics.
Aggregate evidence is
`reports/benchmark/corrected/rs2_encoded/rs2_encoded_candidate_summary.json`.

This PASS is a bounded layer-level engineering check over three stochastic
blocks. It does not establish population-level robustness, closed-loop model
quality, physical fit, or energy.

### Extended Development Traces

Status: `PASS` for both locally registered 8,192-token development generator
manifests and both independent full deterministic recomputations.

Random- and zero-initial-state traces use seed `0xFB72`, the high-retention
family, and checkpoints 64, 256, 1,024, 4,096, and 8,192. The frozen oracle,
executor, and verifier sources are unchanged. The aggregate is generated by
`scripts.aggregate_rs2_encoded_candidate --require-extended` and records both
conditions under the separate `extended_development` result.

Across the random- and zero-initial-state runs, minimum checkpoint cosine is
`0.996507`, minimum all-token cosine is `0.995974`, maximum final state relative
L2 is `0.081702`, maximum all-token state relative L2 is `0.082737`, and maximum
absolute state error is `0.162014`. Element saturation, accumulator saturation,
and scale clamps total zero. Alignment underflows total `1,672,767,604`,
state-scale changes total `43,021,831`, and the log folds `5,460` times. These
two runs share the development seed and are not statistical or real-model
evidence.

### Executed Corrected-Candidate HLS

Arithmetic C simulation passes the frozen cases. Stateful C simulation passes
64 tokens through repeated folds and final non-mutating snapshot readback.
Source-locked C synthesis estimates a 3.106 ns path, 167,082 LUTs, 73,831 FFs,
74 BRAM18Ks, 88 URAMs, and 26 DSPs. Every explicitly targeted loop reaches
II=1. Raw inferred memory counts are excluded from physical-fit conclusions.

Relative to matched BF16, the candidate uses 1.958 times the LUTs, 3.200 times
the maximum non-fold STEP cycles, and 10.191 times the amortized per-layer HLS
cycles per STEP. Non-fold STEP latency is 8,978,912--13,522,144 cycles, fold
latency is 43,966,624--88,629,408 cycles, and the maximum amortized cost is
43,065,280 cycles per STEP. These are one-layer command estimates, not average
or p99 service latency. The HLS cost/latency result is `FAIL` despite II=1.
Candidate-specific RTL, physical allocation, and post-route timing are reported
below. Direct generated-RTL recurrent parity is `PASS`; official-XSim recurrence
completion remains incomplete, and board energy is `BLOCKED_EXTERNAL`.

### Corrected-Candidate Physical Implementation

Status: `PASS` for out-of-context physical fit and evidence extraction; `FAIL`
for the declared 250 MHz and secondary 200 MHz setup checks.

Vivado 2025.2 routes the corrected candidate on
`xcu55c-fsvh2892-2L-e`. The implementation uses 82,038 CLB LUTs, 69,800
registers, 341 BRAM tiles, 598 URAMs, and 12 DSPs. It reports 26 DRC warnings,
zero critical warnings, and zero errors. At 4.0 ns, WNS is -1.736 ns; at 5.0
ns, WNS is -0.736 ns. Aggressive-fanout and
retiming post-route optimization improve WNS only to -1.656 ns; SLR-crossing
optimization remains at -1.736 ns. The first passing point in the tested
fixed-route sweep is 6.0 ns (166.67 MHz), with WNS 0.264 ns and WHS 0.010 ns.
This is not a binary-searched maximum frequency.

At the timing-closed 6.0 ns period, Vivado vectorless activity propagation
reports 5.242 W total, 1.874 W dynamic, and 3.368 W static power with Medium
confidence. This is not board telemetry and is not converted to energy per
token. Evidence is rooted at
`reports/vivado/corrected/rs2_current/rs2_vivado_summary.json`.

Official Vitis HLS/XSIM co-simulation passes two exact generated-RTL
early-return commands. Because neither command executes a recurrent transition,
this is a control smoke only. A direct AMD XSim harness retaining the exact DUT
passes LOAD, all 64 recurrent STEPs, every
output and counter, and complete final-state readback. The official XSIM path
separately passes the eight-token C transaction generator and xelab, then
launches XSIM, but its bounded diagnostic completes no recurrent transaction.
Candidate 64-token direct generated-RTL parity is therefore `PASS`, while
official-XSim recurrence completion remains incomplete. Evidence is rooted at
`reports/cosim/corrected/rs2_current/` and
`reports/cosim/corrected/rs2_fast_direct_rtl_trace64/`; the bounded official
attempt is hash-bound in
`reports/cosim/corrected/rs2_current/xsim_diagnostic/rs2_xsim_diagnostic.json`.

## Real-Input Recurrence and Closed-Loop Protocol

Short recurrence status: **PASS**. Pinned layer-12 hidden states and matching
checkpoint projections reconstruct q, k, v, alpha, and beta at the recurrence
boundary for four prompts totaling 60 valid tokens (12--18 per prompt).
FP32, BF16, MXFP4-state, MXFP8-state, and flat-INT4 floating-Q/DQ paths are
reported in `reports/benchmark/qwen_recurrent_stability_manifest.json`.

Closed-loop model-quality status: **NOT_RUN**. The short captures do not replace
all recurrence cores in a quantized model and cannot support perplexity or
downstream-task claims.

Development data uses the pinned WikiText validation split and PG-19 validation
split. Held-out data uses only their test splits. Before execution, freeze the
ordered example IDs, tokenized sample hashes, prefix lengths, and evaluation
counts in a manifest. No held-out result may tune a candidate.

For each example:

1. Call `model.eval()` under `no_grad()` with `use_cache=True`.
2. Prefill the frozen prefix and retain `past_key_values`.
3. Feed ground-truth tokens one at a time with input length exactly one, correct
   cache position, and the updated cache.
4. Replace all actual GDN recurrence cores so candidate state/output influences
   every later layer and token.
5. Assert call counters for every one-token recurrent layer invocation.
6. Record model/tokenizer revisions, layer types, shapes, dtypes, state
   orientation, source hashes, and transformations.

Primary quality metrics are token-weighted perplexity with paired bootstrap 95%
confidence intervals and per-layer state/output error. A candidate passes the
quality gate only if held-out perplexity degradation is at most 1% relative to
the matched BF16 run and its paired 95% confidence interval does not cross 2%.
Any downstream task must be selected before data access and report paired
confidence intervals; downstream accuracy is not required if the frozen
paper claim is limited to perplexity and recurrence stability.

Offline q/k/v captures may diagnose arithmetic but cannot satisfy this gate.

## Software Candidate Selection

Software exactness status: `PASS`.

Corrected encoded local test-set engineering status: `PASS`.

Selected-method Pareto status: `FAIL`.

HLS report extraction status: `PASS`. Configured timing margin, HLS cost, and
explicit II=1 subcriteria: `FAIL`.

Allocated physical-memory and direct-XSim recurrent RTL parity subcriteria:
`PASS`. Target timing is `FAIL`; generated-UVM-wrapper completion and
service-latency remain `NOT_RUN`, while measured energy is `BLOCKED_EXTERNAL`.

For the lazy-base/write-log hypothesis, prove exact-arithmetic equality to the
official recurrence before quantization. Exercise paired-key sharing, per-head
decay, independent and paired folding, coefficient underflow/rebasing, log-full
backpressure, and atomic folding. Pure decay may not rewrite the entire MXFP4
base every token.

At most one mechanism advances. It must dominate uniform MXFP4 or MXFP8 on the
held-out set in all of:

- quality gate;
- allocated physical memory after padding and banking;
- average and p99 service latency; and
- measured or post-route-estimated energy at the same stage.

Failure to dominate is a valid negative result. HLS measures a cost failure,
and the subsequent out-of-context route establishes physical fit while missing
250 and 200 MHz. The corrected R7 point passes the locally recorded
high-retention test-set gate and logical-payload comparison, but its HLS
LUT/STEP cost and explicit II=1 criteria fail. Recurrent RTL service latency and
measured energy remain unavailable.

## FPGA Protocol

### Required Implementations

- Corrected BF16 recurrence core.
- MXFP8-E4M3-B32 recurrence core/state.
- Uniform OCP MXFP4-B32 recurrence core/state.
- MXFP4 compute with MXFP8 state.
- One selected adaptive/logged design, only if G3 passes.

All variants use the same recurrence and logical state layout, `P_K`, `P_V`,
clock target, and U55C target. Their data-plane encodings may differ and must be
reported explicitly. Report logical bytes and allocated BRAM/URAM primitives,
including padding, banking, replication, ports, metadata, scratch, and SLR
placement.

The corrected BF16, uniform-MXFP4, and native-MXFP8 variants have matched HLS
C-synthesis estimates. BF16 and MXFP8 have bounded HLS C-simulation checks; uniform MXFP4 has
64-token HLS C parity and 64-token direct generated-Verilog parity. The
selected mitigation has 64-token HLS C parity and C synthesis. Its RTL evidence
contains an official two-command control smoke and exact direct-XSim execution
of all 64 recurrent STEPs. The generated UVM wrapper remains incomplete after
transaction 1/66 because of host-memory growth. The selected, BF16, and
native-MXFP8 variants have out-of-context routed images; all preserve 36 state
slots, fit, and miss 250 MHz. Board implementation remains externally blocked.

### Model-Wide State Subsystem

Verify `model.config.layer_types` contains 36 GDN and 12 full-attention layers.
Allocate and address all 36 GDN states. Test interleaved layers, reset/load/
readback, no dropped writes, log-full/fold races, service-rate stability,
occupancy, backpressure, port conflicts, and fold/read atomicity.

Separately report convolution state, attention KV cache, weights, activations,
buffers, and host traffic. Do not claim complete model residency.

### Build Evidence

For each frozen variant, preserve C simulation, C synthesis, RTL cosimulation,
synthesis, implementation, timing, utilization, DRC, bitstream, XRT logs, and
the exact source/configuration hashes. A report from a different recurrence or
kernel boundary is invalid.

No multi-hour sweep, licensed-tool installation, or FPGA programming starts
without explicit approval.

## Board And Baseline Protocol

On a physical U55C record board model/serial, bitstream hash, Vivado/Vitis/XRT
versions, actual clock, host, warm-up, workload length, repetitions, telemetry
sampling, idle baseline, and thermal state.

Use a long repeated workload that reaches thermal steady state. Report mean,
variance, p99, and worst-case latency. Integrate telemetry samples over time for
total and idle-subtracted board energy. Do not multiply one power snapshot by a
microsecond kernel latency.

GPU baselines execute the same recurrence-core boundary with warm-up and explicit
synchronization. Record GPU model, clocks, software, batch, precision, power
telemetry, and sample integration. TDP-derived energy is prohibited.

## Output Artifacts

CSV outputs live under `reports/golden/` or `reports/benchmark/` and include at
least:

```text
run_id, split, seed, trace_family, variant, layer_id, token_index,
output_cosine_fp32, output_rel_l2, output_max_abs,
state_rel_l2, state_max_abs, element_saturations, accumulator_saturations,
scale_clamps, alignment_underflows, state_scale_changes
```

Paper-ready figures are generated from validated CSV/provenance only:

- output cosine versus token index/required length; and
- recurrent-state relative L2 versus token index/required length.

Each figure reports split, seeds, recurrence boundary, state orientation,
variant, and uncertainty limits. The metric contract and zero-reference
convention are versioned with the artifact. No paper number is typed by hand.

## Decision Log

| Decision | Status | Rule |
|---|---|---|
| Run G1 official recurrence parity | PASS | Local FP64/FP32, pinned Transformers recurrent/chunk/cache, and direct FLA BF16 comparisons pass at the exact Qwen dimensions. |
| Freeze resident-state software controls | PASS | Command/status codes, atomic state operations, counters, generations, all 36 layer IDs, and sequence/layer isolation pass 13 focused tests. |
| Complete G2 numerical and HLS C correction | PASS | The encoded-step/resident oracles and the 64-token corrected HLS C command trace are bit-exact. |
| Complete one-token uniform-MXFP4 RTL smoke | PASS | A direct AXI harness executes current-source generated Verilog through RESET, STEP, and READBACK with exact selected checks. |
| Complete required 64-token uniform-MXFP4 RTL parity | PASS | The bounded direct generated-Verilog run checks every output and counter, then the complete final state, scales, status, and generation. |
| Extract uniform baseline C synthesis | PASS | Fresh U55C/4.0 ns report estimates 342.47 MHz; every explicitly targeted loop reaches II=1. |
| Clear the vendor loop-constraint summary | PASS | Vitis reports all loop constraints satisfied; all 14 explicit arithmetic/state pipelines reach II=1, while control/transport loops are not auto-pipelined. |
| Extract matched BF16 HLS baseline | PASS | Bounded C simulation and C synthesis pass at the same boundary, dimensions, parallelism, target, and clock constraint. |
| Full nominal development trace | FAIL | BF16 passes; uniform MXFP4, MXFP8-state fallback, flat INT4, and all six scale policies miss the frozen engineering thresholds. |
| Native encoded 8192-token trace | FAIL | Artifact generation and separate deterministic verification pass, but native MXFP4 misses every required stability threshold. |
| Uniform MXFP4 HLS cost advantage | FAIL | It uses 1.636x BF16 LUTs and 1.437x BF16 maximum STEP cycles at the same estimated clock. |
| Logical state-capacity calculation | PASS | MXFP4-B32 uses 278,528 bytes/layer versus 1,048,576 for BF16; these raw-bit bounds are separate from the corrected candidate's physical fit. |
| Prove exact write-log equivalence | PASS | Exact base-plus-write representation matches the official additive update across focused edge cases. |
| Freeze selected encoded candidate | PASS | The two-term E2M1/E8M0 base/token/log R3 configuration, test seeds, and complete declared source closure were locally recorded before held-out artifacts; lack of an external timestamp remains a limitation. |
| Run corrected encoded test-set gate | PASS | Three token-stream seed blocks crossed with two initial-state conditions pass the 1,024-token quality and three-hard-counter requirements after deterministic recomputation. |
| Run extended corrected 8,192-token development traces | PASS | Random and zero-state conditions plus both full recomputations pass the local development quality and hard-counter gate. |
| Preserve superseded candidate stress | FAIL | The earlier sparse/MXFP8-log point failed both high-retention traces and is not current selected evidence. |
| Characterize available real Qwen capture | PASS | The pinned layer-12 capture establishes layer-boundary range/outlier evidence. Matching checkpoint projections reconstruct q/k/v/alpha/beta for four short prompt traces. |
| Run short real-input Qwen recurrence diagnostics | PASS | Four 12--18-token traces compare FP32, BF16, MXFP4-state, MXFP8-state, and INT4 floating-Q/DQ paths without claiming full-model quality. |
| Extract matched native MXFP8 HLS baseline | PASS | Arithmetic C-sim, one exact persistent-kernel transition, C-synthesis, and all explicit II=1 constraints pass at the controlled geometry. |
| Route matched all-layer BF16 physical implementation | PASS | The unchanged 36-layer state layout routes by splitting state across 928 URAMs and 1,602.5 BRAM tiles. It fails 250 MHz and first closes at the tested 140.35 MHz point. |
| Run closed-loop 80B quality evaluation | NOT_RUN | No perplexity or downstream-quality claim is made. |
| Artifact-release policy | PASS | Release after review, subject to venue anonymity rules; no publication occurs during anonymous review. |
| Start corrected baseline HLS implementation | PASS | Corrected C simulation, one C-synthesis point, and uniform-path 64-token direct generated-Verilog parity are preserved. |
| Complete candidate-specific HLS C simulation and synthesis | PASS | Corrected C simulation and a source-locked U55C synthesis extraction exist. |
| Candidate-specific HLS Pareto advantage | FAIL | LUT, non-fold STEP, and amortized STEP cost exceed BF16 even though every explicit II=1 constraint passes. |
| Candidate-specific 64-token RTL parity | PASS (direct XSim); generated UVM wrapper NOT_RUN | Exact 64-token C simulation and direct XSim over the generated RTL pass all 64 recurrent steps and final-state readback. The distinct generated UVM wrapper reaches 1/66 but exhibits host-memory growth. Uniform-MXFP4 RTL evidence is not transferred to the changed candidate. |
| Candidate-specific generated-RTL control smoke | PASS | Official Vitis HLS/XSIM passes two early-return commands; no recurrent transition is covered. |
| Route selected candidate out of context | PASS | The state bank fits; 250 and 200 MHz setup fail after three post-route optimization attempts; the first passing tested point is 166.67 MHz. |
| Route matched native MXFP8 out of context | PASS | The baseline fits, fails 250 MHz, and first closes at the tested 166.67 MHz point; its vectorless power remains an estimate. |
| Program U55C and collect telemetry | BLOCKED_EXTERNAL | The host has Vitis/Vivado but no attached U55C, U55C XRT platform, xbutil/xrt-smi, xclbin, or board telemetry. |
| Generate selected-candidate paper source assets | PASS | Controlled long-trace data, plots, macros, tables, numbers, provenance, and direct-RTL assets are generated. The official-wrapper status remains explicit rather than being filled by direct-XSim evidence. |
| Render and audit final paper PDF | NOT_RUN | A visibly watermarked working draft is allowed; canonical submission PDF generation remains gated on all eleven release rows passing. |

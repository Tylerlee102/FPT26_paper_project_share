# Numerical Contract

Version: draft `0.9`, updated after corrected-candidate encoded software,
test-set and 8,192-token development recomputation, 64-token HLS C simulation, and
HLS C synthesis on
`2026-08-02`.

Implementation status: **FAIL** at the selected-method Pareto gate. The
corrected FP32 path, independent FP64 scalar/affine references, official
framework parity, uniform and corrected encoded-integer oracles,
resident-state commands, and corrected-candidate HLS C simulation pass bounded
tests. The corrected candidate also passes three 1,024-token high-retention
seed blocks crossed with two paired initial-state conditions and two fully
recomputed 8,192-token development conditions. Its HLS estimate exceeds BF16
LUT and STEP cost, misses its configured timing margin, and misses three
explicit II=1 constraints. The existing 64-token direct
generated-Verilog parity applies only to uniform MXFP4; candidate-specific RTL
is `NOT_RUN`. Post-route evidence is `NOT_RUN`, and board parity is
`BLOCKED_EXTERNAL`. This document does not certify a final system.

## Kernel Boundary And Shapes

The kernel is the Qwen3-Next **GDN recurrence core**, batch one and one decode
token per `STEP` operation.

| Quantity | Logical shape | Meaning |
|---|---|---|
| `q` | `[16, 128]` | L2-normalized query, already multiplied by `1/sqrt(128)` |
| `k` | `[16, 128]` | L2-normalized key |
| `v` | `[32, 128]` | Post-convolution, post-SiLU value |
| `alpha` | `[32]` | Per-value-head decay in `[0,1]` |
| `beta` | `[32]` | Per-value-head delta gate in `[0,1]` |
| `S` | `[36, 32, 128, 128]` | Layer, value head, K row, V column |
| `o` | `[32, 128]` | Recurrence output before gated RMSNorm |

For value head `h`, Q/K head `p(h) = floor(h/2)`. The logical state orientation
is K-by-V. Any V-by-K physical layout must expose explicit conversion routines
whose round trip is tested without arithmetic.

The step ordering and equations are exactly those in `AGENTS.md`. Gated RMSNorm,
`z`, projections, causal convolution, and `out_proj` are outside the kernel.

## Format Names

| Name | Definition |
|---|---|
| OCP MXFP4-B32 | 32 E2M1 elements plus one E8M0 shared scale; 17 bytes/block and 4.25 bits/value. |
| MX-like FP4-B16 | 16 E2M1 elements plus one E8M0 scale; custom research format, not OCP MXFP4 or NVFP4. |
| MXFP8-E4M3-B32 | 32 E4M3 elements plus one E8M0 scale. This is the required MXFP8 baseline. |
| Flat INT4 | Signed symmetric four-bit supplemental fallback with one declared tensor scale; never called MXFP4. |

All headline MXFP4 results use OCP B32. B16 may appear only as a labeled
ablation.

## E2M1 And E8M0 Encoding

E2M1 uses one sign bit, two exponent bits, and one mantissa bit.
For a finite E2M1 element, split the code into sign `s` and three magnitude
bits. Positive magnitudes decode to:

```text
code magnitude: 0  1    2  3    4  5  6  7
value:          0  0.5  1  1.5  2  3  4  6
```

The sign negates nonzero values. Both signed-zero encodings decode to zero and
the encoder emits canonical positive zero. E2M1 has no output NaN or infinity;
overflow saturates to the largest finite magnitude and increments a saturation
counter.

For a valid E8M0 scale byte `e` in `0..254`, the scale is
`2^(e - 127)`. Byte `255` is reserved as invalid/NaN and is rejected by load or
step validation. A zero block uses element code zero throughout and canonical
scale byte `127`; this avoids dependence on a subnormal scale convention.

Inputs containing NaN or infinity are contract violations. Software raises an
error; synthesizable code returns an error status without mutating resident
state. No silent NaN, infinity, or wraparound is allowed.

## Block Axis And Scale Selection

- Vector `q`, `k`, and `v` blocks run along their final 128-element feature
  axis in four consecutive B32 blocks.
- State blocks run along the V-column axis. Each `(layer, head, K-row)` has four
  consecutive B32 blocks.
- Output blocks use the V axis when an encoded output is requested.

For a nonzero finite block with maximum magnitude `m`, choose integer scale
exponent:

```text
s = ceil(log2(m / 6))
e = clamp(s + 127, 0, 254)
```

Quantize each `x` by RNE to the nearest representable E2M1 value after dividing
by `2^s`. Ties choose the code with an even least-significant magnitude bit.
Values beyond the finite range after exponent clamping saturate and increment
the block and global saturation counters. Scale selection is deterministic and
depends only on the unquantized block presented at that boundary.

The OCP specification defines the representation; this scale-selection and RNE
policy are design choices.

## Integer Product And Alignment

Represent each absolute E2M1 magnitude exactly as integer
`r in {0,1,2,3,4,6,8,12}` with decoded value `r / 2`. An element product is the
exact tuple:

```text
sign     = sign_a XOR sign_b
mantissa = r_a * r_b                 # 0..144, no rounding
power    = scale_power_a + scale_power_b - 2
```

The uniform encoded baseline forms one flat 128-term reduction. Every product
aligns directly to the greatest nonzero product power in that reduction. A
smaller-power signed mantissa is right-shifted by the full power difference
using RNE; a shift beyond the source width produces zero and records an
alignment-underflow event. No product is left-shifted to align with a smaller
exponent, and this baseline has no guard-bit offset.

Aligned terms accumulate in a signed 32-bit integer in a fixed documented order.
An implementation may use wider internal storage but must produce the same
32-bit boundary result. Positive and negative overflow saturate to the signed
32-bit endpoint and increment an accumulator-saturation counter. Wraparound is
prohibited.

## Reduction Order

Reductions are deterministic:

1. Find the greatest nonzero product power across all 128 key indices.
2. Align each signed product directly to that power using RNE.
3. Accumulate aligned terms in ascending key-index order with signed INT32
   saturation after each addition.
4. Apply alpha or beta using the fixed-point rule below.
5. Quantize only at an explicitly named tensor boundary.

Parallel hardware may reassociate internal operations only if its encoded result
is bit-identical to this order.

## Alpha And Beta

Alpha and beta use unsigned Q1.15 transport and arithmetic:

```text
code = RNE(clamp(x, 0, 1) * 32768)
value = code / 32768
valid codes = 0..32768
```

Codes `32769..65535` are invalid and cause an error without state mutation. Zero
and one are represented exactly. Multiplication uses a signed 64-bit
intermediate followed by a 15-bit RNE right shift and signed 32-bit saturation.
The previous `uint8 / 127` rule is forbidden.

## State Update And Requantization

The uniform MXFP4 baseline performs these boundaries for every token:

1. Decode the resident state block and align integer terms.
2. Apply alpha decay with Q1.15 arithmetic.
3. Compute the prediction from the decayed state.
4. Form `u` with beta after the subtraction.
5. Compute the rank-one write and add it to the decayed state.
6. Read `o` from the updated state.
7. Recompute each modified B32 state scale and requantize once using RNE.

No intermediate floating Q/DQ call is part of the encoded oracle. The oracle
must record every block scale, aligned accumulator, rounding decision,
saturation, underflow, and final state code. The reference output `o` is FP32
unless a separately named encoded-output experiment is run.

Stochastic rounding, fixed scales, periodic scale refresh, threshold refresh,
MXFP8 state, and a deferred-write log are separate variants. They may not alter
the baseline contract silently.

## Corrected E2M0-Residual Base And Write Log

The official update at this boundary is

```text
S_t = alpha_t S_(t-1) + k_t u_t^T
u_t = beta_t (v_t - k_t^T (alpha_t S_(t-1)))
```

For value head `h`, the exact lazy representation is therefore

```text
S_hat[h] = gamma_B[h] B[h]
           + sum_i lambda_i[h] k_i[p(h)] u_i[h]^T
```

The write sign is positive because `u` already contains `v - prediction`. A
minus sign with this definition of `u` would not equal the official recurrence.
This algebraic correction supersedes the subtractive form in the remediation
directive while preserving its intended lazy-decay mechanism.

For each token, exact mode performs:

1. Multiply `gamma_B[h]` and every live `lambda_i[h]` by `alpha_t[h]`.
2. Evaluate the prediction from the decayed base and every decayed live write.
3. Form `u_t[h]` using the per-value-head beta.
4. Append one shared key plus per-value-head writes with `lambda=1`.
5. Evaluate output from the state including the new write.
6. Fold only complete selected entries, quantize the replacement base at its
   declared boundary, reset the base coefficient, and remove exactly the folded
   entries.

Fixed folding is atomic across all value heads. A full log folds instead of
dropping or overwriting an entry. Pure decay updates only coefficients; it does
not rewrite the base. Coefficients that underflow their selected representation
trigger a documented rebase before their information can be lost. Exact mode
uses FP64 state, keys, writes, and coefficients and must match the independent
FP64 recurrence before any quantized candidate is evaluated.

The frozen corrected candidate is
`mxfp4_rs2_act_e2m1_e2m0_state_mxfp4rs2_log_r7_q1_15_int32_guard5`.
Its base state stores an E2M1 primary term and a dense signed three-bit
E2M0-style residual. Both use E8M0 B32 scales. Query, key, value, and live
rank-one write vectors use two-term E2M1/E8M0 B32 residual stacks. Seven live
writes are retained with unsigned Q1.15 decay coefficients.

Element products are integer table operations. In this corrected candidate,
shared exponents are aligned with five guard bits and accumulated in signed
INT32 using its frozen reduction order. Scale selection minimizes reconstruction error over the adjacent
candidate E8M0 scales, with deterministic tie handling. Alignment underflows
and deliberate E2M0 residual clips are counted separately from element
saturation, accumulator saturation, and scale clamps.

At log capacity, all seven entries fold atomically across value heads. The fold
reconstructs the effective state tilewise, requantizes the primary and residual
terms once, clears only the folded entries, resets their coefficients, and
admits the pending write without dropping or overwriting it. The non-mutating
snapshot command exposes every packed field, coefficient, counter, status, and
generation value for exact C-simulation comparison.

The earlier sparse residual-stack plus MXFP8 write-log candidate remains
preserved development history. It is not the selected encoded or HLS contract.

## Resident-State Control

Each command includes `sequence_id` and `layer_id`; valid layer IDs are `0..35`.
State is isolated by the pair `(sequence_id, layer_id)`. Sequence IDs are
unsigned indices in `0..NUM_SEQUENCES-1`; `NUM_SEQUENCES` is a declared build
parameter and is one for the controlled batch-one hardware comparison.

| Command | Code | Required behavior |
|---|---:|---|
| `RESET` | 0 | Set the selected state and metadata to canonical zero deterministically. Repeating reset is idempotent. |
| `LOAD` | 1 | Validate the complete encoded state and scales, then atomically replace the selected resident state. Partial failure leaves prior state and generation unchanged. |
| `STEP` | 2 | Execute exactly one token against the selected state and commit the new state atomically. |
| `READBACK` | 3 | Return all encoded elements, scales, counters, and generation number without changing them. |

The transport status is an unsigned integer with these frozen values:

| Status | Code | Meaning |
|---|---:|---|
| `OK` | 0 | Command completed. |
| `INVALID_COMMAND` | 1 | Command code is not 0 through 3. |
| `INVALID_SEQUENCE_ID` | 2 | Sequence selector is noninteger or outside the configured range. |
| `INVALID_LAYER_ID` | 3 | Layer selector is noninteger or outside `0..35`. |
| `UNINITIALIZED_STATE` | 4 | `STEP` or `READBACK` occurred before successful `RESET` or `LOAD`. |
| `MISSING_PAYLOAD` | 5 | `LOAD` has no state or `STEP` has no token. |
| `UNEXPECTED_PAYLOAD` | 6 | A command received a payload it does not consume. |
| `INVALID_ENCODING` | 7 | An element, scale, gate code, dtype, or encoded object is invalid. |
| `SHAPE_MISMATCH` | 8 | A validly encoded tensor does not match the configured shape or block size. |

`STEP` before `RESET` or `LOAD` returns an uninitialized-state error. Separate
kernel invocations must preserve initialized state. Interleaved layer and
sequence operations may not alias. A monotonically increasing generation
counter enables tests to detect dropped or duplicated writes. `RESET` starts a
new deterministic epoch at generation zero and clears cumulative counters.
Each successful `LOAD` or `STEP` increments generation exactly once. `READBACK`
and rejected commands do not change generation. A successful `LOAD` preserves
existing cumulative counters unless preceded by `RESET`.

Every returned state is a complete snapshot. Input buffers supplied to `LOAD`
and output buffers returned by any command may be reused or modified by the
caller without aliasing resident storage. A rejected command with a valid
selector leaves state bits and generation unchanged but increments the selected
slot's rejection counters. An invalid selector has no resident slot to update,
so only its per-command rejection counter is nonzero. Human-readable diagnostic
text is software-only and excluded from bit-exact comparison.

Validation precedence is sequence ID, layer ID, command code, command payload
presence, initialization, then encoded payload content and shape. This ordering
is part of status parity when one request violates more than one condition.

## Long-Trace Metrics

At each token, output cosine and output relative L2 flatten all value heads and
V coordinates into one vector. State relative L2 flattens all value heads, K
rows, and V columns; maximum absolute error is the maximum over that same full
state tensor. No per-head minimum, percentile, or acceptance gate is computed.

For candidate `x` and reference `r`, relative L2 is
`||x-r||_2 / max(||r||_2, 1e-12)`. If both arrays are exactly equal, the metric
function returns cosine 1, relative L2 0, and maximum absolute error 0. Otherwise,
if the cosine denominator is at most `1e-24`, cosine is 1 only when both norms
are at most `1e-12`; it is 0 when just one norm is effectively zero. These are
global flattened metrics, not headwise stability certificates.

## Finite-Horizon Error Envelope

For one head under the same external token inputs, let `E_t` be candidate minus
reference state and let `R_t` collect the exact local implementation residual.
With normalized `k_t`, the error transition is

```text
E_t = alpha_t (I - beta_t k_t k_t^T) E_(t-1) + R_t.
```

Writing `P_t = k_t k_t^T`, the squared Frobenius norm after the delta operator
is exactly

```text
||(I - beta_t P_t) E||_F^2
  = (1 - beta_t)^2 ||k_t^T E||_2^2 + ||(I - P_t) E||_F^2.
```

The delta gate attenuates only the component parallel to the current key. Since
`KEY_DIM=128`, the worst-case operator norm is one, and the one-step bound has
factor `alpha_t`. Unrolling gives

```text
||E_T||_F <= product(i=1..T, alpha_i) ||E_0||_F
           + sum(j=1..T, product(i=j+1..T, alpha_i) ||R_j||_F).
```

If every `alpha_i <= alpha_bar < 1` and `||R_i||_F <= R_bar`, this is at most
`alpha_bar^T ||E_0||_F + (1-alpha_bar^T) R_bar/(1-alpha_bar)`. The frozen
protocol permits decay arbitrarily close to one, so it has no uniform
contraction margin. Key variation may attenuate different directions, but no
persistent-excitation condition is assumed or established. The empirical gate
is therefore a finite-trace diagnostic, not a universal stability result.

## Required Counters

Counters are per command and cumulative per resident state:

- element saturation;
- accumulator saturation;
- scale clamp;
- alignment underflow;
- state-scale change;
- invalid encoding;
- rejected command; and
- committed state generation.

Counters are returned per command and cumulatively per selected resident slot.
The acceptance gate groups element saturation, accumulator saturation, and
E8M0 scale clamp as three preregistered hard-event counters. Alignment
underflows, state-scale changes, and deliberate E2M0 residual clips are reported
separately and are not included in that zero-hard-event condition. A zero hard
counter total must therefore never be described as lossless or event-free
arithmetic.
Malformed encoded payloads increment both `invalid encoding` and `rejected
command`; missing, unexpected, shape-mismatched, uninitialized, and unknown
commands increment only `rejected command`. A successful `LOAD` or `STEP`
returns one `committed state generation`; the cumulative value equals the slot's
generation within the current reset epoch. All counters are part of HLS C, RTL,
and board parity.

## Bit-Exact Boundary

Bit-exact comparison is restricted to:

```text
encoded-integer MX oracle == HLS C simulation == RTL cosimulation == board
```

It includes output bits, state element codes, state scale bytes, counters, error
status, and generation number after every command. FP64, FP32, BF16,
Transformers, and FLA comparisons use explicitly reported tolerances and are not
called bit-exact.

## Open Validation Items

| Item | Status | Required evidence |
|---|---|---|
| Independent FP64 scalar implementation | PASS | Hand-derived zero-state write, alpha/beta endpoints, paired heads, non-square orientation, random nonzero state, and FP32 tolerance tests in `docs/evidence/g1_g2_software_pytest.xml`. |
| Independent affine sequence cross-check | PASS | Seven-token random scalar recurrence versus independently derived affine state transition, maximum tested differences within FP64 test tolerance. |
| Official recurrent parity | PASS | Pinned Transformers FP32 fallback and FLA 0.2.1 BF16 outputs/states at 16/32 heads and K=V=128 in `reports/golden/official_parity/`. |
| Official chunk/recurrent parity | PASS | Same 128-token input executed through pinned recurrent and chunk/WY paths; all frozen tolerances pass. |
| Official cache-contiguous parity | PASS | A 64-token chunk prefill followed by 64 one-token recurrent calls matches contiguous execution within the frozen FP32/BF16 tolerances. |
| Encoded-integer MX step oracle | PASS | Independent source plus exhaustive valid E2M1 code pairs, signed RNE shifts, Q1.15 endpoints, invalid encodings, scale changes, underflow, paired heads, output ordering, and multi-token software tests. |
| Vectorized encoded-oracle cross-check | PASS | Every output mantissa/exponent and counter across the frozen 64-token full-dimension trace plus the complete final encoded state and scales match the scalar oracle exactly. |
| Native encoded 8192-token synthetic stability | FAIL | Artifact verification passes, but token-8192 cosine/state relative L2 are 0.429834/2.580730. There are no element/accumulator saturations or scale clamps and 2,685,620,693 alignment underflows. |
| Resident-state command oracle | PASS | Frozen command/status codes, canonical reset, deep-copy load/readback, all 36 layer IDs, sequence/layer isolation, atomic failure, counters, and generation tests in `tests/test_gdn_resident_state.py`. |
| Uniform-MXFP4 HLS C command parity | PASS | The 64-step frozen encoded trace plus 75 hand-command checks match outputs, complete state readback, statuses, generations, and counters in `reports/csim/corrected/`. |
| Uniform-MXFP4 HLS C synthesis extraction | PASS | Fresh U55C/4.0 ns report and source hashes are preserved in `reports/csynth/corrected/baseline_csynth_summary.json`. |
| Uniform-MXFP4 vendor loop constraints | PASS | All 14 explicitly targeted arithmetic/state loops achieve II=1. |
| Legacy Vitis-wrapper one-token RTL smoke | FAIL | The UVM wrapper exhausts XSIM memory before the first valid recurrent STEP completes; this preserved failure does not describe the direct harness. |
| Uniform-MXFP4 direct one-token RTL smoke | PASS | A bounded direct AXI harness executes RESET, STEP, and READBACK with exact selected checks. |
| Uniform-MXFP4 direct 64-token RTL parity | PASS | Every output and counter plus the complete final state, scales, status, and generation match the encoded oracle. |
| Exact lazy-base/write-log equivalence | PASS | FP64 exact mode covers capacity, folds, paired keys, per-head decay, pure decay, atomicity, and no-drop behavior. |
| Corrected scalar/vectorized encoded parity | PASS | Independent implementations agree field for field on the frozen corrected arithmetic and trace cases. |
| Corrected held-out high-retention gate | PASS | Three token-stream seed blocks crossed with random and zero initial states (six paired conditions) pass the locally registered engineering gate after deterministic recomputation. The original registration was not externally timestamped and omitted part of the execution dependency closure. |
| Corrected extended 8,192-token development gate | PASS | Random and zero-state conditions plus both full recomputations pass; minimum all-token cosine is 0.994389, maximum all-token state relative L2 is 0.099057, and the three preregistered hard-event counters total zero. |
| Corrected HLS arithmetic and 64-token resident C simulation | PASS | All 267 arithmetic cases and the stateful trace match outputs, counters, folds, and final snapshot. |
| Corrected HLS C synthesis extraction | PASS | The source-locked U55C report estimates a 3.108 ns path and records logic and command latencies. The estimate misses the configured 2.920 ns target-minus-uncertainty budget by 0.188 ns. Raw inferred memory counts are not physical-capacity evidence. |
| Corrected explicit II=1 constraints | FAIL | Three targeted loops achieve II=2. |
| Corrected HLS LUT/STEP advantage vs BF16 | FAIL | Candidate LUT, non-fold STEP, and amortized STEP estimates exceed the matched BF16 values. |
| Corrected INT32 bounded event check | PASS | Six held-out traces report zero accumulator saturation; this is bounded empirical evidence, not a universal overflow proof. |
| Corrected candidate 64-token RTL parity | FAIL / NOT_ESTABLISHED | Two isolated official XSIM attempts exhaust host memory before transaction one. Verilator 5.050 completes one exact generated-RTL LOAD, but zero recurrent STEPs complete; uniform-MXFP4 RTL evidence is not transferred. |
| Corrected out-of-context physical fit | PASS | Vivado routes the declared 36-slot candidate at 208,523 CLB LUTs, 353 BRAM tiles, and 624 URAMs. This excludes the U55C shell and complete-model storage. |
| Corrected routed target timing | FAIL | The design fails setup at 250 and 200 MHz; 180.18 MHz is the first passing point in the tested fixed-route sweep. |
| Native MXFP8 HLS and physical baseline | PASS with timing failure | Native E4M3/E8M0 C-sim, C-synthesis, and explicit II=1 constraints pass. The routed image fits at 58,582 LUTs and 576 URAMs, fails 250 MHz, and first closes at the tested 166.67 MHz point. |
| Matched all-layer BF16 physical attempt | FAIL capacity | Synthesis completes, but the unchanged BF16 state layout exceeds U55C memory capacity before placement; no smaller substitute is used. |
| Board bit parity | BLOCKED_EXTERNAL | Requires authorized U55C programming, bitstream/XRT logs, and the same command trace. |

The historical phase patch hashes remain in `docs/evidence_manifest.md`. Exact
execution-time source hashes for the uniform and corrected command traces,
C-simulation and C-synthesis reports, the local registration, held-out
recomputations, and extended development recomputations are stored in their JSON
manifests. The local registration is useful chronology evidence but is not an
externally notarized preregistration, and its original source list omitted some
runner dependencies. Official
recurrence parity and the independent MX reference are `PASS`. Corrected and
native-MXFP8 post-route evidence is complete. Corrected recurrent RTL parity is
not established, the BF16 physical attempt fails capacity, and board evidence
remains externally blocked.

# AGENTS.md - Evidence-Gated MXFP GDN Recurrence-Core Research

This file is the repository contract for autonomous work. The July 31, 2026
review directive supersedes the earlier MXFP4-primary phase plan.

Version 3, dated 2026-07-31.

## Objective

Determine whether native MXFP4 arithmetic can replace BF16-style arithmetic in
a persistent-state Qwen3-Next Gated DeltaNet (GDN) recurrence core while:

- preserving long-horizon recurrent-state stability;
- improving physically measured FPGA cost or energy at a matched boundary; and
- remaining distinguishable from prior persistent-state, quantized-state, and
  MXFP FPGA work.

Persistent recurrent state, paired-head sharing, and the five-stage dataflow are
inherited from prior work. They are not contributions by themselves. Until the
prior-art matrix and experiments support a narrower claim, use no claim of
"first", "novel", "certified", "guaranteed", or "minimum precision".

The maximum permitted completion label is `READY FOR HUMAN SUBMISSION REVIEW`.
It is never a guarantee of acceptance.

## Status Vocabulary

Every requirement uses exactly one status:

- `PASS`
- `FAIL`
- `NOT_RUN`
- `BLOCKED_EXTERNAL`

Any `FAIL`, `NOT_RUN`, or `BLOCKED_EXTERNAL` item in the final completion gate
means `NOT PAPER READY`. A script prepared for a different machine is not
experimental evidence.

For each `PASS`, `docs/evidence_manifest.md` must record the command and exit
code, source revision and dirty-patch hash, input hashes, configuration and
seeds, tool versions, raw output path, independent verification method, and
timestamp.

## Preserving Evidence

- Never overwrite or delete the submitted PDF or prior generated evidence.
- Store preserved material under `legacy/` and label invalidated results as
  legacy rather than reusing them.
- A recurrence, kernel-boundary, arithmetic-contract, or target change
  invalidates dependent C simulation, RTL, synthesis, implementation, power,
  benchmark, table, and figure results.
- `paper/numbers.json` and `paper/provenance.json` are generated outputs. Do not
  hand-edit measurements or generated LaTeX.
- Do not push, publish, submit, or open a pull request without approval.

Ask before large model or dataset downloads, licensed-tool installation,
multi-hour synthesis sweeps, paid compute, or FPGA programming.

## Authoritative Recurrence

Pin the official Qwen3-Next checkpoint and software sources in the evidence
manifest. For value/state head `h` in `0..31`, let `p(h) = floor(h/2)` select one
of 16 query/key heads. The logical state is K-by-V with `K = V = 128`.

After depthwise causal convolution and SiLU, the recurrence inputs have shapes:

```text
q, k: [B, T, 16, 128]
v:    [B, T, 32, 128]
z:    [B, T, 32, 128]
a, b: [B, T, 32]
```

For token `t` and value head `h`:

```text
q_norm = q[p(h)] * rsqrt(sum(q[p(h)]^2) + 1e-6)
k_norm = k[p(h)] * rsqrt(sum(k[p(h)]^2) + 1e-6)

beta  = sigmoid(b[h])
g     = -exp(A_log[h]) * softplus(a[h] + dt_bias[h])
alpha = exp(g)

S_decay = alpha * S_prev[h]
u       = beta * (v[h] - transpose(k_norm) * S_decay)
S_new   = S_decay + k_norm * transpose(u)
o[h]    = transpose(q_norm / sqrt(128)) * S_new
```

Required ordering:

1. Decay the state.
2. Predict from the decayed state.
3. Form the beta-scaled delta.
4. Apply the rank-one write.
5. Read the output from the updated state.

The post-recurrence operation is gated RMSNorm, not elementwise gate
multiplication:

```text
y[h] = RMSNorm(o[h], learned_weight, eps=1e-6) * SiLU(z[h])
```

The heads are concatenated and passed through `out_proj`.

## Hardware Boundary

The preferred boundary is the **GDN recurrence core**.

Inputs:

- normalized and `1/sqrt(128)`-scaled query;
- normalized key;
- post-convolution value;
- alpha and beta in `[0, 1]`; and
- resident-state control or explicit state load data.

Outputs:

- recurrence output `o`; and
- updated recurrent state.

Gated RMSNorm, `z`, projections, convolution, and `out_proj` remain outside the
kernel unless implemented and included in every baseline. Do not call the
kernel a complete GDN layer without that larger boundary.

If hardware stores V-by-K, document the transpose and test round trips in both
directions.

## Reference Hierarchy

Maintain three separate references:

1. An independent FP64 mathematical oracle.
2. Pinned official Transformers and FLA references, compared using
   dtype-appropriate tolerances.
3. An independently structured encoded-integer MX oracle that specifies every
   scale, alignment, rounding, saturation, and state-write point.

Only encoded MX oracle versus HLS C simulation, RTL cosimulation, and board
output may be called bit-exact. FP32/BF16 comparisons use numerical tolerances.
Test recurrent versus chunk execution and prefill-plus-decode versus contiguous
execution.

## Numerical Scope

- OCP MXFP4-B32 is E2M1 plus one E8M0 scale per 32 elements: 17 bytes per
  block, or 4.25 bits/value.
- E8M0 with 16 elements is custom `MX-like FP4-B16`, not OCP MXFP4 or NVFP4.
- Name MXFP8 explicitly as E4M3 or E5M2.
- This design selects round-to-nearest, ties-to-even (RNE); do not attribute the
  entire recurrence arithmetic policy to OCP.
- The numerical contract in `docs/numerical_contract.md` is authoritative for
  block axes, scale selection, exceptional values, products, alignment,
  reduction, accumulator widths, quantization boundaries, alpha/beta, and
  state-control semantics.
- The existing unsigned beta divided by 127 is prohibited because it can exceed
  one.

## Required Correction Tests

Correct state decay, initialization, reset, scale use/update, active exponent
alignment, changing scales, orientation, layer/sequence selection, persistence,
and output semantics before accepting HLS evidence.

Tests must cover random nonzero state; alpha/beta endpoints; changing exponents;
extreme magnitudes; cancellation; saturation; multiple tokens; sequence reset;
interleaved layers; load/readback; all 36 GDN layer IDs; and adversarial vectors
with independently computed expectations. Source-string checks and trivial
zero-state vectors are not correctness evidence.

## Evidence Gates

Work proceeds in order:

1. `G0`: read-only repository, manuscript, provenance, evidence, and prior-art
   audit.
2. `G1`: exact official recurrence and reference parity.
3. `G2`: encoded numerical oracle and corrected HLS baseline.
4. `G3`: software-only novelty feasibility and held-out selection.
5. `G4`: real closed-loop Qwen evaluation with cache-faithful decode.
6. `G5`: model-wide GDN recurrent-state subsystem and physical implementation.
7. `G6`: U55C board parity, telemetry, and matched baselines.
8. `G7`: evidence-only paper rewrite, provenance validation, and rendered PDF
   audit.

Do not let an earlier green report validate code changed by a later gate.

PDF release is staged to avoid circular authorization. After every upstream
experimental and hardware gate passes, an internal
`paper_audit_candidate.pdf` may be compiled solely for page-by-page review; it
must be marked ineligible for submission. The final `paper.pdf` may only be an
exact-byte copy of that audited candidate, and may only be created after all
eleven completion gates pass. The paper pack is subject to the same all-PASS
gate.

## Evaluation Requirements

The primary arithmetic comparison is controlled at the recurrence-core boundary
with the same layer, state layout, target, block size, and parallelism. Required
baselines are BF16 state, uniform MXFP8 state, uniform MXFP4 state, and MXFP4
compute with MXFP8 state. INT4 is supplemental.

Long-trace checkpoints include 64, 256, 1024, 4096, and 8192 decode tokens.
Report output cosine similarity, state relative L2 error, maximum state error,
and all saturation/overflow events over token index. Real-model quality requires
closed-loop replacement; offline activation captures are diagnostic only.

Hardware comparisons use the same recurrence boundary. Vivado power multiplied
by simulated latency is estimated energy, not board energy. GPU energy may not
be derived from TDP.

For Qwen3-Next-80B-A3B, separately account for all 36 GDN states, convolution
state, full-attention KV cache, weights, activations, buffers, and host traffic.
Use the phrase **model-wide GDN recurrent-state subsystem**, not complete model
residency.

## Candidate Research Direction

A lazily decayed MXFP4 base plus a bounded higher-precision rank-one write log is
only a hypothesis. Establish exact-arithmetic equivalence and a precise
prior-art gap before naming or implementing it in HLS. Select at most one
mechanism after preregistered software experiments show a Pareto improvement in
quality, physical memory, average and p99 latency, and energy.

Do not call an empirical drift controller certified or error-bounded unless a
conservative finite-arithmetic bound includes every implemented error source,
is independently checked, contains all observed adversarial error, and remains
non-vacuous on real traces.

## Completion Gate

`READY FOR HUMAN SUBMISSION REVIEW` requires all of the following to be `PASS`:

- defensible prior-art gap;
- exact official recurrence parity;
- independent encoded-integer MX reference;
- HLS C simulation and RTL bit parity;
- closed-loop real-model quality;
- selected method's Pareto advantage;
- physical all-layer state-bank fit;
- post-route timing and DRC;
- real-board parity and energy;
- complete reviewer traceability; and
- paper provenance and final PDF visual audit.

Otherwise report `NOT PAPER READY` and state exactly what remains.

## Stop And Ask

Stop for human input before any large download, paid run, multi-hour synthesis,
tool installation, FPGA programming, publication, submission, push, or pull
request. Also stop if prior art is substantially equivalent, a gate cannot be
made reproducible, HLS cannot close timing after a bounded repair pass, RTL
parity remains unexplained after one debug pass, the implementation does not
fit, or final provenance validation fails.

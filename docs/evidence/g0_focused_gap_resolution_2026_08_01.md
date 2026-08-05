# Focused Prior-Art Gap Resolution

Date: `2026-08-01`

Source revision: `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`

## Decision

The author selected the controlled arithmetic-replacement study proposed in
`docs/prior_art_matrix.md`:

> Can native MXFP4 arithmetic replace BF16-style arithmetic in a persistent-
> state Gated DeltaNet FPGA decode kernel while maintaining recurrent-state
> stability over long token sequences?

Status: `PASS` for contribution framing.

## Fixed Baseline

The comparison must hold constant the official Qwen3-Next recurrence-core
boundary, persistent-state layout, five-phase token dataflow, U55C target,
block size, `P_K`, and `P_V`. Persistent state, paired-head handling, and the
five phases are inherited from Gupta et al. and are not contributions.

## Residual Gap

The bounded primary-source search in
`docs/evidence/g0_prior_art_refresh_2026_08_01.md` found nearby work on:

- persistent BF16 GDN FPGA decode;
- quantized GDN chunk computation;
- persistent INT8 state-space inference;
- recurrent-state reduction and diagnostics;
- MXFP4 attention and scale selection; and
- native MXFP arithmetic on FPGA.

It did not locate a matched study that combines the pinned token-serial Qwen3-
Next recurrence, native OCP MXFP4-B32 recurrent-state arithmetic, long-horizon
state-drift measurement, and controlled U55C comparison against the inherited
BF16 dataflow. This is a bounded search result, not proof of universal novelty.

## Permitted Contribution Language

The paper may claim a controlled evaluation of native MXFP4 feasibility and a
machine-traceable characterization of synthetic recurrent-state stability. It
may report LUT-based E2M1 multiplication and block-exponent-aware accumulation
when supported by generated RTL and tool reports.

The paper must not claim novelty for persistent state, the five-phase pipeline,
paired-head semantics, the OCP format, generic LUT low-bit multiplication, or
generic FPGA MX arithmetic. A residual stack or write log is a secondary
mitigation with close constituent prior art unless a later gate supports a more
specific claim.

## Remaining Independent Gates

This framing decision does not establish numerical quality, BF16-relative
physical cost, post-route timing, energy, board behavior, real-model quality,
or paper readiness. Those requirements retain their own `PASS`, `FAIL`,
`NOT_RUN`, or `BLOCKED_EXTERNAL` status.

# Corrected Paper Reframing Blueprint

Status: **NOT PAPER READY**. This is a planning artifact, not manuscript text
and not permission to generate a submission PDF.

## Working Title

**Can MXFP4 Replace BF16 in a Persistent-State Gated DeltaNet FPGA Kernel?**

The title states the controlled question and does not imply a positive answer.
"GDN recurrence core" should replace "GDN layer" wherever the implemented
boundary matters.

## Research Question

Can native OCP MXFP4-B32 arithmetic replace BF16-style arithmetic in the same
persistent-state GDN recurrence-core decode kernel while reducing FPGA
cost/energy and maintaining recurrent-state stability over long token
sequences?

The comparison holds fixed the corrected recurrence, K-by-V state layout, 36
runtime layer slots, inherited five-phase dataflow, AMD Alveo U55C target,
4.0 ns HLS constraint, `P_K=16`, `P_V=8`, and B32 blocking.

## Introduction Logic

1. Define the fixed-size recurrent state and why repeated low-precision state
   writes can accumulate error over autoregressive decode.
2. Attribute persistent on-chip state and the five-phase FPGA dataflow to Gupta
   et al. They are the inherited baseline, not contributions.
3. Explain that OCP MXFP4 reduces logical state payload but changes range,
   rounding, block-scale, alignment, and state-requantization behavior.
4. State the controlled replacement question before describing implementation
   details or results.
5. End with evidence-backed contributions only.

## Contribution Ledger

| Candidate contribution | Evidence status | Permitted wording |
|---|---|---|
| Correct native encoded MXFP4 arithmetic for the GDN recurrence core | PASS at encoded oracle, HLS C, and 64-token direct generated-Verilog parity | "We implement and bit-exactly verify..." only at each completed boundary; do not imply post-route or board validation. |
| Long-horizon recurrent-state stability characterization | PASS for deterministic synthetic diagnostics | "We characterize one controlled synthetic trace through 8192 tokens..." |
| Matched BF16 versus uniform-MXFP4 HLS comparison | PASS extraction; MXFP4 cost advantage FAIL | Report the negative LUT/STEP result without implying post-route performance. |
| Logical state-capacity accounting | PASS calculation; physical fit NOT_RUN | Report bytes and ideal primitive lower bounds; do not claim placement or fit. |
| Scale-refresh policy ablation | PASS execution; all policies FAIL the frozen gate | Report fixed, every-token, periodic, and threshold results as negative ablations. |
| Residual-stack/write-log mitigation | Nominal synthetic PASS; stress FAIL; HLS/physical NOT_RUN | Secondary diagnostic only, with constituent prior art and no novelty claim. |

## Results Order

1. **Numerical correctness.** Official recurrence parity, independent scalar and
   encoded oracles, HLS C parity, and completed current-source RTL evidence.
2. **Long-sequence stability.** FP32, BF16, native/uniform MXFP4, MXFP8-E4M3
   state fallback, and flat INT4 at 64/256/1024/4096/8192 tokens.
3. **Scale-policy ablation.** Stability, maximum state error, clipping, scale
   changes, and alignment events.
4. **Controlled HLS cost.** Same boundary and design parameters for BF16 and
   uniform MXFP4; distinguish extraction PASS from advantage FAIL.
5. **Capacity and physical caveat.** Logical bytes and ideal primitive lower
   bounds followed by the still-unrun banking/placement result.
6. **Limitations.** Layer boundary, synthetic traces, one development seed for
   the uniform study, no closed-loop model quality, no post-route result, and no
   board energy.

## Current Answer

The current controlled answer is negative for uniform MXFP4. It saves logical
state storage but both native encoded and floating-Q/DQ diagnostics fail the
frozen synthetic stability criterion, and the HLS implementation uses more LUTs
with a longer estimated STEP loop than the matched BF16 baseline. Energy and
physical fit are unmeasured.

## Claims Prohibited

- novelty for persistent state or the inherited five-phase dataflow;
- complete GDN-layer or full-model acceleration;
- full Qwen3-Next, 3:1 hybrid-model, perplexity, or downstream-accuracy
  preservation;
- realistic activation fidelity from synthetic traces;
- physical all-layer fit from logical bytes or HLS-reported memory totals;
- measured energy from Vivado power multiplied by simulated latency;
- GPU superiority from TDP or unmatched published numbers;
- "first," "novel," "certified," or "guaranteed" without the required prior-art
  and finite-arithmetic evidence.

## Rewrite Gate

No Introduction, Contributions, Results, Conclusion, canonical paper numbers,
or final PDF should be promoted from this blueprint until
`reports/final_completion_gate.json` reports all eleven requirements `PASS` and
`paper_pdf_permitted: true`.

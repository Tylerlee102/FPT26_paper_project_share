# Prior-Art Matrix

Audit date: `2026-08-02`

The 2026-08-02 archival-metadata refresh is preserved at
`docs/evidence/prior_art_archival_refresh_2026_08_02.csv`. The corrected
manuscript-reference audit is
`docs/evidence/citation_archival_audit_2026_08_03_v3.csv`. The expanded focused
query recheck is preserved at
`docs/evidence/prior_art_gap_recheck_2026_08_02_v2.md`; it leaves the earlier
same-day recheck intact as superseded evidence.

## Gate Result

| Requirement | Status | Conclusion |
|---|---|---|
| Primary sources located and pinned | PASS | Official or author-controlled sources were located for the model, software stack, format, device/platform, and the closest architecture/quantization work. |
| Broad legacy novelty claim | FAIL | Persistent on-chip GDN state, a five-stage FPGA decode pipeline, paired-head handling, low-precision recurrent state, and FPGA MXFP arithmetic each have prior art. |
| Focused arithmetic-replacement framing | PASS | The expanded bounded search found no exact report of the delivered layer-level synthetic-drift and matched-U55C-HLS study. This is a defensible empirical scope, not proof of universal novelty, closed-loop quality, or physical FPGA validation. |
| Recurrence-aware residual plus rank-one write log | PASS | Residual buffers, lazy/deferred state handling, rank-one recurrent writes, and error feedback have close constituent prior art. The implemented candidate is classified as a mitigation and is not claimed as a first or standalone novelty. |

The project must not claim novelty for persistent state, the five-stage
pipeline, paired-head key reuse, LUT-based low-bit multiplication in general, or
MXFP on FPGA in general. The paper's contribution is a controlled empirical and
hardware evaluation at the exact recurrence-core boundary. Any write-log or
residual-state mechanism remains a mitigation with close constituent prior art,
not the headline novelty. All implementation and quality claims remain subject
to their separate evidence gates.

## Focused Gate Resolution

The author explicitly selected the following research question:

> Can native MXFP4 arithmetic replace BF16-style arithmetic in a persistent-
> state Gated DeltaNet FPGA decode kernel while maintaining recurrent-state
> stability over long token sequences?

The prior-art gate is `PASS` only for bounded overlap control and contribution
framing. The expanded search found close work on every constituent but no
matched report combining the pinned Qwen3-Next token recurrence, OCP
MXFP4-B32 state/update arithmetic, complete 64--8192-token layer-level
synthetic drift measurement, and controlled U55C HLS comparison against the
inherited BF16 boundary. The paper must not convert that negative search result
into a claim of first use, architectural novelty, closed-loop quality, or
physical implementation.

The selection record is `docs/evidence/g0_focused_gap_resolution_2026_08_01.md`;
the expanded independent recheck is
`docs/evidence/prior_art_gap_recheck_2026_08_02_v2.md`.

## Reference [4] Bibliographic Resolution

The closest FPGA baseline must be cited as a preprint, not as an archival
publication:

> Neelesh Gupta, Peter Wang, Rajgopal Kannan, and Viktor K. Prasanna,
> "A Persistent-State Dataflow Accelerator for Memory-Bound Linear Attention
> Decode on FPGA," arXiv:2603.05931v1 [cs.AR], Mar. 6, 2026,
> doi: 10.48550/arXiv.2603.05931.

| Field | Verified value | Primary record |
|---|---|---|
| Authors | Neelesh Gupta; Peter Wang; Rajgopal Kannan; Viktor K. Prasanna | [arXiv abstract record](https://arxiv.org/abs/2603.05931) |
| Version and date | `arXiv:2603.05931v1`, submitted 2026-03-06 | [arXiv submission history](https://arxiv.org/abs/2603.05931) |
| Subject/status | `cs.AR`, cross-listed `cs.LG`; six-page preprint | [arXiv abstract record](https://arxiv.org/abs/2603.05931) |
| DOI | `10.48550/arXiv.2603.05931`, issued for the arXiv record through DataCite | [arXiv DOI link](https://doi.org/10.48550/arXiv.2603.05931) |
| Archival venue | None listed as of 2026-08-01; DBLP records it as CoRR and an informal/other publication | [DBLP record](https://dblp.org/rec/journals/corr/abs-2603-05931) |

The final bibliography must not invent a conference, publisher, page range, or
archival DOI. Directive-23 is closed for metadata verification; replacing the
preprint with an archival version remains a G7 recheck.

## Bounded Narrow-Gap Search

The 2026-08-01 refresh searched arXiv, OpenReview, PMLR/proceedings records,
DBLP, IEEE, and exact-title web indexes with these query families:

1. `("MXFP4" OR "FP4") AND ("Gated DeltaNet" OR "linear attention") AND ("recurrent state" OR "state quantization")`
2. `"quantized recurrent state" AND ("rank-one" OR "write log" OR "lazy decay" OR "error feedback")`
3. `"Gated DeltaNet" AND ("FP4" OR "FP8" OR "INT8")`
4. `"MXFP4" AND ("recurrent state" OR "FPGA" OR "attention")`

No located record combined the pinned Qwen3-Next token recurrence, native OCP
MXFP4 state arithmetic, complete 64--8192-token layer-level synthetic drift,
and a matched U55C HLS comparison. This bounded negative result supports the
focused controlled-study framing; it does not prove universal novelty or fill
the unrun closed-loop and physical gates.

| Newly checked work | Relevant overlap | Why it does not establish the exact gap | Status |
|---|---|---|---|
| [When Good Enough Is Optimal, ICML 2026](https://openreview.net/pdf?id=RzLGgyuv0C) | Quantized Gated DeltaNet chunk computation and low-bit integer arithmetic | Targets chunk-wise matrix inversion rather than token-serial quantized recurrent-state replacement | PASS |
| [SSDi8, ICLR 2026](https://openreview.net/forum?id=pjMDZJd4rT) | Persistent INT8 state-space inference with adaptive quantization and error correction | Different recurrence, format, and hardware boundary | PASS |
| [State Rank Dynamics in Linear Attention LLMs, arXiv:2602.02195](https://arxiv.org/abs/2602.02195) | Long-running recurrent-state diagnostics and rank structure | Studies state dynamics/reduction, not MXFP4 arithmetic or FPGA realization | PASS |
| [The Key to State Reduction in Linear Attention, OpenReview](https://openreview.net/forum?id=GfjoMXfaXq) | Rank-based recurrent-state reduction | Changes state representation structurally rather than replacing arithmetic at a matched baseline | PASS |
| [MXAttention, arXiv:2607.24377](https://arxiv.org/abs/2607.24377) | MXFP4 attention quantization and scale selection | Targets softmax attention, not a recurrent GDN state | PASS |
| [Benchmarking PTQ under MXFP, arXiv:2601.09555](https://arxiv.org/abs/2601.09555) | MXFP4 post-training quantization and scale sensitivity | Model-level benchmark without the recurrent FPGA kernel boundary | PASS |

## Pinned Research Inputs

| Component | Pinned revision/version | Primary source | Status |
|---|---|---|---|
| Qwen3-Next-80B-A3B-Instruct | `9c7f2fbe84465e40164a94cc16cd30b6999b0cc7` | [Official model repository](https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct) | PASS |
| Transformers | annotated tag object `76d27aea82449e921e36afdc886c6e5bf34ea526`; peeled commit `8ac2b916b042b1f78b75c9eb941c0f5d2cdd8e10` | [Official Qwen3-Next implementation at v4.57.0](https://github.com/huggingface/transformers/blob/v4.57.0/src/transformers/models/qwen3_next/modeling_qwen3_next.py) | PASS |
| flash-linear-attention | tag `v0.2.1`, commit `a670dff4c2537fc1a82486584dd9569e18fba833` | [Official repository](https://github.com/fla-org/flash-linear-attention) | PASS |
| causal-conv1d | tag `v1.5.3.post1`, commit `52949d0891770c65243ed24db8abb66ef37741b7` | [Official repository](https://github.com/Dao-AILab/causal-conv1d) | PASS |
| PyTorch | tag `v2.8.0`, commit `ba56102387ef21a3b04b357e5b183d48f0afefc7` | [Official release index](https://pytorch.org/get-started/previous-versions/) | PASS |
| Triton | tag `v3.4.0`, commit `c817b9b63d40ead1ed023b7663f5ea14f676f4bc` | Official Git repository tag | PASS |
| CUDA Toolkit | `12.8.1` | [NVIDIA release notes](https://docs.nvidia.com/cuda/archive/12.8.1/cuda-toolkit-release-notes/index.html) | PASS |
| OCP Microscaling Formats | MX specification `v1.0`, September 2023 | [OCP primary specification](https://www.opencompute.org/documents/ocp-microscaling-formats-mx-v1-0-spec-final-pdf) | PASS |
| U55C device | DS978 `v1.3`; `xcu55c-fsvh2892-2L-e` | [AMD U55C data sheet](https://docs.amd.com/r/en-US/ds978-u55c/Product-Details) | PASS |
| U55C Vitis platform | `xilinx_u55c_gen3x16_xdma_3_202210_1`; UUID `97088961feaeda9152a21d9dfd63ccef`; `base_3` dynamic region | [AMD platform guide](https://docs.amd.com/r/en-US/ug1120-alveo-platforms/U55C-Gen3x16-XDMA-base_3-Platform) | PASS |
| WikiText protocol data | repository commit `b08601e04326c79dfdd32d625aee71d232d685c3` | `Salesforce/wikitext` | PASS |
| PG-19 protocol data | repository commit `4d28bd77e66947ad3835cf78ed7aaeb4dd87ad8b` | `deepmind/pg19` | PASS |

The platform is pinned as a published target, but the matching `.xpfm` was not
found in the local installation. Local platform execution is therefore not a
hardware `PASS`.

## Architecture And Algorithm Overlap

| Mechanism or claim | Closest primary source | Established result | Overlap with this project | Residual question | Status |
|---|---|---|---|---|---|
| Gated DeltaNet recurrence | [Gated Delta Networks, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/4904fad153f6434a7bcf04465d4be2cc-Paper-Conference.pdf) | Gated decay plus delta-rule recurrent state. | The mathematical operator and state update are inherited. | Arithmetic replacement and FPGA realization at the exact Qwen boundary. | PASS |
| Delta-rule linear attention | [DeltaNet, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/d13a3eae72366e61dfdc7eea82eeb685-Abstract-Conference.html) | Delta-rule fast-weight recurrence and chunk formulations. | Rank-one erase/write structure is inherited. | Quantization-induced recurrent drift under exact Qwen semantics. | PASS |
| Persistent-state five-stage FPGA decode | [Gupta et al., arXiv:2603.05931](https://arxiv.org/abs/2603.05931) | U55C persistent on-chip state, paired-head GVA, and fused five-phase BF16 decode pipeline. | Direct overlap with the legacy architecture and claimed dataflow novelty. | Replace BF16 arithmetic while holding this dataflow constant. | PASS |
| Newer gated recurrence | [Gated DeltaNet 2, NVIDIA Research, 2026](https://research.nvidia.com/index.php/publication/2026-05_gated-deltanet-2-decoupling-erase-and-write-linear-attention) | Further separates erase/write behavior in linear attention. | Shows rapid evolution of the recurrence family and limits broad GDN novelty claims. | Exact applicability to pinned Qwen3-Next is outside current scope. | PASS |
| Quantized GDN chunk computation | [When Good Enough Is Optimal, ICML 2026](https://openreview.net/pdf?id=RzLGgyuv0C) | Low-precision GDN chunk/prefill computation with wider integer arithmetic. | Establishes quantized GDN arithmetic as prior art, though at a different execution boundary. | Token-serial recurrent state with OCP MXFP4 and long-horizon drift. | PASS |
| Residual high-precision recent buffer | [KIVI, ICML 2024](https://proceedings.mlr.press/v235/liu24bz.html) | Quantized main KV cache plus a recent full-precision residual buffer. | Strong conceptual overlap with a quantized base plus short higher-precision log. | Exact rank-one recurrent equivalence, decay coefficients, folding, and FPGA costs. | PASS |
| Quantized persistent state | [SSDi8, ICLR 2026](https://openreview.net/pdf?id=pjMDZJd4rT) | Persistent INT8 state-space path with adaptive quantization and error correction. | Overlaps mixed-precision recurrent state and empirical drift mitigation. | Official Qwen GDN, MXFP4 format, and a matched FPGA implementation. | PASS |
| Exact side cache beside recurrent state | [LoLA, TMLR submission](https://openreview.net/forum?id=3KhDA252y3) | Recent and sparse exact caches augment a recurrent linear-attention state. | Overlaps retaining selected writes outside the compressed state. | Quantization-error mitigation, exact GDN decay, and FPGA fold cost. | PASS |
| Split rank-one and matrix memory | [Tensor Cache, arXiv:2605.22884](https://arxiv.org/abs/2605.22884) | Recent key/value information is split between exact and matrix memories. | Overlaps a base plus explicit rank-one information. | Fixed quantization write log with matched recurrence-core hardware. | PASS |
| Auxiliary residual recurrence | [Residual Linear Attention, withdrawn ICLR 2026 submission](https://openreview.net/forum?id=dy6tnQMeyI) | Auxiliary recurrent residual state and clipping correct a base linear-attention path. | Overlaps residual-state correction language. | Numeric-format storage mitigation and FPGA implementation cost. | PASS |
| Recurrent-state rank diagnostics | [State Rank Dynamics in Linear Attention LLMs, arXiv:2602.02195](https://arxiv.org/abs/2602.02195) | Measures runtime rank dynamics and proposes state reduction. | Establishes that recurrent-state structure itself is an active optimization target. | Arithmetic-replacement stability under the pinned GDN recurrence. | PASS |
| Rank-based state reduction | [The Key to State Reduction in Linear Attention, OpenReview](https://openreview.net/forum?id=GfjoMXfaXq) | Uses state-rank structure to reduce linear-attention state. | Weakens generic claims about recurrent-state compression. | Native MXFP4 representation at an unchanged state layout. | PASS |
| FPGA microscaling accelerator | [Wen et al., QLlama, IEEE Embedded Systems Letters 17(5), 2025, pp. 337-340](https://doi.org/10.1109/LES.2025.3600563) | FPGA accelerator using microscaling quantization for Llama2 inference. | Weakens generic claims that microscaling arithmetic on FPGA is new. | Recurrence-specific state update and stability. | PASS |
| Versatile FPGA MXFP tensor block | [Jack of All Scales, arXiv:2607.13898](https://arxiv.org/abs/2607.13898) | FPGA MXFP4/MXFP6/MXFP8 dot products with multiple mapping styles. | Direct overlap with native MXFP arithmetic and FPGA datapath claims. | Persistent recurrent state semantics and long-trace quality. | PASS |
| MXFP4 exponent-aligned compute | MXFormer, arXiv:2602.12480 | MXFP4 compute-in-memory with block-exponent alignment. | Block alignment is not unique to this project. | FPGA recurrence integration at the matched boundary. | PASS |
| Mixed MXFP precision | [MicroMix, ICLR 2026](https://openreview.net/forum?id=P5OKoZdwlB) | Mixed MXFP4/6/8 execution and kernels. | Mixed-format fallback and policy ideas have broad precedent. | Recurrent state placement, drift, and U55C physical behavior. | PASS |
| MXFP4 softmax attention | [MXAttention, arXiv:2607.24377](https://arxiv.org/abs/2607.24377) | Data-free scaling and pre-normalization quantization for MXFP4 attention. | Establishes attention-specific MXFP4 scaling work. | Recurrent GDN state evolution rather than softmax attention. | PASS |
| MXFP post-training benchmark | [Benchmarking PTQ under MXFP, arXiv:2601.09555](https://arxiv.org/abs/2601.09555) | Benchmarks MXFP formats and reports that MXFP4 is sensitive to scale selection. | Reinforces that scale policy and quality must be measured rather than assumed. | Long-horizon recurrence and matched FPGA cost. | PASS |
| OCP MXFP4 representation | [OCP MX v1.0](https://www.opencompute.org/documents/ocp-microscaling-formats-mx-v1-0-spec-final-pdf) | E2M1 elements with E8M0 shared scale in B32 blocks. | The data format is standardized, not a contribution. | A fully specified recurrence arithmetic contract and state-update policy. | PASS |
| Stochastic rounding | [Gupta et al., ICML 2015](https://proceedings.mlr.press/v37/gupta15.html) | Stochastic rounding for low-precision training arithmetic. | Stochastic MXFP4 is an ablation, not a new mechanism by itself. | Its utility for inference-time GDN state drift. | PASS |
| Error-feedback quantization | Quantized Adam with Error Feedback, arXiv:2004.14180, plus later error-feedback literature | Feeds quantization residuals into later updates. | Error-feedback language or controllers require careful attribution. | A conservative GDN state-error mechanism and hardware cost. | PASS |

## Component Classification

| Component | Classification before new evidence | Reason |
|---|---|---|
| Persistent on-chip recurrent state | inherited | Directly claimed by Gupta et al. |
| Five-stage token pipeline | inherited | Directly claimed by Gupta et al. |
| Paired Q/K heads serving value heads | inherited | Present in model semantics and the prior FPGA design. |
| Official alpha-decayed Qwen recurrence | corrected | Missing from the repository baseline; required for correctness. |
| Gated RMSNorm outside the core | corrected | Legacy code used an incorrect elementwise gate. |
| OCP MXFP4-B32 storage | modified | Standard format applied to a recurrent state; format itself is inherited. |
| Encoded-integer recurrence oracle | newly implemented verification mechanism | Independent uniform and corrected arithmetic, resident commands, and HLS C checks pass. Uniform MXFP4 also has 64-token direct generated-Verilog parity. Corrected RTL has an exact LOAD but no completed recurrent STEP, so its 64-token parity is not established. This is verification infrastructure, not a standalone novelty claim. |
| Native uniform MXFP4 state datapath | modified and implemented baseline | HLS uses E2M1 arithmetic, E8M0 alignment, and recurrent state requantization. HLS C and direct generated-Verilog parity pass, but synthetic stability and matched HLS cost advantage fail. |
| E2M1/E2M0 residual base plus seven-entry log | evaluated mitigation | Exact equivalence, encoded held-out software, HLS C simulation, HLS synthesis, and out-of-context route exist. Quality passes through 1,024 held-out tokens; HLS cost/II and routed timing criteria fail, while recurrent RTL parity is not established. |
| Long-horizon recurrent-state stability study | controlled empirical evaluation | BF16, uniform MXFP4, MXFP8 state, flat INT4, and six scale policies were evaluated through 8,192 synthetic tokens. Closed-loop real-Qwen quality remains `BLOCKED_EXTERNAL`. |

## Focused Alternatives

1. **Controlled arithmetic-replacement study (selected).** Treat the prior BF16 persistent
   pipeline as the fixed baseline and ask whether OCP MXFP4-B32 can replace its
   arithmetic/state representation without long-horizon instability. The value
   would be rigorous negative or positive evidence, not a broad architecture
   claim.
2. **Recurrence-aware state representation.** Evaluate one bounded write-log or
   residual-state mechanism only after exact equivalence and software Pareto
   evidence. Attribute residual buffers, lazy updates, and error feedback.
3. **Verification contribution.** Build an independent encoded-integer oracle,
   adversarial state tests, and end-to-end provenance chain. This can support the
   other directions but is unlikely to carry the paper alone.

The selected paper direction is item 1. The corrected write-log candidate has
been implemented in HLS as a mitigation experiment. Its failed cost/II result
is reported directly and it is not promoted to a novel or Pareto-superior
architecture.

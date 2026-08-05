# Focused Prior-Art Gap Recheck, Revision 2

Date: `2026-08-02`

This revision preserves and supersedes
`docs/evidence/prior_art_gap_recheck_2026_08_02.md`. It was added after an
independent audit found that the first recheck omitted relevant MXFP work and
misclassified the QuantGDN paper as arXiv-only.

## Delivered-Scope Question

The bounded search tests only whether prior work reports the same controlled
study delivered by this artifact:

> At the pinned Qwen3-Next token-serial recurrence-core boundary, compare
> native OCP MXFP4-B32 state/update arithmetic with matched BF16, MXFP8-state,
> and INT4 paths using 64--8192-token layer-level synthetic drift metrics and a
> same-target U55C HLS cost estimate.

This scope excludes closed-loop model quality, physical FPGA implementation,
board energy, and architectural novelty. Those results are not present here.

## Query Families

1. `("MXFP4" OR "FP4") AND "Gated DeltaNet" AND recurrent state AND FPGA`
2. `"Gated DeltaNet" AND (FP4 OR FP8 OR quantization) AND state stability`
3. `(lazy OR deferred) AND recurrent-state update AND rank-one`
4. `linear attention AND (recent buffer OR exact cache OR write log)`
5. `recurrent-state quantization AND (residual OR error feedback)`
6. `MXFP4 AND (block exponent alignment OR scale policy OR underflow)`

The search covered arXiv, OpenReview, PMLR/proceedings records, IEEE records,
DBLP, official repositories, and exact-title web queries. A negative bounded
search is not proof that no equivalent work exists.

## Closest Primary Sources

| Work | Overlap | Distinction from the delivered study |
|---|---|---|
| [Gupta et al.](https://arxiv.org/abs/2603.05931) | U55C persistent state, paired heads, and five-phase BF16 GDN decode | Baseline dataflow; no MXFP4 replacement or long synthetic drift comparison |
| [QuantGDN, ICML 2026](https://openreview.net/pdf?id=RzLGgyuv0C) | Quantized GDN arithmetic and numerical stability | Chunk-wise matrix inversion on NPU-oriented execution, not token-serial MXFP4 recurrent state on FPGA |
| [QLlama](https://doi.org/10.1109/LES.2025.3600563) | FPGA microscaling quantization | Llama2 inference rather than persistent GDN state evolution |
| [Jack of All Scales](https://arxiv.org/abs/2607.13898) | Native FPGA MXFP4/6/8 tensor arithmetic | Agilex-5 tensor block without GDN recurrence semantics |
| [MXFormer](https://arxiv.org/abs/2602.12480) | MXFP4 block-exponent alignment | Charge-trap compute-in-memory Transformer accelerator, not a GDN FPGA recurrence core |
| [MicroMix](https://openreview.net/forum?id=P5OKoZdwlB) | Mixed MXFP4/6/8 execution | Blackwell GEMM and model quantization rather than recurrent state |
| [MXAttention](https://arxiv.org/abs/2607.24377) | MXFP4 scaling, clipping, and underflow | Softmax attention in video generation rather than GDN state feedback |
| [MXFP PTQ benchmark](https://arxiv.org/abs/2601.09555) | MXFP4/MXFP8 quality and scale sensitivity | Model PTQ benchmark without matched FPGA recurrence-core cost |
| [KIVI](https://proceedings.mlr.press/v235/liu24bz.html) | Quantized cache plus recent full-precision residual entries | Attention KV cache rather than exact decayed rank-one GDN writes |
| [SSDi8](https://openreview.net/forum?id=pjMDZJd4rT) | Persistent low-precision state and error correction | INT8 SSD/Mamba-2 path rather than OCP MXFP4 GDN on FPGA |
| [LoLA](https://openreview.net/forum?id=3KhDA252y3) | Exact recent/sparse caches beside a recurrent linear-attention state | Memory-capacity augmentation, not arithmetic-replacement stability or FPGA cost |
| [Tensor Cache](https://arxiv.org/abs/2605.22884) | Rank-one key/value information split between exact and matrix memories | Learned hybrid memory rather than a bounded quantization write log |
| [Residual Linear Attention](https://openreview.net/forum?id=dy6tnQMeyI) | Auxiliary recurrent residual state and residual clipping | Withdrawn model-architecture submission, not a storage/HLS mitigation |
| [State Rank Dynamics](https://arxiv.org/abs/2602.02195) | Long-running recurrent-state diagnostics | Rank reduction rather than numeric-format replacement |

The lazy/deferred-update and rank-one-log queries did not locate the exact
base-plus-decayed-write representation implemented here. The closest records
above nevertheless establish substantial constituent overlap. The correction
is therefore treated only as a mitigation and is not claimed as new or first.

## Result

Status: `PASS` for bounded study framing and overlap attribution.

No located primary source reports the exact combination of pinned Qwen3-Next
token recurrence, OCP MXFP4-B32 recurrent state/update arithmetic, complete
64--8192-token layer-level synthetic drift comparison, and matched U55C HLS
cost against the inherited BF16 boundary. This supports a narrow controlled
evaluation, including a negative result. It does not support a claim of
architectural novelty, closed-loop stability, physical FPGA validation, or
universal first use.

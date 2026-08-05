# Focused Prior-Art Gap Recheck

Date: `2026-08-02`

Scope: a bounded primary-source search for work that combines Gated DeltaNet,
MXFP4 recurrent-state arithmetic, long-token stability, and an FPGA
implementation at a matched BF16 recurrence-core boundary.

## Queries

1. `site:arxiv.org 2026 Gated DeltaNet FP4 quantization recurrent state FPGA`
2. `site:openreview.net "Gated DeltaNet" quantization state FPGA MXFP4`
3. `site:arxiv.org "MXFP4" recurrent state linear attention FPGA`
4. `site:arxiv.org "Gated DeltaNet" "FP4"`

## Closest Located Records

| Record | Direct overlap | Remaining distinction |
|---|---|---|
| [When Good Enough Is Optimal](https://arxiv.org/abs/2606.06034) | Quantized Gated DeltaNet arithmetic and numerical stability | Chunk-wise matrix inversion and INT arithmetic, not token-serial OCP MXFP4 recurrent-state replacement on FPGA |
| [Jack of All Scales](https://arxiv.org/abs/2607.13898) | Native FPGA MXFP dot-product implementation | Agilex-5 tensor/DSP architecture without GDN state semantics or long recurrent traces |
| [MXAttention](https://arxiv.org/abs/2607.24377) | MXFP4 scaling, clipping, and underflow behavior | Softmax attention for video generation, not recurrent GDN state |
| [MXFormer](https://arxiv.org/abs/2602.12480) | MXFP4 block-exponent-aligned accelerator arithmetic | Charge-trap compute-in-memory Transformer, not a matched FPGA recurrence core |
| [Pretraining large language models with MXFP4](https://arxiv.org/abs/2605.09825) | Controlled MXFP4 numerical-stability study | Training gradients on AMD GPUs rather than persistent inference state on FPGA |
| [SSDi8](https://openreview.net/forum?id=pjMDZJd4rT) | Quantized persistent state-space execution with error correction | INT8 SSD/Mamba-2 boundary, not OCP MXFP4 GDN on FPGA |

## Result

The recheck did not locate a record covering the exact controlled combination.
This negative search result supports only the paper's bounded study framing. It
does not prove first use, and it does not make the inherited persistent-state
or five-phase pipeline a contribution.

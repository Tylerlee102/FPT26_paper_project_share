# G0 Prior-Art And Reference [4] Refresh

Date: `2026-08-01`

Source revision: `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`

## Scope

This report resolves the bibliographic identity and publication status of the
closest persistent-state FPGA baseline, then records a bounded search for work
combining low-precision arithmetic with recurrent linear-attention state. It
does not certify novelty.

## Reference [4]

The verified record is:

> Neelesh Gupta, Peter Wang, Rajgopal Kannan, and Viktor K. Prasanna,
> "A Persistent-State Dataflow Accelerator for Memory-Bound Linear Attention
> Decode on FPGA," arXiv:2603.05931v1 [cs.AR], Mar. 6, 2026,
> doi: 10.48550/arXiv.2603.05931.

Primary-source checks:

- The [arXiv record](https://arxiv.org/abs/2603.05931) gives the exact title,
  four authors, submission date, version, subject classes, six-page length, and
  arXiv-issued DataCite DOI.
- The same record lists no journal reference or archival venue.
- [DBLP](https://dblp.org/rec/journals/corr/abs-2603-05931) classifies the work
  as CoRR and an informal/other publication.
- Exact-title searches of IEEE and ACM indexes did not locate an archival
  version on the audit date.

The arXiv abstract explicitly describes persistent 2 MB on-chip BRAM state, a
five-phase pipelined datapath, one state read/write pass per token, paired-head
Grouped Value Attention, the AMD Alveo U55C, and Vitis HLS. Those mechanisms are
baseline dataflow and cannot be claimed as contributions here.

## Search Protocol

Indexes checked: arXiv, OpenReview, PMLR/proceedings records, DBLP, IEEE, ACM,
and exact-title web indexes.

Query families:

1. `("MXFP4" OR "FP4") AND ("Gated DeltaNet" OR "linear attention") AND ("recurrent state" OR "state quantization")`
2. `"quantized recurrent state" AND ("rank-one" OR "write log" OR "lazy decay" OR "error feedback")`
3. `"Gated DeltaNet" AND ("FP4" OR "FP8" OR "INT8")`
4. `"MXFP4" AND ("recurrent state" OR "FPGA" OR "attention")`

The source-level classification is recorded in
`docs/evidence/prior_art_sources_2026_08_01.csv` and summarized in
`docs/prior_art_matrix.md`.

## Findings

- Persistent-state GDN FPGA decode and its five-phase U55C dataflow are direct
  prior art in Gupta et al.
- Quantized GDN chunk computation, persistent INT8 state-space execution,
  recurrent-state rank reduction, MXFP4 attention, MXFP4 scale-selection work,
  and generic FPGA MXFP compute are all nearby prior art.
- No located record combined all four constraints: the pinned Qwen3-Next token
  recurrence, native OCP MXFP4 recurrent-state arithmetic, long-horizon
  closed-loop stability, and a matched U55C implementation.
- Failure to locate that exact combination in a bounded search is not proof of
  novelty. The narrow gap and the proposed lazy write-log mechanism remain
  `NOT_RUN` until independent human review.

## Gate Interpretation

`PASS` applies only to source collection, overlap classification, and
Reference [4] metadata resolution. The broad legacy novelty claim remains
`FAIL`; the exact narrow gap remains `NOT_RUN`.

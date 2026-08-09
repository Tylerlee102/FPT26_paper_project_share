# Paper Artifact Status

Release state: **NOT PAPER READY**.

All eleven rows in `reports/final_completion_gate.json` are release-required.
Audit-PDF finalization and submission packaging remain blocked until every row
is `PASS`; failed or externally blocked research outcomes are not waived. A
visibly watermarked `corrected/mxfp4_gdn_working_draft.pdf` may be generated for
review.
Existing files named `corrected/paper_audit_candidate.pdf` and
`corrected/paper.pdf` predate this stricter gate and are retained only as stale
audit history. They must not be submitted or cited as the current paper.
The legacy manuscripts, PDFs, tables, figures, `numbers.json`, and
`provenance.json` in this directory are preserved for auditability. They were
produced before the corrected recurrence and kernel boundary and must not be
used as current paper evidence.

## Current Corrected Artifacts

The following artifacts are supported only for the narrow claims stated in
their manifests:

- `figures/corrected/rs2_output_cosine_vs_token.pdf`
- `figures/corrected/rs2_state_relative_l2_vs_token.pdf`
- `figures/corrected/rs2_memory_performance_accuracy.pdf`
- `figures/corrected/rs2_paper_figures_manifest.json`
- `figures/corrected/corrected_candidate_datapath.pdf`
- `figures/corrected/corrected_candidate_datapath_manifest.json`
- `corrected/paper.tex`
- `corrected/working_draft.tex`
- `corrected/mxfp4_gdn_working_draft.pdf` (watermarked, not submission eligible)
- `corrected/numbers.json`
- `corrected/provenance.json`
- `corrected/asset_manifest.json`
- `corrected/paper_audit_candidate.pdf` (stale, non-current)
- `corrected/paper_visual_audit.json` (stale, non-current)
- `corrected/paper.pdf` (stale, non-current)
- `corrected/paper_finalization_manifest.json` (stale, non-current)

The trace figures report layer-boundary synthetic traces. They do not establish
closed-loop model quality, perplexity, downstream accuracy, board parity, or
measured energy. Separate corrected reports support only the paper's scoped
out-of-context physical-fit, timing, DRC, and vectorless-power statements.

The paper-facing synthetic workload parameters are generated from
`docs/synthetic_trace_protocol.json`; a unit test checks that contract against
the actual nominal and high-retention trace generators.

The older write-log held-out figures in the corrected figure directory record
development history for a superseded candidate. They are not imported by the
current manuscript or its corrected asset manifest.

## Preserved Legacy Artifacts

All other existing paper PDFs, TeX sources, tables, snippets, and figures are
legacy snapshots unless the corrected machine-readable manifest explicitly
imports them. In particular:

- `FPT26_MXFP4_GDN_draft.pdf` and `example_research_paper_draft.pdf` are not
  submission candidates.
- `numbers.json` and `provenance.json` contain invalidated measurements and are
  not the canonical source for the corrected project.
- Legacy speedup, energy, accuracy, complete-layer, and novelty claims are
  unsupported by the corrected evidence.

The authoritative status and claim boundaries are maintained in
`docs/implementation_status.md`, `docs/evidence_manifest.md`, and
`docs/final_completion_gate.md`.

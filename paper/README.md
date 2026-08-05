# Paper Artifact Status

Release state: **READY FOR HUMAN SUBMISSION REVIEW**.

All eight release-required rows in `reports/final_completion_gate.json` pass.
The three nonpassing rows are deliberately nonrequired research outcomes:
Pareto advantage fails, while closed-loop real-model quality and board
parity/energy were not run. The compiled audit candidate passed page-by-page
inspection and was copied byte-for-byte to `corrected/paper.pdf`. Submission
packaging remains guarded by that exact current gate and finalization chain.
The legacy manuscripts, PDFs, tables, figures, `numbers.json`, and
`provenance.json` in this directory are preserved for auditability. They were
produced before the corrected recurrence and kernel boundary and must not be
used as current paper evidence.

## Current Corrected Artifacts

The following artifacts are supported only for the narrow claims stated in
their manifests:

- `figures/corrected/output_cosine_vs_token.pdf`
- `figures/corrected/state_relative_l2_vs_token.pdf`
- `figures/corrected/long_trace_plot_manifest.json`
- `figures/corrected/long_sequence_stability_panel.pdf`
- `figures/corrected/long_sequence_stability_panel_manifest.json`
- `figures/corrected/corrected_candidate_datapath.pdf`
- `figures/corrected/corrected_candidate_datapath_manifest.json`
- `corrected/paper.tex`
- `corrected/numbers.json`
- `corrected/provenance.json`
- `corrected/asset_manifest.json`
- `corrected/paper_audit_candidate.pdf`
- `corrected/paper_visual_audit.json`
- `corrected/paper.pdf`
- `corrected/paper_finalization_manifest.json`

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

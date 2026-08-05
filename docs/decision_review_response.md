# Decision-Review Response Matrix

This matrix maps the three cleaned decision reviews supplied on 2026-08-03 to
the current corrected manuscript and evidence. It supplements, but does not
renumber or replace, the authoritative 68-comment workbook ledger in
`docs/reviewer_traceability.md`.

Status describes the requested evidence, not merely whether prose was edited:

- `PASS`: the current source and cited artifact directly answer the concern
  within the paper's declared scope.
- `FAIL`: completed evidence contradicts the desired full-paper claim.
- `NOT_RUN`: the required experiment or physical comparison has not run.
- `BLOCKED_EXTERNAL`: completion requires an external asset or measurement that
  is unavailable for the declared study.

## Reviewer 1

| ID | Concern | Current response and boundary | Primary evidence | Status |
|---|---|---|---|---|
| D1.1 | Novelty relative to Gupta et al. is ambiguous. | The Introduction calls persistent state and the five-phase schedule inherited; the ownership table classifies every component and disclaims literature priority. | `paper/corrected/paper.tex`; `docs/prior_art_matrix.md` | PASS |
| D1.2 | Section IV mixes inherited architecture with modifications. | The FPGA section holds the inherited schedule fixed and identifies native arithmetic, corrected state representation, and folding separately. | `paper/corrected/paper.tex`; `paper/figures/corrected/corrected_candidate_datapath.pdf` | PASS |
| D1.3 | Identify unique structural changes and adopted structures. | The ownership table uses inherited, corrected, modified, and newly proposed classifications, with citations and a no-priority-claim note. | `paper/corrected/paper.tex`; `docs/prior_art_matrix.md` | PASS |
| D1.4 | INT4 is weak; FP8 should be the proper baseline. | A floating-Q/DQ MXFP8-E4M3 state baseline outperforms four-bit state numerically. Its matched native E4M3/E8M0 kernel passes arithmetic and persistent-kernel C-sim, C-synthesis, and all explicit II=1 constraints; the out-of-context image fits, fails 250 MHz, and first closes at the tested 166.67 MHz point. | `paper/corrected/tables/long_sequence.tex`; `paper/corrected/tables/controlled_hls.tex`; `reports/csynth/corrected/mxfp8_hls_summary.json`; `reports/vivado/baselines/mxfp8/mxfp8_vivado_summary.json` | PASS |
| D1.5 | Credit Gupta et al. directly. | The Introduction, related work, ownership table, and figure legend explicitly attribute persistent state, paired-head handling, and the five phases to Gupta et al. | `paper/corrected/paper.tex`; `docs/evidence/g0_prior_art_refresh_2026_08_01.md` | PASS |
| D1.6 | Obtain real data or add fidelity techniques and novelty. | A recurrence-aware residual/write-log mitigation improves bounded synthetic fidelity. Pinned layer-12 hidden states plus matching checkpoint projections now provide q/k/v/alpha/beta recurrence inputs for four real prompt traces. They are only 12--18 tokens and do not support perplexity or downstream-accuracy claims. | `paper/corrected/tables/corrected_quality.tex`; `paper/corrected/tables/qwen_recurrent_stability.tex`; `reports/benchmark/qwen_recurrent_stability_manifest.json` | PASS |
| D1.7 | Submit as a poster until the evidence is stronger. | The revision is recast as a scoped negative-result paper: uniform MXFP4 fails numerically and in matched HLS cost, while the correction physically fits but misses timing and loses the Pareto argument. Missing model/board evidence is a limitation, not filled by simulation. | `reports/final_completion_gate.json`; `paper/corrected/paper.tex` | PASS |

## Reviewer 2

| ID | Concern | Current response and boundary | Primary evidence | Status |
|---|---|---|---|---|
| D2.1 | The external-memory sentence is unclear. | The old sentence is absent. The corrected paper describes excluded state, weights, caches, activations, and traffic directly and makes no vague bandwidth claim. | `paper/corrected/paper.tex` | PASS |
| D2.2 | Figure 1 does not show a meaningful datapath. | The replacement figure shows command control, tensor dimensions, five phases, arithmetic, persistent base, recent-write log, rates, and fold timing. | `paper/figures/corrected/corrected_candidate_datapath.pdf`; `paper/figures/corrected/corrected_candidate_datapath_manifest.json` | PASS |
| D2.3 | Data-transfer sizes are missing. | Figure 1 and the FPGA text now report logical STEP input, expanded output, and state payload sizes. They explicitly label these as pre-AXI type-layout counts; measured traffic remains outside the claim. | `paper/corrected/paper.tex`; `paper/figures/corrected/corrected_candidate_datapath.pdf`; `paper/corrected/numbers.json` | PASS |
| D2.4 | Figure colors and blocks are unclear. | The caption defines gray, orange, teal, blue, and dashed paths; the figure has a matching legend and visually distinct labeled regions. | `paper/corrected/paper.tex`; `docs/evidence/corrected_candidate_datapath_220dpi_20260803.png` | PASS |
| D2.5 | Quantization is insufficiently explained. | The numerical method defines formats, block axes, scale selection, RNE, state-write boundaries, accumulator order, counters, and Q/DQ versus encoded evidence. | `paper/corrected/paper.tex`; `docs/numerical_contract.md` | PASS |
| D2.6 | Block-exponent selection is unclear. | The paper now gives the maximum-magnitude scale-power equation, E8M0 bias/clamp rule, zero-block convention, and RNE behavior. | `paper/corrected/paper.tex`; `golden/mx_format.py`; `docs/numerical_contract.md` | PASS |
| D2.7 | It is unclear which tensors were converted for test vectors. | The paper lists q, k, v, alpha, beta, and initial state, identifies every quantized boundary, and states why projection weights are absent from the recurrence-core vectors. | `paper/corrected/paper.tex`; `docs/synthetic_trace_protocol.json`; `docs/numerical_contract.md` | PASS |
| D2.8 | Synthetic traces omit real activation outliers. | A pinned Qwen layer-12 input capture quantifies its heavy tail, and matching checkpoint projections reconstruct q/k/v/alpha/beta for four short real-input recurrence traces. Long-horizon curves remain synthetic because the real traces contain only 12--18 valid tokens. | `reports/golden/qwen_capture_characterization.json`; `reports/benchmark/qwen_recurrent_stability_manifest.json`; `paper/corrected/paper.tex` | PASS |
| D2.9 | Block-exponent adjustment during multiplication is unclear. | The paper defines the exact integer product magnitude/power, dominant product power, exponent-difference shift, RNE, underflow event, and accumulator order. | `paper/corrected/paper.tex`; `docs/numerical_contract.md`; `hls/src/block_exp_align.cpp` | PASS |
| D2.10 | Synthetic accuracy cannot predict full-model quality. | The abstract, evaluation, limitations, figure captions, and conclusion label the long traces as layer-level synthetic diagnostics and make no perplexity or downstream-quality claim. The short model-derived recurrence traces are reported separately and do not fill that gap. | `paper/corrected/paper.tex`; `reports/benchmark/qwen_recurrent_stability_manifest.json`; `docs/experimental_protocol.md` | PASS |
| D2.11 | Use "element multiplier," not "element multiply." | The current paper uses "element multiplier" or "element product"; the criticized phrase is absent. | `paper/corrected/paper.tex` | PASS |
| D2.12 | MXFP4 is explained repeatedly. | The corrected source has one representation subsection, one implementation contract, and result interpretation without repeatedly redefining the format. | `paper/corrected/paper.tex` | PASS |
| D2.13 | Reference [4] lacks venue/publisher metadata. | The 2026-08-03 primary-source audit still finds Gupta et al. only as an arXiv preprint. The bibliography explicitly labels that status and supplies authors, title, version, date, class, and DOI rather than inventing a venue. | `paper/corrected/paper.tex`; `docs/evidence/citation_archival_audit_2026_08_03_v3.csv` | PASS |
| D2.14 | Too many references are arXiv-only. | Archival versions replace preprints wherever one was verified. Of 16 entries, seven are archival papers, one is a standard, three are pinned artifacts, and five remain explicitly labeled arXiv preprints with no archival venue metadata on their primary records as of 2026-08-03. | `paper/corrected/paper.tex`; `docs/evidence/citation_archival_audit_2026_08_03_v3.csv`; `docs/evidence/citation_archival_audit_2026_08_03_v3.md`; `tests/test_citation_archival_audit.py` | PASS |

## Reviewer 3

| ID | Concern | Current response and boundary | Primary evidence | Status |
|---|---|---|---|---|
| D3.1 | Explain which applications or model sizes fit on chip. | The corrected 36-layer recurrence-state candidate physically fits out of context at 624/960 URAMs. The paper separately states that shell integration, weights, convolution state, attention KV cache, and complete-model residency are not established. | `paper/corrected/paper.tex`; `reports/vivado/corrected/e2m0/e2m0_postroute_summary.json` | PASS |
| D3.2 | Add a memory/performance/accuracy trade-off graph. | A generated three-panel figure juxtaposes logical storage, token-8192 synthetic cosine, and matched HLS STEP cost. Missing HLS and physical points are marked not run, so it is explicitly not presented as a complete Pareto frontier. | `paper/figures/corrected/tradeoff_evidence.pdf`; `paper/figures/corrected/tradeoff_evidence_manifest.json` | PASS |
| D3.3 | Quantify four-bit accuracy loss. | Output cosine and recurrent-state relative L2 are reported at five token lengths for floating Q/DQ and native encoded MXFP4 against FP32, with BF16, MXFP8-state, and INT4 comparators. | `paper/corrected/tables/long_sequence.tex`; `paper/figures/corrected/long_sequence_stability_panel.pdf` | PASS |
| D3.4 | Provide an energy-efficiency breakdown. | Vivado vectorless power is broken down by clocks, logic, signals, BRAM, URAM, and DSP, but service-level board energy requires an attached U55C, XRT platform, xclbin, and telemetry. The hardware audit finds none on this host, so the paper makes no energy-efficiency claim. | `reports/vivado/corrected/e2m0/e2m0_postroute_summary.json`; `reports/environment/hardware_availability.json`; `paper/corrected/paper.tex` | BLOCKED_EXTERNAL |
| D3.5 | Attribute energy gains to precision reduction. | There is no measured energy gain to attribute. The controlled 36-layer BF16 physical attempt also fails capacity before placement, so no matched routed energy attribution can be constructed without changing the state layout. | `reports/vivado/baselines/bf16/bf16_vivado_summary.json`; `reports/environment/hardware_availability.json` | BLOCKED_EXTERNAL |
| D3.6 | Report the accuracy cost paired with energy improvement. | Synthetic and short real-input accuracy costs are reported, but no energy improvement is claimed. Pairing them with measured energy requires the externally blocked board experiment. | `paper/corrected/paper.tex`; `reports/benchmark/qwen_recurrent_stability_manifest.json`; `reports/environment/hardware_availability.json` | BLOCKED_EXTERNAL |
| D3.7 | Clarify whether comparisons use full-size/high-precision datapaths. | The controlled HLS table fixes device, dimensions, state layout, pipeline, parallelism, and block size; BF16 uses BF16 state/operands with FP32 reductions, native MXFP4 uses E2M1/E8M0, and native MXFP8 uses E4M3/E8M0. The controlled all-layer BF16 physical attempt is reported as a capacity failure rather than replaced by a smaller design. | `paper/corrected/paper.tex`; `reports/benchmark/corrected/hls_arithmetic_comparison.json`; `reports/vivado/baselines/bf16/bf16_vivado_summary.json` | PASS |
| D3.8 | Compare with a modern four-bit GPU or explain why unavailable. | The hardware audit detects only an RTX 3070 (compute capability 8.6), not a native-FP4 GPU. A synchronized same-boundary Blackwell-class comparison therefore cannot run on this host, and the paper makes no GPU speed or energy claim. | `reports/environment/hardware_availability.json`; `paper/corrected/paper.tex`; `docs/experimental_protocol.md` | BLOCKED_EXTERNAL |

## Decision Summary

The reviews' novelty, explanation, figure, quantization-contract, reference,
synthetic-stability, and source-level scalability concerns are now directly
addressed. Matched native MXFP8 HLS/post-route evidence and short model-derived
recurrence traces are now complete. Closed-loop real-model quality, board parity and energy, and
a same-boundary native-FP4 GPU comparison remain externally blocked and are
retained as explicit limitations. Corrected all-layer out-of-context
physical fit and routed timing/DRC are reported, but complete-model residency
and corrected-candidate 64-token RTL parity are not established. The completed
HLS and routed evidence shows that the
selected stability mitigation is not Pareto-superior to BF16. All
release-required traceability and PDF-audit gates now pass, so the scoped
negative-result manuscript is **READY FOR HUMAN SUBMISSION REVIEW**.

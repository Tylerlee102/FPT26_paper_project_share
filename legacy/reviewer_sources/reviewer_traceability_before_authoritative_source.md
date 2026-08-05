# Reviewer Traceability

## Source Availability

| Reviewer | Concern | Required action | Evidence path | Paper section | Status |
|---|---|---|---|---|---|
| Authoritative reviewer attachment | The directive names attachment `63cd9dfa-cbf1-43b5-bb3b-43baf511092d`, but it is absent from the available attachment store. | Obtain the exact file, hash it, transcribe one row per comment, and reconcile it against the local sheet below. | `docs/evidence/g0_g1_local_dependency_recheck.txt`; expected external attachment not present | All | BLOCKED_EXTERNAL |

The only recoverable comment source is
`paper/comment_fix_review_2026_06_18.txt` (SHA256
`120967346A69BBFEE422132C952EA824733E69C5694409D909FE5AC0FF6FA6BC`).
It records 67 comments derived from `overleaf-comments-2026-06-18.xlsx`.
These rows preserve that evidence, but they are not asserted to be identical to
the unavailable authoritative attachment. Because the final paper has not been
rewritten, even comments marked "skip" or "keep" in the local sheet remain
`NOT_RUN` for final-paper verification.

## Recoverable 67-Comment Ledger

| Reviewer | Concern | Required action | Evidence path | Paper section | Status |
|---|---|---|---|---|---|
| Legacy-01 | Tokens are not equivalent to natural-language words. | Define tokenizer units accurately and verify final wording. | `paper/comment_fix_review_2026_06_18.txt:8` | Introduction | NOT_RUN |
| Legacy-02 | MAC is undefined. | Expand multiply-accumulate at first use. | `paper/comment_fix_review_2026_06_18.txt:15` | Introduction | NOT_RUN |
| Legacy-03 | Introduction contains excessive related-work and format detail. | Retain problem, motivation, and contribution; move technical background. | `paper/comment_fix_review_2026_06_18.txt:24` | Introduction | NOT_RUN |
| Legacy-04 | Broader implication of quadratic versus linear scaling is unclear. | Explain context-length effect without overstating whole-model behavior. | `paper/comment_fix_review_2026_06_18.txt:33` | Introduction | NOT_RUN |
| Legacy-05 | Informal phrase "a lot" is imprecise. | Replace with a scoped prior-work statement. | `paper/comment_fix_review_2026_06_18.txt:44` | Introduction | NOT_RUN |
| Legacy-06 | Main contribution is hidden. | State the narrow arithmetic/stability question at the recurrence-core boundary. | `paper/comment_fix_review_2026_06_18.txt:52` | Introduction | NOT_RUN |
| Legacy-07 | Citation is mixed with a statement of this work. | Separate prior-work motivation from current implementation. | `paper/comment_fix_review_2026_06_18.txt:60` | Introduction | NOT_RUN |
| Legacy-08 | Passive wording "can be done" is weak. | Use an active, evidence-supported design statement. | `paper/comment_fix_review_2026_06_18.txt:68` | Introduction | NOT_RUN |
| Legacy-09 | "Make a better case" is awkward. | State the concrete storage consequence. | `paper/comment_fix_review_2026_06_18.txt:75` | Introduction | NOT_RUN |
| Legacy-10 | OCP is undefined. | Expand Open Compute Project at first use. | `paper/comment_fix_review_2026_06_18.txt:82` | Background | NOT_RUN |
| Legacy-11 | MXFP4 is not clearly defined. | Define E2M1 elements, E8M0 scale, and B32 metadata overhead. | `paper/comment_fix_review_2026_06_18.txt:87` | Numerical Method | NOT_RUN |
| Legacy-12 | E2M1 is undefined. | Define sign, exponent, mantissa, finite values, and exceptional behavior. | `paper/comment_fix_review_2026_06_18.txt:93` | Numerical Method | NOT_RUN |
| Legacy-13 | E8M0 is undefined. | Define exponent-only block scale and invalid encoding policy. | `paper/comment_fix_review_2026_06_18.txt:98` | Numerical Method | NOT_RUN |
| Legacy-14 | Future tense describes an implemented action. | Use present or past tense only for passed evidence. | `paper/comment_fix_review_2026_06_18.txt:103` | Architecture | NOT_RUN |
| Legacy-15 | "To recap" repeats prior material. | Remove recap and state the objective once. | `paper/comment_fix_review_2026_06_18.txt:110` | Introduction | NOT_RUN |
| Legacy-16 | Introduction contains repeated fluff. | Keep one motivation, one format definition, and one contribution paragraph. | `paper/comment_fix_review_2026_06_18.txt:117` | Introduction | NOT_RUN |
| Legacy-17 | LUT is undefined. | Expand lookup table at first use and scope the LUT-based claim to element multiply. | `paper/comment_fix_review_2026_06_18.txt:124` | Introduction | NOT_RUN |
| Legacy-18 | FPGA is defined too late. | Expand field-programmable gate array at first use. | `paper/comment_fix_review_2026_06_18.txt:131` | Introduction | NOT_RUN |
| Legacy-19 | Preserve a strong introduction ending. | End with the supported arithmetic/stability question, not broad novelty. | `paper/comment_fix_review_2026_06_18.txt:139` | Introduction | NOT_RUN |
| Legacy-20 | Related Work repeats a citation sentence. | Verify duplicate is absent in the final source. | `paper/comment_fix_review_2026_06_18.txt:148` | Related Work | NOT_RUN |
| Legacy-21 | FPGA definition should move earlier. | Define once in the introduction and use the acronym thereafter. | `paper/comment_fix_review_2026_06_18.txt:153` | Introduction | NOT_RUN |
| Legacy-22 | Related Work uses indirect wording. | State that the numeric datapath, not persistent dataflow, is under study. | `paper/comment_fix_review_2026_06_18.txt:159` | Related Work | NOT_RUN |
| Legacy-23 | "This research" is vague. | Name the proposed design or experiment directly. | `paper/comment_fix_review_2026_06_18.txt:166` | Related Work | NOT_RUN |
| Legacy-24 | LLM is defined repeatedly. | Define large language model once. | `paper/comment_fix_review_2026_06_18.txt:171` | Introduction | NOT_RUN |
| Legacy-25 | Reduced-precision cost claim needs a citation. | Cite the OCP format source and separate representation facts from measured hardware effects. | `paper/comment_fix_review_2026_06_18.txt:177` | Background | NOT_RUN |
| Legacy-26 | Fixed low-bit dynamic-range limitation needs a citation. | Cite primary format literature and explain shared-scale tradeoffs. | `paper/comment_fix_review_2026_06_18.txt:185` | Background | NOT_RUN |
| Legacy-27 | Problem formulation is too brief. | Explain why the recurrence-core boundary isolates the research question. | `paper/comment_fix_review_2026_06_18.txt:193` | Problem Formulation | NOT_RUN |
| Legacy-28 | Alternatives are not discussed. | Describe excluded boundaries and why they would confound the comparison. | `paper/comment_fix_review_2026_06_18.txt:201` | Problem Formulation | NOT_RUN |
| Legacy-29 | Figure is too small and has excess whitespace. | Redesign and visually inspect a legible two-column datapath figure. | `paper/comment_fix_review_2026_06_18.txt:208` | Architecture | NOT_RUN |
| Legacy-30 | Architecture shape lacks rationale. | Explain the matched persistent-state baseline and native arithmetic objective. | `paper/comment_fix_review_2026_06_18.txt:215` | Architecture | NOT_RUN |
| Legacy-31 | Memory-wall citations are unexplained. | Tie each citation to a specific serving or bandwidth result. | `paper/comment_fix_review_2026_06_18.txt:222` | Background | NOT_RUN |
| Legacy-32 | Storage table is not referenced. | Reference it in prose after regenerating it from valid evidence. | `paper/comment_fix_review_2026_06_18.txt:229` | Architecture | NOT_RUN |
| Legacy-33 | Block-scale metadata is unexplained. | State one E8M0 byte per B32 and resulting 4.25 bits/value. | `paper/comment_fix_review_2026_06_18.txt:235` | Numerical Method | NOT_RUN |
| Legacy-34 | Own design statement carries an unrelated citation. | Attribute persistent placement to prior work, then state modifications separately. | `paper/comment_fix_review_2026_06_18.txt:241` | Architecture | NOT_RUN |
| Legacy-35 | Recurrent-state paragraph is repetitive. | Replace with one precise banking/layout description. | `paper/comment_fix_review_2026_06_18.txt:248` | Architecture | NOT_RUN |
| Legacy-36 | BF16/FP32 storage table is not referenced. | Reference regenerated physical and logical storage results. | `paper/comment_fix_review_2026_06_18.txt:255` | Architecture | NOT_RUN |
| Legacy-37 | Gated DeltaNet equations were viewed positively. | Retain only after replacing them with the exact official alpha-decayed recurrence. | `paper/comment_fix_review_2026_06_18.txt:262` | Method | NOT_RUN |
| Legacy-38 | Arithmetic-format table is not referenced. | Reference a regenerated table tied to the numerical contract. | `paper/comment_fix_review_2026_06_18.txt:267` | Numerical Method | NOT_RUN |
| Legacy-39 | Pipeline explanation repeats prose and lacks a naive comparison. | Attribute the five-stage baseline and use one diagram/table without repetition. | `paper/comment_fix_review_2026_06_18.txt:272` | Architecture | NOT_RUN |
| Legacy-40 | Quantization boundary is unclear. | Distinguish synthetic diagnostics from closed-loop model quality. | `paper/comment_fix_review_2026_06_18.txt:279` | Evaluation | NOT_RUN |
| Legacy-41 | Multiply path needs a precise explanation. | Describe encoded product, alignment, rounding, and saturation from the contract. | `paper/comment_fix_review_2026_06_18.txt:286` | Numerical Method | NOT_RUN |
| Legacy-42 | Two E2M1/LUT subsections repeat each other. | Merge into one arithmetic subsection. | `paper/comment_fix_review_2026_06_18.txt:293` | Numerical Method | NOT_RUN |
| Legacy-43 | Design Parameters subsection is too small. | Fold B, P_K, and P_V into architecture/evaluation setup. | `paper/comment_fix_review_2026_06_18.txt:299` | Architecture | NOT_RUN |
| Legacy-44 | AMD/Xilinx naming is inconsistent. | Use a single historically and technically accurate device/tool naming convention. | `paper/comment_fix_review_2026_06_18.txt:306` | All | NOT_RUN |
| Legacy-45 | HLS design choices are absent. | Report actual directives and their verified effect after correction. | `paper/comment_fix_review_2026_06_18.txt:313` | Implementation | NOT_RUN |
| Legacy-46 | HLS pragmas are misplaced. | Put implementation directives in the implementation/evaluation flow. | `paper/comment_fix_review_2026_06_18.txt:320` | Implementation | NOT_RUN |
| Legacy-47 | Power basis is unclear. | Separate Vivado estimate from integrated board energy and report static/dynamic breakdown. | `paper/comment_fix_review_2026_06_18.txt:327` | Evaluation | NOT_RUN |
| Legacy-48 | Simulation-only work targets only one FPGA. | State why U55C is the target and scope portability as untested. | `paper/comment_fix_review_2026_06_18.txt:334` | Evaluation/Limitations | NOT_RUN |
| Legacy-49 | Artifact release policy is unspecified. | Obtain an author decision consistent with anonymity and venue policy. | `paper/comment_fix_review_2026_06_18.txt:341` | Reproducibility | BLOCKED_EXTERNAL |
| Legacy-50 | Latency table is not referenced. | Reference only a corrected matched-boundary latency table. | `paper/comment_fix_review_2026_06_18.txt:351` | Results | NOT_RUN |
| Legacy-51 | Results prose repeats the latency table. | Interpret causes and uncertainty without duplicating cells. | `paper/comment_fix_review_2026_06_18.txt:357` | Results | NOT_RUN |
| Legacy-52 | Results prose repeats the resource table. | Discuss only the important tradeoffs and caveats. | `paper/comment_fix_review_2026_06_18.txt:364` | Results | NOT_RUN |
| Legacy-53 | Resource table is not referenced. | Reference regenerated post-route physical resource data. | `paper/comment_fix_review_2026_06_18.txt:371` | Results | NOT_RUN |
| Legacy-54 | Activation-capture caveat belongs in limitations. | Keep offline-capture limits separate from actual results. | `paper/comment_fix_review_2026_06_18.txt:378` | Limitations | NOT_RUN |
| Legacy-55 | Accuracy table is not referenced. | Reference only validated synthetic and closed-loop quality tables. | `paper/comment_fix_review_2026_06_18.txt:385` | Results | NOT_RUN |
| Legacy-56 | Own generated results carry unnecessary citations. | Cite methods/background, not locally generated numeric values. | `paper/comment_fix_review_2026_06_18.txt:391` | Results | NOT_RUN |
| Legacy-57 | Recurrent-state stress table is not referenced. | Reference regenerated 64-8192 token results with uncertainty. | `paper/comment_fix_review_2026_06_18.txt:397` | Results | NOT_RUN |
| Legacy-58 | Stress-test interpretation is unclear. | Explain observed drift and fallback tradeoff without universal claims. | `paper/comment_fix_review_2026_06_18.txt:403` | Results | NOT_RUN |
| Legacy-59 | Storage/traffic table is not referenced. | Reference matched physical storage and measured traffic. | `paper/comment_fix_review_2026_06_18.txt:411` | Results | NOT_RUN |
| Legacy-60 | HBM is undefined. | Expand high-bandwidth memory at first use. | `paper/comment_fix_review_2026_06_18.txt:416` | Limitations | NOT_RUN |
| Legacy-61 | Tiling/buffer hierarchy belongs in future work. | Keep unimplemented hierarchy experiments out of results. | `paper/comment_fix_review_2026_06_18.txt:421` | Future Work | NOT_RUN |
| Legacy-62 | Return of DRAM pressure is unbounded. | State which state, batch, beam, and cache growth exceeds physical allocation. | `paper/comment_fix_review_2026_06_18.txt:429` | Scalability | NOT_RUN |
| Legacy-63 | Larger parallelism values need results. | Regenerate the sweep for the corrected design before reporting it. | `paper/comment_fix_review_2026_06_18.txt:436` | Results | NOT_RUN |
| Legacy-64 | DSP/binding claim is too broad. | Claim LUT mapping only for proven FP4 element multiply and report all DSP use. | `paper/comment_fix_review_2026_06_18.txt:445` | Implementation | NOT_RUN |
| Legacy-65 | Future Work is too long. | Keep a short list of genuinely unexecuted extensions. | `paper/comment_fix_review_2026_06_18.txt:454` | Future Work | NOT_RUN |
| Legacy-66 | Terminology is globally inconsistent. | Standardize "recurrent state" and hyphenate only compound adjectives. | `paper/comment_fix_review_2026_06_18.txt:467` | All | NOT_RUN |
| Legacy-67 | IEEE citation numbering does not follow first use. | Use a validated bibliography and first-use order. | `paper/comment_fix_review_2026_06_18.txt:475` | References | NOT_RUN |

## Gated Remediation Concerns

These rows capture explicit concerns in the current remediation directive that
are not safely reducible to prose edits.

| Reviewer | Concern | Required action | Evidence path | Paper section | Status |
|---|---|---|---|---|---|
| Directive-01 | Legacy work claims credit for persistent state and five stages. | Classify both as inherited from Gupta et al. | `docs/prior_art_matrix.md` | Introduction/Related Work | PASS |
| Directive-02 | The recurrence omits alpha decay and official ordering. | Implement and verify the pinned recurrence. | `golden/gdn_fp32.py`, `golden/gdn_oracle_fp64.py`, `hls/src/gdn_top.cpp` | Method | FAIL |
| Directive-03 | State orientation and paired-head mapping are wrong or undocumented. | Use logical K-by-V and test explicit transpose conversions. | `docs/numerical_contract.md`, `docs/evidence/g1_g2_software_pytest.xml` | Method/Implementation | PASS |
| Directive-04 | Output uses an incorrect elementwise gate. | Freeze the core before gated RMSNorm and remove the gate from HLS. | `hls/src/gdn_top.cpp` | Method | FAIL |
| Directive-05 | No independent FP64 and official recurrence/chunk references. | Build three distinct reference levels and parity tests. | `golden/gdn_oracle_fp64.py`, `docs/experimental_protocol.md` | Evaluation | NOT_RUN |
| Directive-06 | MX reference is not encoded-integer or independent. | Implement every quantization/alignment/state-write boundary independently. | `golden/gdn_mxfp4_encoded.py`, `tests/test_gdn_mxfp4_encoded.py` | Numerical Method | PASS |
| Directive-07 | Active HLS ignores block scales/alignment. | Wire activation/state scales and block alignment into the corrected datapath. | `hls/src/gdn_top.cpp`, `hls/src/block_exp_align.cpp` | Implementation | FAIL |
| Directive-08 | Beta encoding can exceed one and alpha is absent. | Implement validated Q1.15 alpha/beta with exact endpoints. | `hls/src/phase3_update.cpp`, `docs/numerical_contract.md` | Numerical Method | FAIL |
| Directive-09 | Resident state lacks reset/load/readback and runtime identity. | Implement atomic controls with sequence/layer isolation. | `docs/numerical_contract.md` | Implementation | FAIL |
| Directive-10 | Tests can pass while computation is wrong. | Add independent random, adversarial, multi-token, all-layer, and state-control tests. | `tests/`, `docs/evidence/g1_g2_software_pytest.xml`, `docs/experimental_protocol.md` | Evaluation | FAIL |
| Directive-11 | Real activation hooks are open loop. | Replace all GDN recurrence cores in cache-faithful closed-loop decode. | `scripts/qwen_capture.py` | Evaluation | BLOCKED_EXTERNAL |
| Directive-12 | FP8 baseline is missing. | Implement matched MXFP8-E4M3-B32 state/compute baseline. | `docs/experimental_protocol.md` | Evaluation | NOT_RUN |
| Directive-13 | Long-horizon stability is unsupported. | Run frozen 64-8192 token synthetic and real closed-loop traces. | `reports/benchmark/corrected/long_trace_checkpoints.csv`, `reports/benchmark/corrected/scale_policy_checkpoints.csv`, `docs/experimental_protocol.md` | Results | BLOCKED_EXTERNAL |
| Directive-14 | Candidate lazy log may overlap prior art. | Prove equivalence and obtain human approval of a precise gap before HLS. | `docs/prior_art_matrix.md` | Related Work/Method | NOT_RUN |
| Directive-15 | Existing model-wide fit claims use logical bytes only. | Allocate all 36 layers and report padded/banked/replicated physical primitives. | `docs/experimental_protocol.md` | Hardware Results | FAIL |
| Directive-16 | No timing DRC, bitstream, XRT, or board parity exists. | Complete physical build and exact board comparison after approval. | `reports/vivado/` | Hardware Results | BLOCKED_EXTERNAL |
| Directive-17 | Vivado power times simulated latency is called energy. | Label legacy value estimated and integrate physical telemetry for measured energy. | `paper/numbers.json`, `docs/experimental_protocol.md` | Results | FAIL |
| Directive-18 | H100 comparison derives energy from TDP. | Remove it unless rerun at the same boundary with telemetry and synchronization. | `paper/numbers.json` | Results | FAIL |
| Directive-19 | Application and scalability boundary is overstated. | Account separately for convolution state, attention KV, weights, activations, and traffic. | `docs/experimental_protocol.md` | Limitations | FAIL |
| Directive-20 | Quality claims rely on synthetic/open-loop data. | Report synthetic results as diagnostic and require closed-loop perplexity with confidence intervals. | `scripts/qwen_capture.py` | Results/Limitations | FAIL |
| Directive-21 | Datapath figure does not expose widths, rates, scales, and legend. | Redraw only after the corrected datapath is frozen and visually audit it. | `paper/figures/` | Architecture | NOT_RUN |
| Directive-22 | Component ownership is not explicit. | Include inherited/corrected/modified/new classification. | `docs/prior_art_matrix.md` | Related Work | PASS |
| Directive-23 | Reference [4] lacks complete archival metadata. | Verify authors, title, venue/publisher/DOI or clearly label arXiv status. | `docs/prior_art_matrix.md` | References | NOT_RUN |
| Directive-24 | Archival references should replace arXiv when available. | Recheck every citation at G7 and record the source revision. | `docs/prior_art_matrix.md` | References | NOT_RUN |
| Directive-25 | Final paper numbers and figures are not valid for the corrected design. | Regenerate from evidence only, render, and inspect every page. | `docs/implementation_status.md` | All | NOT_RUN |

## Closure Rule

This ledger can be `PASS` only after the authoritative attachment is present,
every source comment has exactly one reconciled row, each required action has
raw evidence, and the rendered final PDF has been checked against every row.
Current reviewer-traceability status is **BLOCKED_EXTERNAL**.

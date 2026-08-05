# Numeric Validity Audit

Date: 2026-06-25

Scope audited: benchmark extraction, generated paper numbers/provenance, report
generators, README/known-issues text, and current generated paper artifacts. The
canonical source remains `paper/numbers.json`; generated paper tables, snippets,
and figures were regenerated from it after the fixes below.

## 1. Mixed On-Chip Energy With Board/TDP Baselines

Severity: high

Locations:

- `scripts/benchmark.py:281` computes the new board/TDP energy basis.
- `scripts/benchmark.py:509` writes `ours_mxfp4_b32_energy_mj` as board/TDP energy.
- `scripts/benchmark.py:612` keeps the old on-chip comparison as diagnostic only.
- `reports/vivado/impl_power.rpt:33` is the Vivado on-chip power source.
- `reports/vivado/impl_power.rpt:43` and `reports/vivado/impl_power.rpt:45` show medium confidence and no simulation activity file.
- `paper/numbers.json:188` now stores the corrected H100 headline energy-efficiency ratio.

Plain-language explanation:

The old headline energy-efficiency result compared this design's Vivado
estimated on-chip energy against H100/USC baseline energies that are reported on
a board/TDP basis. Those are not the same denominator. This made the headline
energy-efficiency claim look about 12.8x stronger than a denominator-matched
comparison.

Fix applied:

- Added an explicit `u55c_board_tdp_power_w` canonical number using AMD's Alveo
  U55C product brief value, `Power (TDP) 115W`.
- Split FPGA energy into two named records:
  `ours_mxfp4_b32_onchip_energy_mj` for Vivado on-chip diagnostics and
  `ours_mxfp4_b32_board_tdp_energy_mj` for headline comparisons.
- Changed `ours_mxfp4_b32_energy_mj` to the board/TDP-conditioned value.
- Kept the old ratio only under
  `diagnostic_onchip_energy_efficiency_vs_h100_tdp`, with notes that it is not
  denominator-matched.
- Updated generated tables, snippets, IEEE assets, example report, benchmark
  notes, and tests.

Before/after:

| Quantity | Before | After |
|---|---:|---:|
| FPGA energy used for headline | 0.462 mJ/token on-chip | 5.919 mJ/token board/TDP |
| H100 energy-efficiency headline | 216.011x | 16.86x |
| USC energy-efficiency headline | 20.562x | 1.605x |
| Diagnostic on-chip-vs-H100 ratio | reported as headline | retained as diagnostic, 216.011x |

Source note: AMD U55C TDP comes from the official AMD product brief:
https://www.amd.com/content/dam/amd/en/documents/products/accelerators/alveo/u55c/alveo-u55c-product-brief.pdf

Regression guard:

- `tests/test_paper_provenance.py:114` verifies the board/TDP energy basis and
  checks that the headline ratio is lower than the diagnostic on-chip ratio.

## 2. Qwen Capture Status Was Conflated With Model-Quality Evidence

Severity: medium

Locations:

- `scripts/qwen_status.py:67` reports valid captures as `available`.
- `scripts/qwen_status.py:77` explains that the activation capture is present.
- `scripts/qwen_status.py:78` explicitly says this is not PPL/model-quality evidence.
- `scripts/benchmark.py:701` records the same caveat in `paper/numbers.json`.
- `README.md:7` and `README.md:83` separate capture availability from model-quality claims.
- `reports/known_issues.md:15` keeps Qwen-derived accuracy/PPL extraction open.

Plain-language explanation:

The repository had a real checked-in Qwen3-Next activation capture artifact, but
the status report still described the path as dependency-blocked. At the same
time, treating capture availability as model-quality validation would also be
too strong. The correct state is: the capture exists, but Qwen-derived
accuracy/PPL metrics have not been generated.

Fix applied:

- Regenerated `reports/golden/qwen_capture_status.md` as `Status: available`.
- Updated the status script so missing `torch`/`transformers`/`datasets` is a
  recapture limitation, not proof that the checked-in capture is unavailable.
- Updated `paper/numbers.json`, `paper/example_report.md`, README, and known
  issues to state that generated accuracy metrics remain synthetic-only until a
  separate Qwen-derived extraction report exists.

Before/after:

| Quantity | Before | After |
|---|---|---|
| `qwen_capture_status` | `dependency_blocked` | `available` |
| Qwen PPL/model-quality claim | ambiguous risk | no PPL/model-quality claim; synthetic-only accuracy caveat remains |

## 3. Some Generated Assets Could Bypass Canonical Numbers

Severity: medium

Locations:

- `scripts/benchmark.py:571` creates `design_sweep_rows` in `paper/numbers.json`.
- `scripts/paper_figures.py:37` reads sweep rows from `paper/numbers.json`.
- `scripts/paper_graph_previews.py:57` reads sweep rows from `paper/numbers.json`.
- `scripts/paper_table_previews.py:70` reads sweep rows from `paper/numbers.json`.
- `scripts/ieee_assets.py:316` reads sweep rows from `paper/numbers.json`.
- `scripts/example_report.py:21` reads sweep rows from `paper/numbers.json`.
- `tests/test_paper_provenance.py:147` checks the canonical sweep-row path.

Plain-language explanation:

The paper pipeline rule says generated figures under `paper/figures` must read
from `paper/numbers.json`. The Pareto figure path and several preview/IEEE
helpers could previously read `reports/benchmark/sweep.csv` directly or use
stale fallback constants. That meant two generated artifacts could disagree even
when `paper/numbers.json` was correct.

Fix applied:

- Added `design_sweep_rows` as a structured, provenance-tracked copy of the
  sweep table inside `paper/numbers.json`.
- Removed direct sweep-CSV fallback paths from the generated paper/preview/IEEE
  report scripts.
- Regenerated paper figures, previews, IEEE assets, tables, snippets, and the
  example report.

Before/after:

| Quantity | Before | After |
|---|---:|---:|
| Canonical sweep rows in `numbers.json` | absent | 5 rows |
| Generated paper figure sweep source | direct CSV path | `design_sweep_rows` |
| Preview/IEEE fallback constants | possible | removed |

## 4. Legacy Manuscript Drafts Still Contain Hand-Typed Pre-Audit Numbers

Severity: low

Locations:

- `paper/overleaf_ready_mxfp4_gdn.tex:410`
- `paper/ieee_template_smaller_graphs.tex:49`
- `paper/overleaf_ready_from_original_tables.tex:410`
- `paper/overleaf_comments_fixed_2026_06_18.tex:35`
- `reports/known_issues.md:32`

Plain-language explanation:

Several old manuscript draft files still contain hand-typed versions of the
pre-audit 216.011x energy-efficiency claim. They are not the generated
canonical paper artifacts, but they are risky if copied into a submission.

Fix applied:

- Regenerated the canonical assets that should be used for current numbers:
  `paper/numbers.json`, `paper/snippets/`, `paper/tables/`, `paper/figures/`,
  `paper/ieee_tables/`, and `paper/example_report.md`.
- Added a known-issues warning that legacy drafts must be replaced with
  generated macros/tables before submission.

Before/after:

| Quantity | Before | After |
|---|---|---|
| Legacy draft prose | old hand-typed 216.011x claim present | explicitly marked non-canonical in known issues |
| Canonical generated headline | 216.011x | 16.86x |

## Checklist Items With No Material Finding

- Unexplained headline-driving defaults: the material energy default introduced
  by this audit is cited from the AMD U55C TDP. Existing headline hardware
  defaults are AGENTS-specified device/kernel constants or covered by the Phase
  6 sweep.
- Independence/correlation assumptions: no probabilistic protection or
  reliability model drives a headline number in the audited pipeline.
- Aggregation drops/double-counting: stress and drift aggregations use equal
  per-group vector counts, and Phase 6 sweep extraction now preserves all five
  current rows with cosim and post-implementation evidence.
- Circular validation: no headline hardware number is validated solely against
  itself; extracted numbers come from checked-in cosim, HLS, Vivado, and
  generated benchmark reports.

## Regenerated And Verified

Commands rerun with the bundled Python runtime:

- `python -m scripts.qwen_status`
- `python -m scripts.benchmark`
- `python -m scripts.paper_tables`
- `python -m scripts.paper_figures`
- `python -m scripts.paper_table_previews`
- `python -m scripts.paper_graph_previews`
- `python -m scripts.ieee_assets`
- `python -m scripts.example_report`
- `python -m scripts.paper_pack`
- `python -m scripts.validate_paper_pack`
- `python -m unittest discover -s tests`

Verification results:

- Unit tests: 51 tests passed.
- Paper pack validation: `reports/phase7_validation.md:5` reports `Overall status: PASS`.
- Canonical count: `reports/phase7_validation.md:23` reports 104 numbers and 104 provenance records.
- Current pack: `paper/pack/submission_bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe.zip`.

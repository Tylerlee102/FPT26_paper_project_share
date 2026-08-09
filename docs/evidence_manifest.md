# Evidence Manifest

> **Historical manifest with a current-status overlay.** The detailed entries
> below preserve the evidence sequence through earlier correction milestones;
> some intermediate candidate labels are intentionally historical. Current
> release status is controlled by `reports/final_completion_gate.json`, current
> candidate selection by
> `reports/benchmark/corrected/rs2_encoded_candidate_preregistration.json`, and
> manuscript numbers by `paper/corrected/numbers.json` plus
> `paper/corrected/provenance.json`. No earlier `selected` label overrides those
> files.

Current candidate (2026-08-06):
`mxfp4_rs2_act_rs2_state_mxfp4rs2_log_r3_q1_15_int32_guard5` (RS2/R3).
Its held-out and extended synthetic gates, exact HLS C simulation, matched HLS
reports, and all-layer out-of-context routes are recorded under the current
`reports/*/corrected/rs2_*` trees. The completion gate remains authoritative
for every nonpassing or externally blocked release requirement.

Current local tool status is recorded in
`reports/environment/hardware_availability.json`: Vitis HLS, Vivado, `v++`,
`platforminfo`, and XSim are available. The installed platform inventory has no
U55C XPFM, Windows and WSL have no `xbutil` or `xrt-smi`, and no PCI vendor
`0x10ee` device is present. Thus synthesis, routing, C simulation, and RTL
simulation are local capabilities; U55C execution and telemetry are not.

Manifest version: `0.9`

Audit host date/time zone: `2026-08-03`, America/Los_Angeles.

Source revision:
`bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`

Preserved source dirty-patch SHA256:
`C2278346E698A0F2E8095888E54795F3AED8D838B750CCA0C36152B058972E1E`

Corrected G1/G2 software source-patch SHA256:
`B0AD3C5AA073C277C0EDDF14B4E18B50430F7959BCE14ADCC9CBF2E8EA7FDC45`

Corrected evidence hash list: `docs/evidence/g1_g2_sha256.txt`, SHA256
`AE408B3D8336EBF3B16C051295DFB160C9DA6CE16CAE92CD17954A0B962475DD`.

Reviewer-source reconciliation patch SHA256:
`01C201AB71A70CAE174F0850B7055ABC21026125B05A16FF57D35D553B65D185`.

Reviewer-source evidence hash list:
`docs/evidence/g0_reviewer_source_sha256.txt`, SHA256
`3FB553F282CBE971A61E305EBE1987684A1031FFB383F70F55487CED3246DA64`.

Prior-art refresh evidence hash list:
`docs/evidence/g0_prior_art_refresh_sha256.txt`, SHA256
`4F415742D137FE04CC7116DA08D619E366B08496B000EC96B257CEFAF5446E2A`.

Official recurrence-parity evidence hash list:
`docs/evidence/g1_official_parity_sha256.txt`, SHA256
`01CFD4CB13A5FB1E72747322B3FB752283A37211E48EA48ECA79836F908B3E5A`.

Resident-state command evidence hash list:
`docs/evidence/g2_resident_state_sha256.txt`, SHA256
`A70E445B41AC69546E44D27E7C5E0E9C6E57A981434449FCFFC0BBF87DA6A774`.

Current corrected source dirty-patch SHA256:
`65ABCBE91C7626E3F99083B3D1254AA5F74331DBA3A3CA7A2693C29C00C02FA4`.
The 1,864,391-byte binary patch covers 226 changed files among 254 frozen source,
test, protocol, and release-control files relative to the source revision.
Snapshot manifest:
`docs/evidence/current_corrected_source_snapshot.json`, SHA256
`08CB76CA0F9432FC54794CF17A7CAD083076A9BEF6F65160C6EC7827D914D12E`.
Snapshot command: `python -m scripts.evidence_source_snapshot`, exit code `0`,
at `2026-08-04T01:35:52.699424+00:00`.
`docs/evidence_manifest.md` is deliberately excluded from that snapshot to
avoid a self-referential hash; every other matched document source is frozen.

## Interpretation

An evidence entry is `PASS` only for the narrow requirement named in that row.
For example, the baseline pytest suite passes as a reproducibility observation,
while its adequacy for the corrected recurrence is `FAIL`. Legacy numerical and
hardware reports never inherit validity after the recurrence, boundary, or
arithmetic contract changes.

## Historical Environment Snapshot

| Item | Observed value | Status |
|---|---|---|
| Git | `2.54.0.windows.1` | PASS |
| System Python | `3.12.10` | PASS |
| Bundled artifact Python | `3.12.13` | PASS |
| NumPy in bundled runtime | `2.3.5` | PASS |
| pytest in system Python | `9.1.1` | PASS |
| Vitis HLS | `2025.2`, build `6295257`, IP build `6300035` | PASS |
| Vivado | `2025.2`, build `6299465` reported, version command returned exit 1 | FAIL |
| Local U55C `.xpfm` discovery | `platforminfo` unavailable and target platform not found | FAIL |
| Declared Python compatibility | Project says `>=3.10`; corrected source uses `datetime.timezone.utc` and no `datetime.UTC` | PASS |

## G0 Evidence Entries

### E-G0-001 - Isolated Legacy Preservation

- Status: `PASS`
- Requirement: preserve the submitted PDF, source revision, source dirty patch,
  and untracked inputs without modifying the source repository.
- Command and exit code: local `git clone --no-hardlinks`, `git rev-parse HEAD`,
  `git diff --binary`, and file-copy operations; exit code `0`.
- Source Git revision:
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`.
- Dirty-patch hash:
  `C2278346E698A0F2E8095888E54795F3AED8D838B750CCA0C36152B058972E1E`.
- Input hashes: submitted PDF
  `0EDAFE5B6943E3E89C1F50BD9BD5C609AE1A2953F4BD388EF0DC1FDF6C92B787`;
  legacy draft
  `2397FB5201C50307FEBF8B12A2929BA3F3B0B09D47578896CEA5C8EA5ABAB353`.
- Configuration/seeds: read-only copy; seeds not applicable.
- Tool versions: Git `2.54.0.windows.1`, PowerShell host.
- Raw paths: `legacy/submitted/IEEE_Conference_Template.pdf`,
  `legacy/source_snapshot/source_dirty.patch`, and
  `legacy/source_snapshot/untracked/`.
- Independent verification: SHA256 hashes recomputed in the isolated clone and
  source HEAD checked with `git rev-parse`.
- Timestamp: `2026-07-31T23:56:06.3792681-07:00`.

### E-G0-002 - Repository And Provenance Audit

- Status: `PASS`
- Requirement: inspect history, golden models, MX formats, HLS, tests, reports,
  model capture, benchmark pipeline, paper numbers, and provenance.
- Command and exit code: `git log`, `git status`, `rg`, `Get-Content`,
  `Get-FileHash`, and report-tree inspection; exit code `0`.
- Source Git revision and dirty-patch hash: manifest header.
- Input hashes:
  - `golden/gdn_fp32.py`:
    `8356EC83D6B68E89B5AB6A59E0CF24BB4F43414A541A2B9BE150182F75F6F311`
  - `golden/gdn_mxfp4.py`:
    `0848436ACE19805FB1E43C442018F713BA795520C00566A60DF8BA45C67B14CE`
  - `golden/mx_format.py`:
    `4CCEE9527E0CB2C42ABB47FD270355CDA3D046E5ACCFDAC5296835AC44D66E96`
  - `hls/src/gdn_top.cpp`:
    `B98C2934AFB269E053967B01C83AD9ACD8BA89CA9C8A7E28DC31CF245ED3B7E9`
  - `hls/src/phase3_update.cpp`:
    `AFA4645DEEAA6600A129C849CED81C5A5974BAC6FA5211A4CEB6E12DACF59A0D`
  - `hls/src/block_exp_align.cpp`:
    `F7DB025BD068BFD8C3CFC400296D316D75047C8ECE6E44828E428CAAAAA7AE13`
  - `hls/tb/tb_gdn_top.cpp`:
    `F2B0A6DC33D466A05BBC6349AA8D69277E73A178F6E36B077ED7B92273F79272`
  - `scripts/qwen_capture.py`:
    `D2BA2EA81E88D56B7E42964C240051076C71915942D7992CDF1900E4F5D582FD`
  - `scripts/benchmark.py`:
    `0212CAB2EDE90B1B61663E0AB532E9FE54060D95FE87AFF00F577D71F51AC3BB`
  - `paper/numbers.json`:
    `5720ECB5E70EDC68C3C7077C655F82D41570807F17A7C4CC1B56208CFB762A99`
  - `paper/provenance.json`:
    `5C8D8A92859EAC636BCCB1514AD79A444962F0E365A8996827920858F2DC29C0`
- Configuration/seeds: static audit; seeds not applicable.
- Tool versions: Git `2.54.0.windows.1`, PowerShell, Python `3.12.10`.
- Raw paths: the hashed source files and `reports/` tree.
- Independent verification: official pinned Transformers recurrence was read
  separately; report claims were cross-checked against active dataflow calls and
  report headers rather than provenance metadata alone.
- Timestamp: `2026-07-31T23:56:06.3792681-07:00`.

### E-G0-003 - Baseline Test Reproduction

- Status: `PASS`
- Requirement: reproduce what the legacy test suite currently reports.
- Command and exit code:

  ```powershell
  $env:PYTHONPATH='C:\Users\tyboy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages'
  python -m pytest -q --junitxml=docs/evidence/g0_baseline_pytest.xml
  ```

  Exit code `0`; 48 passed and 1 skipped.
- Source Git revision and dirty-patch hash: manifest header.
- Input hashes: `tests/test_gdn_fp32.py`
  `2B32577114B17D5BBBC329EB1CCA6B975223F12A5A5F496CDEE32DC0FA04BB8F`;
  `tests/test_cosim_parity.py`
  `8C1F3E486A51E63BDADBED47A9679C7A7714F1321966291CCDFC48CA4C0A9F8E`.
- Configuration/seeds: repository defaults; `GDN_SEED` unset, default
  `0xFB72`; bundled NumPy injected through `PYTHONPATH`.
- Tool versions: Python `3.12.10`, pytest `9.1.1`, NumPy `2.3.5`.
- Raw report: `docs/evidence/g0_baseline_pytest.xml`, SHA256
  `16BA982D60A00429F9E6F8F2F5AC7ED9B626FA41C5E5E7BA9EF5DA5EEAB64C43`.
- Independent verification: manual test-source audit showed that the tests
  validate the simplified recurrence, use loose floating tolerances/string
  checks, and do not establish independent RTL parity. Adequacy status is
  therefore `FAIL` despite reproducibility `PASS`.
- Timestamp: recorded in JUnit report.

A plain `python -m pytest -q` without the injected bundled dependency path
returned exit code `1` because NumPy was absent from the declared environment.
This is an environment-metadata failure, not a failing numerical test.

### E-G0-004 - PDF Render And Visual Audit

- Status: `PASS`
- Requirement: preserve, render, and visually inspect every page of both
  available manuscript PDFs.
- Command and exit code: Poppler PDF-to-PNG rendering through the PDF artifact
  workflow; exit code `0` for both documents.
- Source Git revision and dirty-patch hash: manifest header.
- Input hashes: submitted and legacy-draft hashes from E-G0-001.
- Configuration/seeds: original page size, one PNG per page, no randomness.
- Tool versions: Poppler runtime from the bundled PDF workflow; Python
  `3.12.13`, pypdf `6.10.0`, pdfplumber `0.11.9`.
- Raw report paths: `docs/evidence/pdf_renders/submitted-1.png` through
  `submitted-5.png`, and `legacy-draft-1.png` through `legacy-draft-8.png`;
  per-file hashes are in `docs/evidence/pdf_renders.sha256`.
- Independent verification: all 13 pages viewed individually; metadata/page
  counts independently inspected with pypdf/pdfplumber.
- Timestamp: file timestamps and manifest audit date.

Findings: the submitted PDF is five pages and remains mostly IEEE template
content with placeholder references and unsupported claims. The later draft is
eight pages and repeats invalidated recurrence, native-scale, speedup, and
energy claims.

### E-G0-005 - Official Revision Pinning

- Status: `PASS`
- Requirement: pin the requested model/software/format/device/platform inputs
  and protocol datasets.
- Command and exit code: read-only `git ls-remote <official-repository> HEAD` or
  tag queries, plus official documentation inspection; exit code `0` for Git
  queries.
- Source Git revision and dirty-patch hash: manifest header.
- Input hashes/revisions: all revisions in `docs/prior_art_matrix.md`, including
  Qwen `9c7f2f...`, Transformers tag object `76d27aea...` and peeled commit
  `8ac2b916...`, FLA `a670dff4...`,
  causal-conv1d `52949d08...`, PyTorch `ba561023...`, Triton `c817b9b6...`,
  WikiText `b08601e0...`, and PG-19 `4d28bd77...`.
- Configuration/seeds: read-only metadata queries; seeds not applicable.
- Tool versions: Git `2.54.0.windows.1`; browser source retrieval.
- Raw report: `docs/evidence/g0_revision_pins.txt`, SHA256
  `02D80DE9A5A1686BB9AB1774433C9DE742B56811DFD7970C45E5E1864203BF5E`.
- Independent verification: architectural recurrence was checked against the
  pinned Transformers source and official Qwen model card; device/platform
  names were checked against AMD DS978 and UG1120.
- Timestamp: raw report and manifest audit date.

### E-G0-006 - Prior-Art Overlap Audit

- Status: `PASS`
- Requirement: inspect primary sources in all requested prior-art categories and
  distinguish inherited components from candidate contributions.
- Command and exit code: primary-source search/open operations; successful
  retrieval for sources listed in `docs/prior_art_matrix.md`.
- Source Git revision and dirty-patch hash: manifest header.
- Input hashes: external documents are identified by stable official URL,
  version, DOI, proceedings record, or repository revision in the matrix.
- Configuration/seeds: bounded literature audit dated 2026-07-31 and refreshed
  2026-08-01; no randomness.
- Tool versions: web retrieval and Git `2.54.0.windows.1`.
- Raw reports: `docs/prior_art_matrix.md`,
  `docs/evidence/g0_prior_art_refresh_2026_08_01.md`,
  `docs/evidence/prior_art_sources_2026_08_01.csv`, and linked primary
  documents. See E-G0-010 for hashes and the bibliographic refresh protocol.
- Independent verification: overlap conclusions require a later human novelty
  review; this entry passes source collection/classification only. The broad
  novelty claim itself is `FAIL`, and the narrow gap remains `NOT_RUN`.
- Timestamp: `2026-07-31`.

### E-G0-007 - Legacy Evidence Invalidation

- Status: `PASS`
- Requirement: identify evidence invalidated by correcting recurrence or kernel
  boundary and prevent silent reuse.
- Command and exit code: cross-check active model/HLS source hashes against
  report and provenance inputs; exit code `0`.
- Source Git revision and dirty-patch hash: manifest header.
- Input hashes: E-G0-002 source/provenance hashes.
- Configuration/seeds: static dependency audit; seeds not applicable.
- Tool versions: PowerShell, Git, Python.
- Raw report: `docs/implementation_status.md`, section "Invalidated Legacy
  Evidence"; original artifacts remain under `reports/` and `paper/`.
- Independent verification: mathematical mismatch and inactive scale wiring
  were established directly from source, independent of report labels.
- Timestamp: `2026-07-31T23:56:06.3792681-07:00`.

### E-G0-008 - Attachment Store And Local Runtime Recheck

- Status: `PASS` for the bounded attachment-store/runtime recheck only.
  Authoritative reviewer ingestion subsequently passed through the separately
  recovered named workbook in E-G0-009. Official runtime parity remains
  `NOT_RUN`.
- Requirement: exhaust the local attachment store and existing Python/runtime
  caches before asserting that external input or installation is required.
- Command and exit code: `rg --files`, exact UUID/content searches,
  `Get-ChildItem -Recurse -Filter pyvenv.cfg`, Python `importlib.util.find_spec`,
  cache/source/wheel searches; successful inventory commands returned exit code
  `0`, while no-match searches returned the documented `rg` exit code `1`.
- Source Git revision:
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; corrected software source-patch
  SHA256 is the manifest header.
- Input hashes: attachment index
  `10720C6FFD6CC5CC4A47F42937D6F46C2DB9FD69167296B1329406C96F00FB67`;
  remediation directive
  `81454B5A9AA7D836835C6AE5BDEE228A2BD74A70438C739F5EBB5D81DB087B7B`.
- Configuration/seeds: 154 attachment-store files; system Python, bundled
  artifact Python, and both discovered virtual environments; seeds not
  applicable.
- Tool versions: PowerShell host, ripgrep available through the Codex shell,
  Python `3.12.10` and bundled Python `3.12.13`.
- Raw report: `docs/evidence/g0_g1_local_dependency_recheck.txt`, SHA256
  `AF17739F29F306BF6A49D475928A111DAB94B0CD23BD6A209FBC5F4BCCE1A78E`.
- Independent verification: both path/name and exact-content searches were
  used for the attachment; package availability was queried in each discovered
  interpreter and cross-checked against caches, wheel files, and the official
  source filename.
- Result: the named attachment UUID remains absent. A later whole-profile search
  found the workbook named by the local derivative review note; see E-G0-009.
  No checked Python environment contains Torch, Transformers, FLA,
  causal-conv1d, or Triton; no Hugging Face cache, official source checkout, or
  cached wheel was found. Nothing was installed or downloaded.
- Timestamp: `2026-08-01T02:07:50.3280417-07:00`.

### E-G0-009 - Authoritative Reviewer Workbook Reconciliation

- Status: `PASS` for reviewer-source ingestion and one-row-per-comment
  reconciliation. The author release-policy decision is `PASS`; final comment
  remediation remains `NOT_RUN` pending future evidence-supported PDF
  verification.
- Requirement: preserve and hash the named Overleaf comment workbook, extract
  it with a structured spreadsheet API, independently verify the extraction,
  and place exactly one row per distinct reviewer message in
  `docs/reviewer_traceability.md`.
- Commands and exit codes:

  ```powershell
  node scripts/inspect_reviewer_workbook.mjs legacy/reviewer_sources/overleaf-comments-2026-06-18.xlsx build/reviewer_workbook_inspect/repro <artifact_tool.mjs>
  python scripts/reconcile_reviewer_workbook.py --workbook legacy/reviewer_sources/overleaf-comments-2026-06-18.xlsx --artifact-json docs/evidence/reviewer_workbook_artifact_tool_values.json --legacy-ledger legacy/reviewer_sources/reviewer_traceability_before_authoritative_source.md --traceability docs/reviewer_traceability.md --evidence-dir docs/evidence
  ```

  Both commands returned exit code `0`. A second artifact-tool extraction
  reproduced the values JSON and preview PNG hashes exactly.
- Source Git revision:
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; reviewer-source dirty patch
  SHA256:
  `01C201AB71A70CAE174F0850B7055ABC21026125B05A16FF57D35D553B65D185`.
- Input hashes: workbook
  `C4A70E704BEBDC8126540B2FEEBB25A26FA3672DBE79F9AE08157E27FDA7E54E`;
  artifact-tool value matrix
  `1D0C633198BB4C69E0AB1689B721B32E76DB570D099ABFAAFEEFC4A5B5C1B6BC`;
  legacy derivative ledger snapshot
  `7BF91012089F2F6CCBD246AADE324AC79479F3F5B18DEA8B4D72F9EF5269A65A`.
- Configuration/seeds: worksheet `Comments`, range `A1:H94`; exact duplicate
  exporter rows retained; no randomness or seed.
- Tool versions: Node.js `24.14.0`, `@oai/artifact-tool` `2.8.36`, bundled
  Python `3.12.13`.
- Raw reports: `docs/evidence/reviewer_workbook_rows.csv` SHA256
  `BA970048B1C114BBEB296668F222910F9309334D964D579A72783B84E9206B3B`;
  `docs/evidence/reviewer_workbook_reconciliation.csv` SHA256
  `D7A2CE932A5809501B746C7DE140162597F24D6FDE96CBF87E51A1982A0D5EBC`;
  visual preview SHA256
  `2CD57DDAEFA3CF6BFD5CD2653E875ED0E02C453FCCA3CF4DAA1DC573074F6991`.
- Independent verification: a Python standard-library ZIP/XML parser matched
  the artifact-tool 94-by-8 semantic value matrix after canonicalizing empty
  strings to null. The 93 raw rows resolve to 72 thread/reply messages: 68 from
  reviewer `jason.blocklove` and four author messages. Twenty exact duplicate
  extra rows and one fuller same-message variant are preserved by raw row
  number. The rendered worksheet preview was visually inspected. A later CI
  check rehashes the workbook and enforces ordered R01-R68 labels, 68 unique
  thread/reply pairs, the exact status vocabulary, and the current 67
  `NOT_RUN` plus R49 `PASS` distribution. Its successful log SHA256 is
  `4B51F40BE2AA8B0A0D1AFD4B4B564E3A4C5CC3D61CF0C46231235EF3DC4A2BE4`.
- Preserved failed CI attempt: the first test incorrectly assumed that all 68
  rows were `NOT_RUN` and overlooked the already-recorded R49 author decision.
  The failed log SHA256 is
  `4432B9FDA36E8C3AAD8CC3C843D0A1EAC26E6F309412A89510D2D304CCC1909E`;
  no reviewer ledger data changed.
- Timestamp: `2026-08-01T20:33:27.0468909Z`.

### E-G0-010 - Reference [4] And Prior-Art Refresh

- Status: `PASS` for exact Reference [4] metadata resolution and bounded source
  collection/classification only. The broad legacy novelty claim remains
  `FAIL`; the exact narrow gap and lazy write-log gap remain `NOT_RUN`.
- Requirement: verify Reference [4]'s authors, title, publication status, DOI,
  and direct architectural overlap; refresh the narrow-gap search without
  treating search absence as novelty evidence.
- Command and exit code: primary-source exact-title and query-family searches,
  followed by direct arXiv, OpenReview, proceedings, DOI, and DBLP record
  inspection; all records used in the classification were retrieved
  successfully. OpenReview pages that rate-limited automated viewing retained
  their stable primary record URLs and prior verified classification.
- Source Git revision:
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`.
- Input identifiers: `arXiv:2603.05931v1`, submitted 2026-03-06; arXiv-issued
  DataCite DOI `10.48550/arXiv.2603.05931`; DBLP key
  `journals/corr/abs-2603-05931`; all other stable IDs and URLs are in the CSV.
- Configuration/seeds: four query families across arXiv, OpenReview,
  PMLR/proceedings records, DBLP, IEEE, ACM, and exact-title web indexes;
  audit date `2026-08-01`; no randomness.
- Tool versions: web search/retrieval and Git `2.54.0.windows.1`.
- Raw reports: `docs/evidence/g0_prior_art_refresh_2026_08_01.md` SHA256
  `3C656E8CFF352E1DD484A6113E85BBAFA1D27D0B30E230FC272D901F83A14D98`;
  `docs/evidence/prior_art_sources_2026_08_01.csv` SHA256
  `994ADAE9D745A9C6B02A3091A5F34DDF1C6938CB0DFC64318B5264CC9178E4CD`;
  `docs/prior_art_matrix.md` SHA256
  `76122916D8F977E9A14C0C3EAFDFDC6D34F9E0D049E5526743093C2C6D153331`.
- Independent verification: arXiv gives the exact four authors, title,
  submission date, version, subjects, preprint length, and DataCite DOI; DBLP
  independently classifies the same title as CoRR and an informal/other
  publication. The arXiv abstract directly states the persistent BRAM state,
  five-phase pipeline, one state read/write pass, paired-head GVA, U55C target,
  and Vitis HLS flow.
- Timestamp: `2026-08-01`.

### E-G0-011 - Focused Gap Resolution And Citation Refresh

- Status: `PASS` for the controlled arithmetic-replacement framing, component
  ownership classification, official Qwen model citation, and bounded citation
  archival audit. This is not proof of first-ever novelty.
- Requirement: separate the inherited persistent-state/five-phase dataflow
  from the MXFP4 stability-and-cost question; classify close constituent prior
  art; and cite the exact model configuration from a primary record.
- Commands and exit codes: bounded primary-source searches and record checks;
  `pytest tests/test_citation_archival_audit.py`, exit code `0`.
- Source revision: `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; current
  source identity is recorded by the manifest header.
- Inputs: official Qwen model repository revision
  `9c7f2fbe84465e40164a94cc16cd30b6999b0cc7`, OCP MX v1.0, the Gupta et al.
  preprint, and the closest GDN, FPGA MX, cache/state quantization, and
  residual-buffer records listed in the prior-art matrix.
- Raw paths/hashes: focused resolution
  `docs/evidence/g0_focused_gap_resolution_2026_08_01.md`, SHA256
  `77393229087A8CE498193AA091588AFACA9032E080DE76E7B71C6BAF3079805F`;
  same-day gap recheck
  `docs/evidence/prior_art_gap_recheck_2026_08_02.md`, SHA256
  `266642B138A66DAE4ED57724256AFA1BC337EDA73655DAEDEA4D95DC31C4DAA0`;
  citation audit `docs/evidence/citation_archival_audit_2026_08_03_v3.csv`,
  SHA256
  `8E44CE1AE4C826B1ED88EF504085E8C45A8CAA786EFBDC1036D12AB0C4E8EDA3`;
  audit note `docs/evidence/citation_archival_audit_2026_08_03_v3.md`, SHA256
  `6162E4D3F5FCFE7ED58FABFC9DD34FF9274A433B1B429D533C2B61DF9AA6CB95`.
- Independent verification: the citation test requires a one-to-one mapping
  between manuscript bibliography keys and 16 PASS audit rows, primary HTTPS
  records for every entry, the exact seven-paper/one-standard/three-artifact/
  five-preprint classification, explicit preprint labels, and the pinned Qwen
  revision in both evidence and manuscript source.
- Result: the defensible contribution is the controlled empirical replacement
  study. Persistent state, the five-phase schedule, FPGA MX arithmetic, and the
  residual/write-log constituents are not claimed as firsts.
- Timestamp: original gap audit `2026-08-02`; citation refresh `2026-08-03`.

## G1/G2 Software Evidence Entries

### E-G1-001 - Independent FP64 And Corrected FP32 Recurrence

- Status: `PASS` for the local scalar/affine/FP32 requirement. Official
  framework parity is independently recorded in E-G1-003.
- Requirement: implement the K-by-V alpha-decayed recurrence independently,
  verify paired Q/K heads and boundary normalization, and compare FP32 with
  hand-derived and random FP64 results.
- Command and exit code:

  ```powershell
  $env:PYTHONPATH='C:\Users\tyboy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages'
  python -m pytest -q --junitxml=docs/evidence/g1_g2_software_pytest.xml
  ```

  Exit code `0`; the full suite reported 91 passed and 1 skipped.
- Source Git revision:
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`.
- Corrected source-patch SHA256:
  `B0AD3C5AA073C277C0EDDF14B4E18B50430F7959BCE14ADCC9CBF2E8EA7FDC45`.
- Input hashes: `golden/gdn_fp32.py`
  `7EBC9B7A0BA400A553E9C079B2E2E98596723DCC8B1D137B0477C798E34697C5`;
  `golden/gdn_oracle_fp64.py`
  `9C37880B58EF7272E1D441330D54576BE7512596A775FA9DDC25D4620F7CDB3F`;
  `tests/test_gdn_fp32.py`
  `52C0C7F89E2A6AD45D12B7F13D0D5AF8B0C15FEF353CA3A14F8B1D7B0B4395B2`;
  `tests/test_gdn_oracle_fp64.py`
  `C69615AE16E423BEB5AFD97320F981AC16F5BF58D3C561FD9055E3CFA35BAFC6`.
- Configuration/seeds: non-square hand cases; paired heads; alpha/beta zero and
  one; random affine sequence seed `0xA11CE`; FP32 random cases use fixed local
  seeds recorded in the tests.
- Tool versions: Python `3.12.10`, NumPy `2.3.5`, pytest `9.1.1`.
- Raw report: `docs/evidence/g1_g2_software_pytest.xml`, SHA256
  `8F7BEC453A0782E530AC91B2EC9BCD83B77249C35A714DD050FE59620DA38847`.
- Independent verification: the FP64 step uses explicit scalar loops and does
  not import production FP32; its sequence check uses a separately derived
  affine state transition. Hand-computable zero-state and endpoint cases guard
  against two implementations sharing the same algebraic mistake.
- Timestamp: `2026-08-01T01:52:34.268050-07:00`.

### E-G1-002 - Existing Runtime Exhaustion

- Status: `PASS` for the bounded inventory only; official framework parity
  remains `NOT_RUN`.
- Requirement: inspect all existing Windows, WSL, and local Docker Python
  runtimes before requesting installation or download approval.
- Commands and exit codes: WSL distribution/package/venv probes returned exit
  code `0`; Docker Desktop started successfully; Docker client/server were
  `29.6.1`; eleven network-disabled Python image probes returned `0`; three
  images without Python returned the expected `127`; Docker was shut down after
  inventory. Two preliminary WSL wrapper probes returned `1` because host
  quoting removed string literals and are documented in the raw log.
- Source Git revision:
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; corrected G1/G2 software
  source-patch SHA256:
  `B0AD3C5AA073C277C0EDDF14B4E18B50430F7959BCE14ADCC9CBF2E8EA7FDC45`.
- Input hashes: prior Windows/runtime inventory
  `AF17739F29F306BF6A49D475928A111DAB94B0CD23BD6A209FBC5F4BCCE1A78E`;
  current runtime log
  `5372DE7006E30146497D40A2923117890620CE8D835466779A6F6BB7C975BE8D`.
- Configuration/seeds: existing local artifacts only; Docker probes used
  `--rm --network none`; no randomness or seed.
- Tool versions: WSL `2.7.10.0`, Linux kernel `6.18.33.2-2`, Ubuntu Python
  `3.12.3`, Docker client/server `29.6.1`; GPU visible to WSL was an NVIDIA
  GeForce RTX 3070 with 8192 MiB.
- Raw report: `docs/evidence/g1_runtime_inventory_2026_08_01.txt`, SHA256
  `5372DE7006E30146497D40A2923117890620CE8D835466779A6F6BB7C975BE8D`.
- Independent verification: module discovery used Python `importlib` in the
  base WSL distro and every existing Docker image that contained Python;
  separate filesystem searches found no WSL virtual environment or alternate
  site-packages directory. No checked runtime contained Torch, Transformers,
  FLA, causal-conv1d, or Triton.
- Timestamp: `2026-08-01T20:45:00Z`.

### E-G1-003 - Pinned Official Recurrent/Chunk/Cache Parity

- Status: `PASS` for operator-level G1 parity at the exact Qwen recurrence-core
  dimensions. This is not a closed-loop model-quality result.
- Requirement: compare the independent local recurrence with pinned
  Transformers recurrent and chunk implementations, compare pinned FLA BF16
  recurrent/chunk kernels with the official fallback, and compare a chunk
  prefill plus one-token cache path with contiguous execution.
- Commands and exit codes:

  ```powershell
  wsl -d Ubuntu-24.04 --cd 'C:\Users\tyboy\OneDrive\Documents\mxfp4 improve\FPT26_data_review' -- /opt/gdn-parity/venv/bin/python -m scripts.official_parity --output-dir reports/golden/official_parity --seed 0xFB72 --tokens 128 --prefill-tokens 64 --qk-heads 16 --value-heads 32 --key-dim 128 --value-dim 128
  wsl -d Ubuntu-24.04 --cd 'C:\Users\tyboy\OneDrive\Documents\mxfp4 improve\FPT26_data_review' -- /opt/gdn-parity/venv/bin/python -m scripts.verify_official_parity reports/golden/official_parity
  ```

  Both commands returned exit code `0`; the runtime-internal `pip check` also
  returned `0` with `No broken requirements found.`
- Source Git revision:
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; official-parity source-patch
  SHA256:
  `465BAD47E0AEAE02B74D03D8D55DE99991A377DF9D5EE82529BF0FE11FD96D2F`.
- Input hashes/revisions: deterministic input NPZ SHA256
  `A3E0E6CF5DFA14FB16C51B4559F57B014E48BF9DB9C624FA17EF31AEFAEF68D8`;
  Transformers commit `8ac2b916b042b1f78b75c9eb941c0f5d2cdd8e10`; FLA commit
  `a670dff4c2537fc1a82486584dd9569e18fba833`. Exact official/local source
  hashes are embedded in the run manifest.
- Configuration/seeds: seed `0xFB72`; batch 1; 128 tokens; 64-token prefill;
  16 Q/K heads repeated to 32 value heads; K=V=128; nonzero FP32 initial state;
  FP32 and BF16 paths. Frozen FP32 limits are relative L2 `1e-5` and maximum
  absolute error `5e-5`; BF16 limits are relative L2 `0.03`, maximum absolute
  error `0.125`, and cosine at least `0.999`.
- Tool versions: WSL Ubuntu Python `3.12.3`; PyTorch `2.8.0+cu128`; CUDA runtime
  `12.8`; Triton `3.4.0`; Transformers `4.57.0`; FLA `0.2.1`; datasets `3.3.0`;
  NumPy `2.1.3`; NVIDIA GeForce RTX 3070, compute capability 8.6.
- Raw reports: metrics CSV SHA256
  `039F6DE415189A50501B03EB1A13EDA3CBED887E8B7BB08F0D36E1929403C8BF`;
  output arrays SHA256
  `161912784A644991BB1E2CFA7ACE6DDAA36DF51D9971C5DE5E4FC589F9534702`;
  run manifest SHA256
  `3E520E4CBE989FE1EE7A4A73119FD7B70413986AF68A803D6535D423B6729C0F`;
  independent verification report SHA256
  `BAD26B28390EE5C2F2DC985FD9A8BEC908DB262FA9456F53069500F885D35E54`.
- Result: all six rows are `PASS`. The largest FP32 relative L2 is
  `3.280705e-7`; the largest BF16 output/state relative L2 values are
  `0.005808352` and `0.004633965`, respectively.
- Independent verification: `scripts/verify_official_parity.py` independently
  reloads the archived arrays, recomputes every output/state metric, checks the
  CSV and manifest row sets/statuses, verifies three artifact hashes and six
  source hashes, and confirms both official source commits. The pinned official
  trees remain unmodified. Transformers 4.57.0 automatically enables only FLA
  0.2.2 or newer, so the pinned FLA 0.2.1 operator modules are loaded directly
  without executing unrelated model registrations or modifying official code.
- Timestamps: run `2026-08-01T21:26:52.046174+00:00`; independent verification
  `2026-08-01T21:26:59.918567+00:00`.

### E-G2-001 - Encoded-Integer MXFP4 Step Oracle

- Status: `PASS` for the one-step software arithmetic oracle only. Resident
  command and HLS C parity pass separately; the one-token RTL smoke is `FAIL`.
- Requirement: consume E2M1/E8M0/Q1.15 encodings and execute products,
  exponent alignment, signed RNE, INT32 saturation, output read, and state
  requantization without calling the FP32 recurrence.
- Command and exit code: the E-G1-001 full-suite command; exit code `0`.
- Source Git revision and corrected source-patch hash: E-G1-001.
- Input hashes: `golden/gdn_mxfp4_encoded.py`
  `CEF6C7EF1FEDA19359DF1E9B22E68DB295A13196117CEB8FCC389D88D33337C3`;
  `golden/mx_format.py`
  `B0F8BEE046465F342E8049B33A91C3E424C3C2C6E69FB53E85D2D63656BE269D`;
  `tests/test_gdn_mxfp4_encoded.py`
  `DAA4C678E920D3298CB7A4DB1CE36A0D1AE5836192B242C7F804FFAC029BB34A`.
- Configuration/seeds: every valid E2M1 code pair at E8M0 scale codes
  0/127/254; signed values -255 through 255 for shifts 1 through 8; Q1.15
  endpoints/ties; paired heads; noncanonical zero; invalid E8M0 255; changing
  scales; large alignment gaps; and output-before-state-requantization cases.
- Tool versions and raw JUnit report: E-G1-001.
- Independent verification: exact products are checked with Python `Fraction`
  arithmetic; signed RNE expected values are generated independently in the
  tests; a hand-derived one-dimensional state write checks recurrence ordering.
- Timestamp: `2026-08-01T01:52:34.268050-07:00`.

### E-G2-006 - Resident-State Command Oracle

- Status: `PASS` for the software control-plane oracle only. Corrected HLS C
  command parity and the current-source direct one-token RTL smoke pass
  separately; the legacy Vitis-wrapper smoke remains `FAIL`.
- Requirement: freeze `RESET/LOAD/STEP/READBACK` command and status codes,
  canonical reset, complete-payload validation, atomic state commit,
  sequence/layer isolation, per-command and cumulative counters, and generation
  tracking around the encoded arithmetic oracle.
- Command and exit code: `wsl -d Ubuntu-24.04 --cd <workspace> --
  /opt/gdn-parity/venv/bin/python -m pytest
  tests/test_gdn_resident_state.py -p no:cacheprovider -q
  --junitxml=docs/evidence/g2_resident_state_pytest.xml`; exit code `0`, 12
  passed. The complete-suite command used host Python with bundled packages via
  `PYTHONPATH` and wrote `post_g2_resident_state_pytest.xml`; exit code `0`, 108
  collected, 107 passed, one existing Phase 7 pack skip, zero failures/errors.
  A later host rerun after adding explicit all-layer iteration returned exit
  code `0` with 13 passed.
- Source Git revision: `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`.
  Resident source-patch SHA256:
  `974A8DE309C387A15F21F96A27C3F35F300994F6AC1279765ACD121947E998B9`.
- Input hashes: `golden/gdn_resident_state.py`
  `963B043623BF1585F7DCB40BD497CD7FED682D0A7187563F314316D786135217`;
  `tests/test_gdn_resident_state.py`
  `99D8F9945BE0BB09A9A08E8CF6BECE54C535F166BDAE749B3B9BA9445EFBD5E8`;
  frozen contract `1AE6EA0941499440F31D896B62597AC0877587E5303D12BD0863338EFBBC2CA9`.
  The later all-layer test source SHA256 is
  `3DD5038CAC0BE7C1111E7EB5050683FE885D308AB7789EA7411409B6BC0A60A6`.
- Configuration/seeds: no randomness. Tests use two sequence slots, all 36
  valid layer selectors, two value heads sharing one Q/K head, K=2, V=3, B16,
  valid and malformed E2M1/E8M0 payloads, missing/unexpected payloads, and
  literal command/status/generation expectations. The default oracle remains
  the controlled Qwen shape: one sequence, 36 layers, 16 Q/K heads, 32 value
  heads, K=V=128, B32.
- Tool versions: targeted run Ubuntu Python `3.12.3`, NumPy `2.1.3`, pytest
  `9.0.2`; complete run Windows Python `3.12.10`, NumPy `2.3.5`, ReportLab
  `4.4.9`, pytest `9.1.1`.
- Raw evidence: targeted JUnit SHA256
  `B9F6EA99A352240FEBCF6A050201F2D4A59BE973A0D6E69EE257E060C60B4B7B`;
  complete-suite JUnit SHA256
  `5B2F002AEE2B117E0F28344CF7A1A32457E2C6565467C8A56FC97D483D32BD8C`;
  all-layer host-rerun log SHA256
  `F95AD150D263D233C98824CB0380F71FEE8F7CBBA6CA50E7E1BE468069CD9CBA`;
  source patch and hash list are under `docs/evidence/`.
- Independent verification: PowerShell independently parsed both JUnit files
  and confirmed their tests/failures/errors/skips fields. The tests compare a
  committed `STEP` directly with `recurrence_core_step_encoded`, use literal
  canonical-zero/status/generation expectations, mutate caller-owned buffers to
  detect aliasing, and compare state snapshots before and after rejected
  commands. The later test resets every valid layer ID, steps alternating
  layers, and verifies all 36 generation/state snapshots independently.
  `git diff --check` returned `0` with only existing line-ending warnings.
- Preserved failed attempt: the G1 parity venv lacks ReportLab, so its initial
  full-suite collection attempt returned exit code `1` before running tests.
  That one-error JUnit is preserved as
  `post_g2_resident_state_wsl_missing_reportlab_pytest.xml`, SHA256
  `4D12BB48D1B1F2D194DDFDF27AF3CBF83ABF108FE6E4722192EB0B7F186F51D8`;
  the targeted resident tests in that same venv had already passed.
- Timestamp: `2026-08-01T21:44:03.2240727+00:00`.
  All-layer augmentation: `2026-08-02`.

### E-G2-002 - Full-Dimension Nominal Long Trace

- Status: `PASS` for deterministic execution/artifact integrity; the candidate
  engineering result is `FAIL`.
- Requirement: run one shared synthetic prefix at required checkpoints for
  FP32, BF16 operands/state with FP32 accumulation, uniform MXFP4 state,
  MXFP8-E4M3 state fallback, and flat INT4.
- Command and exit code: `python -m scripts.long_sequence_stability`; exit code
  `0`; measured wall time `1088.2` seconds.
- Source Git revision `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe` and
  run-specific dirty-patch SHA256
  `1C473C5961DE371C72BD06E958824FD042D150BE9991CAB8F45973ACFB11F69A`. Exact
  per-generator-file hashes at execution time are stored in
  `reports/benchmark/corrected/long_trace_manifest.json`; notably the executed
  `scripts/long_sequence_stability.py` hash is
  `977BA478F143676388BBC78B87777330269E150ABAFC38C68B848A9647B05C14`.
- Inputs/configuration: split `development`, seed `0xFB72` (64370), family
  `nominal`, 32 value heads, 16 Q/K heads, K=V=128, activation/state B32,
  token prefix 1..8192, checkpoints 64/256/1024/4096/8192. The same input
  generator/configuration was independently rehashed by E-G2-003 as SHA256
  `ADB9105CE36C702EEB5D72A52145AED951C55752E9A541BAFBB549E61679DF0E`;
  initial-state SHA256
  `CB92F5959750AB44FBB97A8AA7C416961CDE747284B54511A47CBAEA26F13D19`.
- Tool versions: Python `3.12.10`, NumPy `2.3.5`.
- Raw paths and hashes: token CSV
  `C074D9709DE38297AD1FD77B87F2DF21AEA563D72827AFA9D1B1488DD6909904`;
  checkpoint CSV
  `BA27DD61AE09FC009C95B0E586B9E7BF8D275A9425EF014A554D6359730349AA`;
  report `67E3044CA21B511C1610CBD945BADF11D561FC1453CCA0171BE1711307375887`;
  manifest `6814584CC6C073E951EA5A1732FECB76780D3CA01C532E0869B44E74C3AC657A`.
- Independent verification: `python -m scripts.verify_synthetic_stability`
  rehashes every declared source and output, verifies 40,960 token rows and 25
  canonical checkpoint rows, checks all five complete 1..8192 sequences, and
  cross-checks the shared input/initial-state hashes against E-G2-003.
- Result: BF16 passes with token-8192 output cosine/state relative L2
  `0.999955`/`0.008988`. Uniform MXFP4 state is output cosine `0.729275` and
  state relative L2 `1.103841`; MXFP8-E4M3 state is `0.968498` and `0.232133`.
  Both fail the frozen `0.99`/`0.10` development thresholds. Event metrics for
  these floating Q/DQ rows are explicitly `NOT_RUN`.
- Timestamp: `2026-08-02T03:26:31.178993+00:00`.

### E-G2-003 - Full-Dimension Scale-Policy Ablation

- Status: `PASS` for deterministic execution/artifact integrity; every tested
  policy's engineering result is `FAIL`.
- Requirement: compare fixed, every-token, periodic N=4/8/16, and threshold
  `[0.75,5.5]` state-scale refresh with all other recurrence inputs fixed.
- Command and exit code: `python -m scripts.scale_policy_ablation`; exit code
  `0`; measured wall time `2513.2` seconds.
- Source Git revision `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe` and
  run-specific dirty-patch SHA256
  `84EFD72607FAE237C07B7BCD957DC917B044783AD8CD15D9984165505A9B38C0`. Exact source
  hashes at execution time are in the run manifest.
- Inputs/configuration: identical dimensions, split, seed, nominal family, and
  checkpoint prefix as E-G2-002; ordered tensor-stream SHA256
  `ADB9105CE36C702EEB5D72A52145AED951C55752E9A541BAFBB549E61679DF0E`;
  initial-state SHA256
  `CB92F5959750AB44FBB97A8AA7C416961CDE747284B54511A47CBAEA26F13D19`.
- Tool versions: Python `3.12.10`, NumPy `2.3.5`.
- Raw paths and hashes: token CSV
  `519E36FA962721E6931E3672F3FA5903014EB10ECA83AC4176286C49C5ED623C`;
  checkpoint CSV
  `6C2FF3F714F856AC0D4471EC3C0CEC6E95CF8A13DC4154F7E847B0B8E65C96F0`;
  report `C7B0CDAB2C53EEF71D1FA8EADD84001D192ED9C1BB81D6D10BB35AEB071A44EE`;
  manifest `1BBFBC435A19BDADC45FC047727F3456B0C9D51E8556FBE8E06863FBE91FC7E4`.
- Independent verification: `scripts.verify_synthetic_stability` finds 49,152
  token rows and 30 canonical checkpoint rows, checks six complete token-policy
  sequences, verifies event-count domains, and proves every-token refresh is
  identical to the independently executed uniform-MXFP4 trace at all 8192 tokens.
- Result: no policy passes. Fixed scales are least-bad numerically at token 8192
  (`0.847089` cosine, `0.676620` state relative L2) but record 67,980,414
  state-element clips. Threshold refresh records zero state-element clips but
  reaches `0.558410` and `1.724816`. Events are scoped to floating-Q/DQ state
  requantization and are not encoded accumulator or HLS counters.
- Timestamp: `2026-08-02T04:10:58.004273+00:00`.

### E-G2-004 - Corrected Long-Trace Vector Figures

- Status: `PASS` for vector generation and visual layout only; the figures are
  labeled diagnostic and do not make the scientific gate pass.
- Requirement: generate output-cosine and state-relative-L2 PDF plots from the
  corrected token CSV and visually inspect the rendered output.
- Command and exit code: `python -m scripts.plot_long_sequence_stability`, then
  bundled Poppler `pdftoppm -singlefile -png -r 180`; exit code `0`.
- Source Git revision and run-specific source identity are in the plot manifest.
- Input hash: E-G2-002 token CSV
  `C074D9709DE38297AD1FD77B87F2DF21AEA563D72827AFA9D1B1488DD6909904`.
- Configuration/seeds and tool versions: E-G2-002; ReportLab `4.4.9`, bundled
  Poppler renderer.
- Raw outputs: `paper/figures/corrected/output_cosine_vs_token.pdf`, SHA256
  `7F8075964D56EA7207DFE499ECDAE27CB8CFA98CD9CC0C75078525CCB66B5C69`;
  `state_relative_l2_vs_token.pdf`, SHA256
  `D9FA1A96319B29FB9BFE65A1B103783A54ECD90082DCB4DCD2B450E80BC8D813`;
  plot manifest `BC0FA1E3373C327A95EA4DCA648E650011A5C8157F61EA2A9FE9B1A5F249328D`.
- Independent verification: both PDFs were rendered at 180 dpi and visually
  inspected for titles, identity-stable colors, legends, decision lines, axes,
  log scaling, footer labels, clipping, overlap, and full 8192-token coverage.
- Timestamp: plot manifest `2026-08-02T04:14:46.423332+00:00`.

### E-G1G2-005 - Corrected Software Regression Suite

- Status: `PASS` for the checked-in Python test suite.
- Requirement: run all repository tests after recurrence, format, oracle,
  long-trace, scale-policy, and plotting changes.
- Command, source revision/patch, tool versions, raw path, hash, and timestamp:
  E-G1-001.
- Result: 92 collected, 91 passed, 1 skipped, 0 failed, 0 errors in 0.60 seconds.
  The skip is `test_phase7_pack_contains_sweep_evidence_when_present` because no
  Phase 7 pack exists for the source revision.
- Independent verification: JUnit XML was parsed separately for test, failure,
  error, skip, timestamp, and skip-reason fields; `git diff --check` returned
  exit code `0` with only a line-ending warning for `AGENTS.md`.
- Post-reviewer-source rerun: the same full-suite command wrote
  `docs/evidence/post_reviewer_pytest.xml`, SHA256
  `C904F4AF0A8D4D32297240EE326DF6AC3A1FBD89D06A6A15529EF528D5476DE3`;
  exit code `0`, 92 collected, 91 passed, 1 skipped, 0 failed, and 0 errors in
  1.54 seconds. The skip reason is unchanged. Pytest warned that it could not
  write `.pytest_cache` because of host ownership, which did not affect test
  collection or execution. Python compilation of the reconciliation script,
  Node syntax checking of the artifact-tool extractor, and `git diff --check`
  each returned `0`. A clean-room reconciliation under `build/` reproduced the
  traceability Markdown and both CSV hashes exactly.
- Post-reviewer-source timestamp: `2026-08-01T20:41:45.1994767Z`.
- Post-G1 parity rerun: the full-suite command wrote
  `docs/evidence/post_g1_official_parity_pytest.xml`, SHA256
  `9E0349E12C20A63E918213FD9026E1D403CC9EA909F3F5E7023C6A5EC03BF1DA`;
  exit code `0`, 96 collected, 95 passed, 1 skipped, 0 failed, and 0 errors in
  0.61 seconds. The four new parity-helper tests pass; the existing Phase 7
  pack skip and cache-write warning are unchanged.
- Post-G3/HLS-cleanup rerun: the full-suite command wrote
  `docs/evidence/post_g3_write_log_pytest.xml`, SHA256
  `E89629BD78724648F6E3AE0D26DA346B5441281C1603F09A59348C2E2F8A2EA6`;
  exit code `0`, 138 collected, 136 passed, 2 skipped, 0 failed, and 0 errors
  in 0.88 seconds. The skips are the prohibited pre-gate Phase 7 pack and the
  absent complete current-source RTL co-simulation report. Both are recorded
  in `reports/known_issues.md`.
- Post-G3/HLS-cleanup timestamp: `2026-08-02T01:15:05.662457+00:00`.

## G2 Hardware Evidence Entries

### E-G2-007 - Frozen Full-Dimension HLS Command Trace

- Status: `PASS` for deterministic generation and independent structural/hash
  verification.
- Requirement: freeze at least 64 full-dimension encoded steps, including
  complete expected outputs, counters, and final resident state.
- Commands and exit codes: `python -m scripts.generate_hls_command_trace` and
  `python -m scripts.verify_hls_command_trace`; both exit code `0`.
- Source Git revision and dirty-patch hash: manifest header. Exact execution
  source hashes for five golden/generator files are in the trace manifest.
- Inputs/configuration: development nominal trace, seed `0xFB72`, 64 tokens,
  one sequence, layer 0 of 36, 16 Q/K heads, 32 value heads, K=V=128, B32.
  Ordered floating input-stream SHA256:
  `617F8F961DABA23CC7F161527F2AB60E3B09017BD2019EFA4A0C698222782BDA`.
- Tool versions: Python `3.12.10`, NumPy `2.3.5`, Windows 11.
- Raw paths and hashes: binary
  `data/vectors/corrected_gdn_command_trace.bin`, SHA256
  `677A4C1673754AD7603EC05FBA4FFC7B5417B5763B293F69B5E798C1769659C0`;
  manifest `CE6B3EA04B16BD074B8BB9DC10738C31F0A028A16309CDC32AA1BF1E57EF5EC8`;
  summary CSV `8A5F5D8045A30583DED33165A7DE802D541A75619B54B654C9BAEE84E5B7A4F5`.
- Independent verification: the verifier rehashes all five execution sources,
  binary and summary artifacts; parses every record; checks lengths, command
  ordering, finite metadata, generation monotonicity, and final counters.
- Result: 64 committed steps, zero element/accumulator saturation, zero scale
  clamps, zero rejected commands, 112,565 state-scale changes, and 16,054,881
  counted alignment underflows.
- Timestamp: generation completed `2026-08-01T22:17:03.384298+00:00`;
  verification `2026-08-01T22:19:51.195981+00:00`.

### E-G2-008 - Corrected HLS C-Simulation Parity

- Status: `PASS` for HLS C execution at the frozen encoded boundary.
- Requirement: execute hand-command coverage and the complete 64-step oracle
  trace with exact status/output/state/counter equality.
- Commands and exit codes: `python -m scripts.hls_flow csim`, then
  `python -m scripts.csim_report`; exit code `0`.
- Source Git revision and dirty-patch hash: manifest header. The C-sim manifest
  freezes SHA256 for every HLS include/source, the top testbench, C-sim TCL, and
  trace generator.
- Input/configuration/seeds: E-G2-007; U55C target
  `xcu55c-fsvh2892-2L-e`, 4.0 ns clock target.
- Tool versions: Vitis HLS `2025.2` build `6295257`; C++14 synthesis boundary.
- Raw paths and hashes: `reports/csim/corrected/gdn_top_csim.log`, SHA256
  `6DE97D87AEF498E03A65105619885F6D48A10BADA78670A7D953F14B3AE91CC8`;
  C-sim manifest
  `7B4E8DEA217EF69D229B8E046811A3A25F8D91313EDD638DD4393930D398EEDA`;
  human-readable result `reports/csim/corrected/results.md`.
- Independent verification: the C++ testbench compares 75 hand-command checks
  and 64 oracle steps, including every output code/exponent, all eight
  per-command and cumulative counters, status, generation, and complete final
  state readback. `scripts.csim_report` independently checks the PASS marker,
  zero-error tool terminator, trace hash, and source/log freshness.
- Result: `tb_gdn_top PASS hand_commands=75 oracle_steps=64`; Vitis reports
  `CSim done with 0 errors`.
- Timestamp: `2026-08-02T01:04:14.518500+00:00`.

### E-G2-009 - Corrected Uniform-MXFP4 Baseline C-Synthesis

- Status: `PASS` for fresh report extraction, completed HLS C synthesis, and
  the vendor loop-constraint summary. RTL and physical implementation remain
  unverified.
- Requirement: synthesize the corrected controlled baseline for the U55C at the
  fixed 4.0 ns target and preserve timing, loop, resource, and source evidence.
- Commands and exit codes: `python -m scripts.hls_flow csynth`, then
  `python -m scripts.corrected_hls_report`; exit code `0`.
- Source Git revision and dirty-patch hash: manifest header. The extractor
  verifies that current HLS source hashes equal the preceding C-sim hashes and
  that the archived synthesis log is newer than every source.
- Input/configuration: uniform encoded OCP MXFP4-B32 baseline, 16 Q/K heads, 32
  value heads, K=V=128, 36 runtime-addressable layer slots, `P_K=16`, `P_V=8`,
  U55C `xcu55c-fsvh2892-2L-e`, 4.0 ns target.
- Tool versions: Vitis HLS `2025.2`; synthesis command completed in 107 seconds.
- Raw paths and hashes: immutable attempt directory
  `reports/csynth/corrected_attempt9_transport_pipeline_cleanup/`, canonical
  tree SHA256
  `8FE9BEF86E9A92E46F79D96C536C1E12DDA6E6587280D53B70DD9FD1A0ECE60E`;
  top XML
  `77A607DEC1E4AF82EA165FEF5DB144B0C1175E88CD682E9B6B404A7BC6802103`;
  extraction JSON
  `E41A7D78948384082C447C09A04679BC013457E8440F541E773126C3916A0CD3`.
  Failed attempts 7 and 8 remain preserved in their original archive
  directories rather than being overwritten.
- Independent verification: `scripts.corrected_hls_report` parses XML rather
  than presentation text for timing/latency/resources, separately parses the
  reported SLR rows and every loop result, hashes the complete raw artifact
  tree, and refuses stale or C-sim-mismatched source.
- Result: estimated clock `2.920` ns (`342.47` MHz); 138,969 LUT, 43,962 FF,
  24 BRAM18K, 32 URAM, and 3 DSP. Reported one-SLR utilization is 31% LUT, 5%
  FF, 1% BRAM18K, and 10% URAM. All 14 explicitly targeted loops reach II=1,
  and Vitis reports `All loop constraints were satisfied`. Automatic
  pipelining is disabled for control/transport loops. No post-route inference
  is made.
- Timestamp: raw log `2026-08-02T01:06:05.733432+00:00`; extraction
  `2026-08-02T01:06:54.063596+00:00`.

### E-G2-010 - Bounded Corrected RTL Co-simulation Smoke

- Status: `FAIL` for the one-token Verilog RTL smoke. The generated C
  testbench is `PASS`; required 64-token RTL parity was `NOT_RUN` in this
  wrapper attempt and later passes through the direct harness in E-G2-016.
- Requirement: make one bounded XSIM attempt before deciding whether the full
  64-token, 141-transaction parity run is feasible on the available host.
- Command and exit code:

  ```powershell
  $env:GDN_COSIM_VECTORS='1'
  $env:GDN_COSIM_TRACE='reports/cosim/corrected/smoke_1token/trace.bin'
  python -m scripts.hls_flow cosim
  ```

  Exit code `1`; HLS reports 673 seconds for `cosim_design`.
- Source Git revision and dirty-patch hash: manifest header. The extraction
  JSON freezes every HLS include/source, testbench, and co-simulation TCL hash.
- Input/configuration: deterministic development trace, seed `0xFB72`, one
  oracle token, uniform corrected OCP MXFP4-B32 baseline, U55C target, 4.0 ns
  clock target. Trace SHA256:
  `67D2D2A1A0345D8844F20F292414BD65D0D81FEBAAB29D34C2A8DADF1A5B6175`.
- Tool versions: Vitis HLS and XSIM `2025.2`.
- Raw paths and hashes: `reports/cosim/corrected/smoke_1token/raw/xsim.log`,
  SHA256
  `64BE9D28EEC283D685312618E5CFD66E8714152527A785D75487BE6963BDD83F`;
  raw co-simulation report
  `A61A7E7E02D0A611A8E9A28DBEECB9F915FC54F6A7AA7BA6D2A9AEC6CC2E697A`;
  extraction JSON
  `189CBFF2F418F4504F7618B34BCAD1153E7BAB5B570C07B6E3922497E3A935AF`;
  frozen extraction-at-run JSON
  `3404FBE7400E4DACC79BBC8555935072E671F83EFEF9491688B892D4AD301E68`.
- Independent verification: `scripts.corrected_cosim_report` requires the C
  PASS marker, parses the last XSIM inter-transaction record, requires the raw
  out-of-memory marker and Verilog FAIL report, and hashes all archived logs.
- Result: the C testbench reports `hand_commands=12 oracle_steps=1`. XSIM
  completes 3 of 15 top-level transactions, then fails during transaction 4,
  the first valid full STEP, while requesting another 8,388,608 bytes. No
  recurrent STEP reaches RTL post-check, so this is not parity or latency
  evidence. The full 64-token run was not launched. Later pipeline-directive
  cleanup changes `block_exp_align.cpp` and `phase1_prepare.cpp`; the extractor
  reports both mismatches and does not apply the smoke to current RTL.
- Timestamp: raw report `2026-08-02T00:52:52+00:00`; extraction
  `2026-08-02T01:09:43.488528+00:00`.

### E-G2-011 - Current-Source Direct RTL Smoke

- Status: `PASS` for one bounded RESET/STEP/READBACK generated-Verilog smoke;
  required 64-token RTL parity later passes in E-G2-016.
- Requirement: bypass the memory-exhausting Vitis UVM wrapper without bypassing
  the current HLS-generated Verilog, then demonstrate that one recurrent STEP
  can execute on the available host.
- Commands and exit codes: `xvlog -prj direct_rtl.prj`, `xelab
  xil_defaultlib.tb_gdn_top_direct -s direct_rtl_smoke`, and `xsim
  direct_rtl_smoke --runall --stats`; all exit code `0`.
- Source revision: `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe` with a dirty
  working tree. The summary freezes both SystemVerilog source hashes, all 86
  generated Verilog files, and all 14 initialization files. Testbench SHA256 is
  `196FE4BD7F289E9B8BD2BCBF6D4099E46D642A44BAEC71497F2BF18B3912509B`.
- Configuration/tools: deterministic layer 0, one token, K=V=128, 32 value
  heads, `P_K=16`, `P_V=8`, B32; AMD XSIM `2025.2`.
- Raw paths/hashes: XSIM log
  `FACF3907ABD528E5212843FDA64EF95B06DCE60C12BE81014DCFFCF64B5E6FCD`;
  summary JSON
  `AA1148F1FAB9DFAFF6B9C9D67FCF31D3D209FEB6781F97769DDF121E3D885614`.
- Independent verification: fatal testbench checks cover reset status and
  generation, STEP status/generation/committed counter, first and last output,
  updated and untouched state, state scales, and READBACK; the Python report
  independently parses all three commands and hashes raw/generated inputs.
- Result: STEP latency is 5,597,299 simulated cycles; peak XSIM kernel memory is
  83,580 KiB. This is pre-synthesis generated RTL, not post-route or board
  evidence.
- Timestamp: `2026-08-02T02:29:02.247570+00:00`.

### E-G2-012 - Matched BF16 HLS Baseline

- Status: `PASS` for bounded HLS C simulation and HLS C-synthesis extraction.
  BF16 64-token RTL parity, post-route evidence, and energy are `NOT_RUN`.
- Requirement: hold the corrected recurrence-core boundary, K-by-V state,
  36 layer slots, `P_K=16`, `P_V=8`, B32 banking, U55C target, and 4.0 ns
  constraint constant while replacing MXFP4 operands/state with BF16 and using
  FP32 accumulation.
- Commands and exit codes: `vitis_hls -f X:/hls/bf16/tcl/run_csim.tcl` and
  `vitis_hls -f X:/hls/bf16/tcl/run_csynth.tcl`; both exit code `0` with Vitis
  HLS `2025.2`. The final-source C simulation was rerun after synthesis.
- Source revision and dirty-patch SHA256:
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe` and
  `8886E76675F7018F4FF8331758FEB0F36FDD2B24652E406DEFE9F6BD79A4A4A0`.
  The summary freezes common parameters, BF16 header/source/testbench/TCL, and
  extractor source hashes.
- Inputs/configuration: deterministic hand-computable RESET, sparse rank-one
  STEP, beta-zero persistence STEP, and complete 524,288-element READBACK.
- Raw paths/hashes: final C-sim log
  `E80588EC4E145D7A056364331A35EA18009A6967D23E327E0B00CFE526DF5CB5`;
  top XML
  `9EA0EDD568ACCEFA3CC81E467F18383B4D840A7E2386E82CE5499C50512F0378`;
  implementation report
  `5B98EA56982AE9FCAB1EA34D208A08B661788042682E38983F405CFA34FF540F`;
  extraction JSON
  `010349D332F8843CF6E3B6511B486116BF5FF6033744CE672BF1552C558F2F95`.
- Independent verification: `scripts.bf16_hls_report` requires final-source
  freshness, both tool completion markers, the exact C-sim marker, all 19
  explicit II=1 constraints, the vendor loop-constraint PASS, target/clock,
  STEP-loop extraction, and raw hashes. Five focused extractor/comparison/
  capacity tests independently pass.
- Result: estimated 2.920 ns (342.47 MHz), STEP loop 4,225,728 cycles, 84,919
  LUT, 39,087 FF, 13 BRAM18K, 128 reported URAM, and 0 DSP. The C-sim test is
  bounded and is not random-vector or RTL parity.
- Preserved failed attempt: `reports/csynth/corrected/bf16_attempt1_axi_validation_path/`
  records 7.002 ns (142.82 MHz) and a LOAD-only II=8 validation path before the
  non-arithmetic LOAD validation loop was corrected. It is not reused.
- Timestamp: extraction `2026-08-02T03:40:41.656335+00:00`.

### E-G2-013 - Controlled HLS And State-Capacity Comparison

- Status: `PASS` for extraction/calculation; uniform-MXFP4 HLS LUT/STEP
  advantage is `FAIL`; energy and physical fit are `NOT_RUN`.
- Requirement: compare BF16 and uniform MXFP4 at identical recurrence,
  dimensions, state layout, layer slots, parallelism, target, block size, and
  clock constraint, then independently reconcile logical state capacity with
  HLS-reported memory totals.
- Commands and exit codes: `python -m scripts.hls_arithmetic_comparison` and
  `python -m scripts.state_capacity_lower_bound`; both exit code `0`.
- Source revision and run-specific dirty-patch hashes are in both JSON
  manifests. Raw input HLS summaries and implementation reports are hashed by
  each extractor.
- Raw outputs/hashes: controlled comparison CSV
  `58E395114D4E7B16F8EC699FEFC090852201639929AC5E32A220DFCBBF128741`;
  JSON `7F46D97EA7E3C29C8CC2B0EE4D5679138D9D4BA9E5A3030C74ED791E0C8E5A46`;
  capacity CSV
  `EE21E4FCA9AE34210DE96C5498FFEB79A826F91465B1B27CA036B14643320FBE`;
  capacity JSON
  `E92205E53D8FDFB2609E0822B8DD2E1473D7B004D1AE782DF4351910843144C6`.
- Independent verification: parsers independently extract both STEP loops,
  compare target/clock fields, compute ratios, parse device resource totals,
  and recompute `ceil(logical bits / primitive capacity)` lower bounds. Five
  focused real-artifact tests pass.
- Result: uniform MXFP4 uses 1.636x BF16 LUTs and 1.437x BF16 maximum STEP
  cycles at the same 2.920 ns estimate. Per-layer logical state is 278,528 bytes
  versus 1,048,576 bytes for BF16, a 73.4375% reduction. Across 36 slots, BF16
  requires an ideal minimum of 1,024 URAM288, exceeding 960 device URAM; MXFP4
  requires at least 256 URAM288 plus 256 BRAM18K. HLS totals below these
  state-only bounds are not accepted as physical-fit evidence.
- Timestamp: comparison `2026-08-02T03:40:42.018702+00:00`; capacity
  `2026-08-02T03:45:13.916370+00:00`.

### E-G2-014 - Validated Synthetic Decision And Research Answer

- Status: `PASS` for artifact verification and controlled evidence synthesis;
  the current native/uniform-MXFP4 replacement answer is `FAIL`.
- Commands and exit codes: `python -m scripts.verify_synthetic_stability` and
  `python -m scripts.replacement_question_summary`; final attempts exit code
  `0`.
- Inputs/configuration/seeds/tools: E-G2-002, E-G2-003, E-G2-012, E-G2-013,
  and the later native evidence in E-G2-017. Every input manifest/CSV is
  rehashed; Python is `3.12.10`, NumPy `2.3.5`.
- Raw outputs/hashes: verifier JSON
  `ECE6BBC33FE35C38DAED8286B10EF07D8B626E7A229AF5776CB70D42195D1317`;
  answer JSON
  `E22E43D7F53190D7F01F503A75B344D5FE29593A1D7C3C1434001EAB66102383`;
  answer Markdown
  `C71564E2B3254FDD948BBF8B7504400518BBBE98C8E3FB11230AF6AAE09A9FC3`.
- Validation: exact row counts/sequences, canonical checkpoint
  projections, source/output hashes, shared input and initial-state hashes,
  event domains, every-token policy parity, status vocabulary, state-byte
  calculation, and input hashes are all checked independently.
- Result: BF16 synthetic stability is `PASS`; native encoded MXFP4, floating
  uniform MXFP4, MXFP8-state, flat INT4, every scale policy, and MXFP4 HLS
  LUT/STEP advantage and the corrected candidate's configured timing margin are
  `FAIL`. Logical storage reduction is `PASS`; energy and physical fit are
  `NOT_RUN`. The current answer is therefore no for this
  native uniform-MXFP4 implementation, limited to the tested synthetic trace
  and HLS-estimate stage. The correction passes its bounded synthetic quality
  checks but not the selected-method Pareto gate.
- Preserved failed attempt: the first verifier invocation returned exit code
  `1` because the verifier compared execution-order token projections with
  canonically sorted checkpoint rows. Log SHA256
  `01BD1B376252A7DD9F6A7A59098652A2A19306B23C030B7ECC1DA2B41845E622`.
  The verifier now sorts both sides before exact equality; no benchmark data
  changed.
- Timestamp: verifier `2026-08-02T04:11:55.278549+00:00`; reissued answer
  `2026-08-02T17:51:50.784822+00:00`.

### E-G2-015 - Focused Stability And HLS Regression

- Status: `PASS` for the completed checks; one evidence-dependent test was
  skipped because required 64-token direct RTL evidence was `NOT_RUN` at this
  execution point. E-G2-016 later closes that requirement.
- Command and exit code: focused pytest across BF16, write-log, long-trace,
  scale-policy, verifier, plot, HLS extractors, capacity, replacement summary,
  BF16 sources, and direct RTL reports; exit code `0`.
- Tool/version/configuration: Python `3.12.10`, pytest `9.1.1`, repository
  revision above, repo-local pytest base directory because the Windows default
  temporary directory is inaccessible.
- Raw log/hash: `reports/test_results/focused_stability_hls_20260801.log`,
  `57591B2BE14548784DE992C3B020B158D60576004B50E87073D2FD7C8D1DE198`.
- Result: 39 passed, 1 skipped, 0 failed in 4.30 seconds. The sole skip was the
  real 64-token direct-RTL evidence check; E-G2-016 later passes it.
- Timestamp: `2026-08-02T04:15:00+00:00` (bounded by log and adjacent artifact
  timestamps).

### E-G2-016 - Required 64-Token Direct RTL Parity

- Status: `PASS` for sequential 64-token bit-exact parity of current-source
  HLS-generated Verilog against the independently verified encoded oracle.
- Requirement: execute one RESET, 64 ordered STEP commands, and one READBACK;
  compare every output and counter at every token and the complete final
  recurrent state before accepting the result.
- Commands and exit codes: `xvlog -prj direct_rtl.prj -d GDN_TRACE64`, `xelab
  xil_defaultlib.tb_gdn_top_direct -s direct_rtl_trace64 --mt 8
  --ignore_coverage --ignore_assertions --stats`, `xsim direct_rtl_trace64
  --runall --stats --ignore_coverage --ignore_assertions`, and `python -m
  scripts.direct_rtl_trace_report`; all exit code `0`.
- Source revision and dirty-patch hash: revision
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; the report freezes 21 direct
  harness, verifier, HLS include/source/TCL files under dirty-patch SHA256
  `23B7BE9FEC8E157AF88FAC2D9D7C300B45B5612E483E171B663AC5D04574D357`,
  plus all 86 generated Verilog files and 14 initialization files.
- Inputs/configuration: frozen layer 3 command trace, seed `0xFB72`, 64 tokens,
  16 Q/K heads, 32 value heads, K=V=128, B32, `P_K=16`, and `P_V=8`.
  Trace SHA256 is
  `677A4C1673754AD7603EC05FBA4FFC7B5417B5763B293F69B5E798C1769659C0`;
  asset-manifest SHA256 is
  `B6033992CA0E1E8643AEC29D31A236405ED396C3F1EE90E51C57B4CBD01DD375`;
  oracle-verification SHA256 is
  `593CF9F9DB65EC4C0735AF0C619BE2E76C6767C270DFA78904493317D7E9CAFE`.
- Tools: AMD Vivado/XSIM `2025.2`; report verification uses Python `3.12.10`
  and NumPy `2.3.5`.
- Raw paths and hashes: XSIM log
  `6AAA1CA7F21F7FCBD466EB9757EEAFA6E8F9D62673C04B5D588FB9C725DD4627`;
  XELAB log
  `4F14E6CF2A01A968EA9AE76A71925B15EA341877F7E1BC2E7F4976A808342917`;
  XVLOG log
  `6236701A030FEB48A3215C601896925189A6789D27EF761896869A13D89FCB3D`;
  project file
  `B092A7ED9154ADADACDFC52C2BDB48C376ED90F5A1E84B3BA0F854669724F24B`;
  XSIM journal
  `53677BDD75E8F99AAB7A1FE371AB98D0D30F20A32B5F576DD4C5470BC73662AD`;
  summary JSON
  `D140A93463C5C619974E2862AC06DB4EBA730C8E800719DB016AD0FCF25A2923`;
  summary Markdown
  `A6E57F35737C097CB5C5D19E922ED272B7CB0C8282E134A2BF81005E7C388EDC`;
  report log
  `3A48CEA9E42F5710853ED42C64BAF6C5B545A856147C424F5466C7543FF397D2`;
  focused verification log
  `D30D48B8A1A34FACABB947BD3C521469CE6A74F2E7EA6D9B47140FF7A4388ECE`.
- Independent verification: the SystemVerilog harness uses fatal checks for all
  262,144 output mantissas, 262,144 output exponents, 512 command counters, 512
  cumulative counters, 524,288 final-state elements, 16,384 final scales, every
  status, and every generation. The Python report independently reparses all 66
  commands and 64 token markers, rehashes every source/asset/log, and requires
  the terminal PASS marker. Eight focused report/gate tests pass.
- Result: STEP latency ranges from 5,461,867 to 6,137,971 simulated cycles,
  with mean 6,123,314.875 and median 6,137,971. The XSIM kernel reports 89,988
  KiB peak memory and the simulation completes in 4:54:31 elapsed. This is
  pre-synthesis generated-RTL simulation using a custom direct AXI harness, not
  Vitis UVM, post-route, power, energy, physical-fit, or board evidence. It
  validates the uniform-MXFP4 baseline, not the write-log candidate.
- Timestamp: report `2026-08-02T07:29:45.370971+00:00`; XSIM exits at
  `2026-08-02T07:29:15+00:00`.

### E-G2-017 - Native Encoded Long-Sequence Stability And Figures

- Status: `PASS` for exact scalar-oracle cross-check, artifact validation,
  and figure rendering; the frozen native-MXFP4
  engineering stability gate is `FAIL`.
- Commands and exit codes: `python -m scripts.verify_vectorized_encoded_oracle`,
  `python -m scripts.native_encoded_long_trace`,
  `python -m scripts.verify_native_encoded_long_trace`, and
  `python -m scripts.plot_long_sequence_stability`; all final attempts exit
  code `0`.
- Source revision and dirty-patch hashes: revision
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; vectorized-oracle patch
  `3FEBD71E0487100BA7B55FC35B1CDD84946B4013B25FE12045875F0344F74EDD`;
  native-run patch
  `12B72E49F5361F1AB289281D0A8C318870916BAB322C1F1371EC60FFA3968796`;
  plot patch
  `23379544C2367E1035AA5822FA5A4A590DFE5AB9CDD6BE227D2CEB089BE736EB`.
- Inputs/configuration/seeds/tools: seed `0xFB72`; 16 Q/K heads, 32 value
  heads, K=V=128, B32, and the required 64/256/1024/4096/8192 checkpoints.
  The input-stream SHA256 is
  `ADB9105CE36C702EEB5D72A52145AED951C55752E9A541BAFBB549E61679DF0E`;
  initial-state SHA256 is
  `CB92F5959750AB44FBB97A8AA7C416961CDE747284B54511A47CBAEA26F13D19`.
  Python is `3.12.10`, NumPy `2.3.5`, ReportLab `4.4.9`; PDF QA used the
  bundled Poppler renderer.
- Exact cross-check outputs/hashes: 64-token verification JSON
  `3542C7AD48EC4E4A322BBC889AE83887B14634B777ED0B46CB7B39FD12E05DAE`;
  log `462DADC82DBD245294A4F07DB5BB24D39A631F49099801666AD8E607F5EC1A5C`;
  frozen scalar/HLS trace
  `677A4C1673754AD7603EC05FBA4FFC7B5417B5763B293F69B5E798C1769659C0`.
  All 262,144 output mantissas, 262,144 output exponents, counters, 524,288
  final state elements, and 16,384 final scales match exactly.
- Long-run outputs/hashes: token CSV
  `06F7B5C7A21A52411E0B218AF3F63DD56F56A1798D74F144BE58E092E9EFBC9B`;
  checkpoint CSV
  `CAD02382EDE3F744CB0BDE36382A4268D8C37DDD3359A196A43D56C38FB60A32`;
  manifest
  `7595E7CAF2B6D2D85E50D6D26E7030B3CEE9CCE3FD1B73868183FFBDD5C3B24F`;
  verifier
  `D3399B314A7B6887A9E6ED61D86A42C3EBF137F0D2373A64459887A6DB521A7B`;
  run log
  `43DA759BDBCD3B1A4EC24D80A258D7BD5DF312C13BF5625CC8F6C118AA1A0548`;
  verifier log
  `13B4DD2D4CE32FC9B976A04E90A2730EDD6AE8FA4943D670B4CEA1F8B5A00F42`.
- Artifact validation: the verifier rehashes all inputs and outputs,
  checks all 8192 token rows and cumulative counter recurrences, proves each
  checkpoint is an exact canonical projection, recomputes every checkpoint
  metric, and validates six compressed complete-state snapshots.
- Result: at token 8192, output cosine is `0.429834`, output relative L2 is
  `2.589596`, state relative L2 is `2.580730`, and maximum state error is
  `1.110176`. Element saturation, accumulator saturation, and scale clamps are
  all zero; cumulative alignment underflows are `2,685,620,693`. The failure
  is not explained by clipping or overflow alone. Every native encoded token
  is below the plotted `0.99` cosine limit and above the `0.10` state-error
  limit, beginning at token 1; this diagnostic does not alter the frozen
  checkpoint rule.
- Figure outputs/hashes: output-cosine PDF
  `286F899026640235D8CCD60FEE97EDAF718510E747309C3BD4E27935DA3E026A`;
  state-error PDF
  `80C63ABDDA2A0FD31152AB6EF8EE6C0F15270FDB4711E21C8C6C16D5D9AAB698`;
  plot manifest
  `922D4FDECDC4FFE2046F3B14E97D8121E839780DF6F2027B3B899D55B578717F`.
  The combined paper-scale panel and current 220-dpi visual render are recorded
  separately in E-G7-004.
- Preserved interrupted attempt: the first native run used the wrong floating
  manifest field name in its bridge check and was stopped before token 4096.
  Its token-0/64/256/1024 snapshots and log are retained under
  `reports/benchmark/corrected/native_encoded_long_trace_attempt1_manifest_key_mismatch/`;
  they are not used as scientific evidence. Its token-64 arrays exactly match
  the completed run.
- Timestamps: exact cross-check
  `2026-08-02T04:40:57.765783+00:00`; native run
  `2026-08-02T05:28:18.841209+00:00`; independent verification
  `2026-08-02T05:28:31.507448+00:00`; current figures
  `2026-08-02T18:17:44.330208+00:00`.

### E-G2-018 - Final Guarded Python Regression

- Status: `PASS` for every executed test; two release-dependent tests are
  `NOT_RUN` through explicit pytest skips.
- Command and exit code: system Python with the bundled dependency path,
  `python -m pytest -p no:cacheprovider -q`, with JUnit written to
  `reports/test_results/full_current.xml`; exit code `0`.
- Source revision: `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe` with the dirty
  working tree frozen by the final source snapshot below.
- Tool/version/configuration: Python `3.12.10`, pytest `9.1.1`, NumPy `2.3.5`,
  repo-local temporary directories, and pytest cache disabled.
- Raw JUnit: `reports/test_results/full_current.xml`, SHA256
  `C46E7ADAE4A2721F2E9CC19B5FCD9E5E6AD5CD2BDE7B1FC7E3A4DE70F21E0424`.
- Result: 271 tests collected; 269 passed, 2 skipped, and 0 failed in 11.43
  seconds. The skips are the absent Phase 7 pack for the current revision and a
  generic legacy HLS co-simulation report that predates current HLS sources.
  The dedicated current-source 64-token direct RTL test executes and passes.
- Timestamp: `2026-08-03`.

### E-G2-019 - Machine-Checked Synthetic Trace Protocol

- Status: `PASS` for exact trace-family definitions and metric semantics.
- Requirement: bind every paper-facing synthetic distribution, seed, shape,
  checkpoint, initialization mode, and relative-L2 denominator floor to the
  executed generators instead of relying on narrative descriptions.
- Commands and exit codes: focused paper/protocol/source suite, exit code `0`
  with 47 passed; the same tests are included in E-G2-018.
- Source revision and dirty-patch identity: manifest header.
- Configuration: PCG64 via NumPy `default_rng`; one deterministic generator per
  token from seed, token index, and trace family; nominal development seed
  `0xFB72`; encoded-correction test seed blocks `0xA17E5EED`, `0xC4D3B2A1`, and
  `0x06E5A1D0`; nominal and high-retention alpha/beta ranges; normalized
  standard-normal q/k, value standard deviation `0.25`, random-state standard
  deviation `0.05`, zero-state mode, seed `0xFB72`, required checkpoints through
  8,192 tokens, and relative-L2 denominator floor `1e-12`.
- Raw paths/hashes: `docs/synthetic_trace_protocol.json`, SHA256
  `061C8CA381B3868FA6530636711F40E78E5067E43A550754B44D17FD647F9155`;
  protocol test source SHA256
  `8DA17718903B2F062CF19C0EE238389BFF84AE345C5E80602633029F8CDCB243`;
  focused JUnit SHA256
  `607E21207B615E42E2CF622FCF7AD4586126F95B894AAB8EAFD835C7072F5EEC`.
- Validation: tests monkeypatch the executed trace generators,
  derive observed distribution parameters and the metric denominator floor,
  and compare them with the protocol JSON.
- Result: manuscript distribution macros and metric definitions are generated
  from the checked protocol. The protocol remains synthetic and layer-level.
- Timestamp: `2026-08-02`.

## G3 Software Candidate Evidence Entries

### E-G3-001 - Exact Write-Log Equivalence And Development Freeze

- Status: `PASS` for exact software equivalence and development-only candidate
  freeze. Physical Pareto evidence is `NOT_RUN`.
- Requirement: prove exact recurrence equality, then select at most one
  quantized candidate without held-out tuning.
- Commands and exit codes: focused pytest on
  `tests/test_gdn_write_log.py tests/test_write_log_stability.py`, then
  `python -m scripts.select_write_log_candidate`; exit code `0`.
- Source Git revision and dirty-patch hash: manifest header. The selection JSON
  freezes hashes of every development checkpoint input used for selection.
- Inputs/configuration: development seed `0xFB72`; nominal prefixes through
  8192 tokens; exact and quantized modes at 16 Q/K heads, 32 value heads,
  K=V=128, B32; fixed R=4/8/16, precision, residual-stack, sparsity, and
  adaptive-policy development ablations.
- Tool versions: Python `3.12.10`, NumPy `2.3.5`, pytest `9.1.1`.
- Raw paths and hashes: selection
  `reports/benchmark/corrected/write_log_selection.json`, SHA256
  `522D3E2FEAE50E71EC38C80CD083383B84EEA2CD9667BDA5A06EB0546B391739`;
  selected development checkpoint CSV
  `FF126A4234CA7F3708781DD49BC3C69F0FEEAE508FA7F70B2F6FFADAB64E8D42`.
- Independent verification: exact tests compare capacities/folds directly with
  the independent FP64 oracle and exercise the additive sign, paired-head key
  sharing, per-head decay, pure decay, coefficient rebasing, atomic all-head
  folds, deterministic BF16 RNE, and no-drop behavior. The selector independently
  recomputes eligibility from development CSVs and requires exactly one point
  below the uniform-MXFP8 logical payload.
- Result: selected
  `mxfp4_rs2_act_rs2_sparse75_base_b32_mxfp8_log_fixed_b32_r7`, logical payload
  536,912 bytes, 48.796% below BF16 and 0.695% below uniform MXFP8-B32. These
  are logical values only.
- Timestamp: selection `2026-08-01T23:49:55.482326+00:00`.

### E-G3-002 - Frozen Nominal Held-Out Synthetic Gate

- Status: `PASS` for the preregistered nominal synthetic engineering gate only.
- Requirement: run the frozen selection once on three held-out seeds and both
  zero/random initial states through the five required lengths.
- Commands and exit codes: two invocations of
  `python -m scripts.run_selected_write_log_matrix` for random and zero initial
  states, then `python -m scripts.aggregate_write_log_held_out`; all exit code
  `0`.
- Source Git revision and dirty-patch hash: manifest header. The matrix/run
  manifests freeze the selection, source, input-stream, output, and verifier
  hashes at execution.
- Inputs/configuration: selection SHA256 from E-G3-001; held-out seeds
  `0xA11CE`, `0xC0FFEE`, `0x5EED5`; nominal family; random and zero initial
  states; 8192-token common prefixes; checkpoints 64/256/1024/4096/8192.
- Tool versions: Python `3.12.10`, NumPy `2.3.5`.
- Raw paths and hashes: random matrix
  `8636DB8AAF65663B28848E70E9FA72AA499CCAC3FE208590D5817A1877621084`;
  zero matrix
  `89B378613AF64C7EE9F1E78CC8DD8AAC53741A9E2B2090EB111914145E549C47`;
  aggregate manifest
  `5025F273F19ABD9EB601022E4290287718F1321EC07A31A4A3AF7335F61CF807`;
  summary CSV
  `AA6F38DA8DF39C8E89C1F647F9476BB2FAE37BFA9BAB61E44EAEC86C04848961`;
  checkpoint statistics CSV
  `E0043515BA0CD98DB7B4FBC508B770128176E680BCA18B3388AD72EECB407E2C`.
- Artifact validation: six run verifiers check exact row cardinality,
  hashes, required checkpoints, finite metrics, FP32 self-reference, fold/live
  invariants, logical storage, no drops, and the registered thresholds. The
  aggregate separately requires 30 checkpoint rows and six token-8192 rows.
  The statistical unit is the token-stream seed block; random and zero initial
  states are paired conditions, not six independent samples.
- Result: worst required-checkpoint cosine `0.994163`; worst token-8192 state
  relative L2 `0.098834`; zero dropped entries. Across all 49,152 candidate
  token rows, cosine minimum is `0.993407` and state-error maximum is `0.105004`.
- Timestamp: random matrix `2026-08-02T00:00:22.259569+00:00`; zero matrix
  `2026-08-02T00:09:30.439082+00:00`; aggregate manifest timestamp recorded in
  the raw JSON.

### E-G3-003 - Additional Development Stress Matrix

- Status: `FAIL`. This failed attempt is preserved and did not trigger retuning.
- Requirement: challenge the frozen candidate on additional synthetic trace
  families and both initial-state modes.
- Command and exit code: `python -m scripts.run_selected_write_log_matrix
  --split development --seeds 0xFB72 --families dynamic_range cancellation
  high_retention decay_sweep adversarial --initial-states random zero --tokens
  1024 --checkpoints 64 256 1024`; exit code `1` because the scientific matrix
  status is `FAIL`.
- Source revision/dirty-patch, configuration, and tools: E-G3-002 except split
  and family list above. Every run manifest contains its own input and source
  hashes.
- Raw path/hash: matrix manifest
  `reports/benchmark/corrected/write_log_development_stress_1024/matrix_manifest.json`,
  SHA256 `527EAA6F72195D0F98FA5B695BA0FB6B6EB4562D0E6640DC479692DEDC5A929B`;
  summary CSV SHA256
  `9D0875BF17919B40CC8901C8119010F3D59DEA183BA85FD2416C94D060815A47`.
- Artifact-validation result: each of ten runs has a separate verifier.
  Eight pass; random and zero high-retention runs fail. At token 1024 they reach
  cosine/state-error pairs `0.983090`/`0.185116` and
  `0.983534`/`0.185297`, respectively. All ten runs report zero drops.
- Timestamp: `2026-08-02T00:15:08.159041+00:00`.

### E-G3-004 - Held-Out Stability Figures

- Status: `PASS` for hash-validated vector generation and visual layout only.
- Requirement: generate paper-ready output-cosine and state-relative-L2 plots
  from three held-out token-stream seed blocks, each paired with random and zero
  initial state, with envelope and gate context.
- Commands and exit codes: `python -m scripts.plot_write_log_held_out`, then
  bundled Poppler `pdftoppm -png -r 180` for both outputs; exit code `0`.
- Source Git revision and dirty-patch hash: manifest header. The plot manifest
  records the plotting-source hash plus both matrix, selection, run-manifest,
  token-CSV, aggregate-CSV, and output hashes.
- Inputs/configuration/seeds/tools: E-G3-002; ReportLab `4.4.9`; bundled Poppler.
- Raw outputs: output cosine PDF SHA256
  `B337C2912CFF4CA4BF11840BAF534D074F9C03CE0ADB2D2FD8C26B11917C8940`;
  state-error PDF SHA256
  `147BA719A6E97E331D6DAA800AEBEAB5479106B918C768A39C725E16600879DD`;
  plot manifest SHA256
  `1D1366C238E9E10A9041169C789949A8CD17C07618F977C820E1E266D75E803C`.
- Artifact validation: the generator rejects any stale hash, non-PASS run,
  wrong variant, missing token, drop, or threshold regression. Both pages were
  rendered at 180 dpi and visually inspected for titles, exact candidate label,
  min/max envelope, mean, decision line, K-by-V orientation, relative-L2 floor,
  axes, clipping, overlap, fonts, margins, and complete 1-8192 coverage.
- Timestamp: plot manifest and rendered artifacts on `2026-08-02`.

### E-G3-005 - Encoded E2M0 Candidate Registration And Paired Test Conditions

- Status: `PASS` for the locally registered 1,024-token synthetic engineering
  gate and same-implementation deterministic recomputation check.
- Requirement: freeze one corrected encoded candidate and all executor/oracle
  hashes before local test-artifact generation; run three token-stream seed
  blocks with random and zero initial state as paired conditions; require every
  registered quality check and preregistered hard-event count to pass.
- Commands and exit codes: each run manifest records its
  `python -m scripts.e2m0_encoded_stability` command and exit code `0`; each
  verification records a full
  `python -m scripts.verify_e2m0_encoded_stability --recompute` deterministic
  recomputation; aggregate
  command `python -m scripts.aggregate_e2m0_encoded_held_out` exits `0`.
- Source revision and dirty-patch identity: recorded per run and verification;
  the local registration freezes four oracle/executor/verifier source hashes.
  It does not freeze the full dependency closure and has no external timestamp,
  so it does not independently establish chronology or absence of leakage.
- Configuration: candidate
  `mxfp4_rs2_act_e2m1_e2m0_state_mxfp4rs2_log_r7_q1_15_int32_guard5`,
  high-retention family, three token-stream seed blocks crossed with random and
  zero initial state (six paired conditions), 1,024 tokens, checkpoints
  64/256/1024, K-by-V state, B32 scales, R7, Q1.15, INT32, guard five.
- Tools: Python `3.12.10` and NumPy `2.3.5` as recorded in run manifests.
- Raw paths/hashes: registration
  `reports/benchmark/corrected/e2m0_encoded_preregistration.json`, SHA256
  `1C325E244A26F78598D8160B76104D3A8EDC75561742458CABE63FA43ACEAF5A`;
  aggregate
  `reports/benchmark/corrected/e2m0_encoded/held_out/held_out_summary.json`,
  SHA256
  `AE5E344B840DF8801178B402682CD0B1E003E0CB2F3894B8B7C3F8881ADD9920`.
- Validation: all six verification files record `recomputed=true` and bind the
  corresponding manifest hash. This is an integrity check using the same
  implementation, not an independent numerical oracle. The aggregate rechecks
  identities, separated token-stream/initial-state hashes, frozen source hashes,
  row counts, checkpoint projection, counters, quality, and recomputation status.
- Result: minimum all-token output cosine `0.994430`, maximum all-token state
  relative L2 `0.098653`, and zero element saturation, accumulator saturation,
  or scale-clamp events. This is layer-level synthetic evidence.
- Timestamp: aggregate `2026-08-02T17:51:40.910679+00:00`.

### E-G3-006 - Corrected-Candidate HLS C Simulation And Synthesis

- Status: `PASS` for source-locked extraction, arithmetic C simulation,
  64-token resident C simulation, and completed C synthesis. The HLS cost/II
  hypothesis is `FAIL`. At this 2026-08-02 extraction point, candidate RTL and
  physical evidence were `NOT_RUN`; later E-G5 entries supersede that status.
- Requirement: implement the frozen encoded candidate, preserve exact
  arithmetic/state snapshots, and compare it with matched BF16/uniform HLS
  evidence without transferring uniform RTL results.
- Commands and exit codes: Vitis HLS arithmetic, resident-smoke, trace C-sim,
  and C-synthesis TCL runs complete; raw logs are hashed by the summary.
  `python -m scripts.e2m0_hls_report` exits `0`.
- Source revision, dirty-patch hash, input hashes, configuration, and Vitis HLS
  `2025.2` version are recorded in
  `reports/csynth/corrected/e2m0_hls_summary.json`.
- Raw summary SHA256:
  `F9FFC69166F7C7C5579A7F6B8549C25AC221A5E98FF012786E6F86505897C984`.
  The 64-token trace C-sim log SHA256 is
  `FE6EC1008AB11CE078437673D7F2BA3ADDFEE3F04AA7B50835DB7C8AC3D68C88`.
- Validation: the report parser rechecks source freshness,
  explicit PASS markers, report metrics, loop constraints, matched controls,
  logical-byte calculations, and raw hashes. Focused parser/source tests pass.
- Result: estimated clock `3.108 ns`; `435,089` LUTs; max non-fold STEP
  `17,954,144` cycles; max amortized `39,947,365` HLS cycles per layer STEP;
  and a `153,952,544`-cycle maximum fold-command burst. The reported
  `3.108 ns` path misses the configured target-minus-uncertainty budget of
  `2.920 ns` by `0.188 ns`, although its reciprocal exceeds 200 MHz. Three
  explicit II=1 loops achieve II=2. Cost/II/timing-margin Pareto status is
  `FAIL`; HLS-inferred memory counts are not accepted as physical-fit evidence.
- Timestamp: summary `2026-08-02T17:51:40.561013+00:00`.

### E-G3-007 - Fully Recomputed 8,192-Token Corrected Development Traces

- Status: `PASS` for the preregistered extended synthetic development gate and
  full deterministic recomputation of both registered runs.
- Requirement: run the frozen corrected candidate for 8,192 high-retention
  tokens with random and zero initial state, then deterministically regenerate
  with the same implementation and compare every token and checkpoint field
  before aggregation.
- Commands and exit codes: two
  `python -m scripts.verify_e2m0_encoded_stability <manifest> --recompute`
  invocations, each exit code `0`; `python -m
  scripts.aggregate_e2m0_encoded_extended`, exit code `0`.
- Source revision and identity: revision
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; the aggregate rechecks all four
  preregistered oracle/executor/verifier hashes before accepting results.
- Configuration: candidate
  `mxfp4_rs2_act_e2m1_e2m0_state_mxfp4rs2_log_r7_q1_15_int32_guard5`, seed
  `0xFB72`, high-retention family, random and zero initial state, K-by-V state,
  B32 scales, checkpoints 64/256/1,024/4,096/8,192, R7, Q1.15, INT32, and five
  guard bits.
- Raw paths/hashes: random manifest
  `B64932AE3CDA303FFC65772D91C9BB186CADADC7659838A1DA61E502EB31B681`;
  random verification
  `1746CFBF2DF6A84D783159607FBDB9B408E1C2E22242809CD01A86E8DE2B7529`;
  zero manifest
  `7860EB0FAADE3A5E58CD4AE62F360458C58D71114336B88D44E252C8986F148D`;
  zero verification
  `0A1E73A6519A00D84CB0262704AB6C81D6B1CC1EBABB3C77455DDF6402A3BBFF`;
  aggregate `reports/benchmark/corrected/e2m0_encoded/extended_development/
  extended_summary.json`, SHA256
  `D876B11E3C43C008D34176196AE0B3BA1DA238260BE8922C42F06FD86D915051`.
- Validation: both verification JSON files bind the expected
  original manifest hash, report `recomputed=true`, and have empty failure
  lists. This is same-implementation artifact integrity, not an independent
  numerical oracle. The aggregate separately checks identities, source hashes,
  row counts, checkpoint projection, counters, gate status, and recomputation
  status.
- Result: minimum checkpoint cosine `0.995065`; minimum all-token cosine
  `0.994389`; maximum final state relative L2 `0.097472`; maximum all-token
  state relative L2 `0.099057`; maximum absolute state error `0.267635`; zero
  element saturations, accumulator saturations, or scale clamps. Across both
  runs, alignment underflows total `1,049,355,823`, deliberate E2M0 residual
  clips total `23,296,266`, and folds total `2,340`. The PASS is
  development-only layer-level synthetic evidence. The two initial-state modes
  share one token stream and do not estimate trace-population uncertainty.
- Timestamp: aggregate `2026-08-02T17:51:40.062508+00:00`.

### E-G5-001 - Corrected-Candidate Out-of-Context Implementation

- Status: `PASS` for route completion, physical fit, DRC extraction, and a
  timing-closed point; `FAIL` for the declared 250 MHz and secondary 200 MHz
  setup checks.
- Controlled boundary: the declared 36-slot corrected recurrence-state kernel
  on `xcu55c-fsvh2892-2L-e`, without a U55C shell, xclbin, or board run.
- Evidence: `reports/vivado/corrected/e2m0/e2m0_postroute_summary.json`, SHA256
  `E757DD4356ADF20F60E24AB6BF380E17640DF389472D587E4D29D2288E6AEF04`.
- Result: 208,523 CLB LUTs, 111,027 registers, 353 BRAM tiles, 624 URAMs,
  and 44 DSPs. The design fails setup at 250 and 200 MHz and first closes at
  the tested 180.18 MHz point. DRC reports 38 warnings, zero critical warnings,
  and zero errors. The 6.991 W result is a medium-confidence vectorless power
  estimate, not board energy.
- Timestamp: `2026-08-04T10:22:11.126987+00:00`.

### E-G5-002 - Matched Wider-Arithmetic Physical Baselines

- Status: `PASS` for native-MXFP8 HLS and routed evidence; `FAIL` for the
  unchanged all-layer BF16 physical-fit outcome.
- Evidence: native-MXFP8 HLS
  `reports/csynth/corrected/mxfp8_hls_summary.json`, SHA256
  `1EF6CB422542513C70838B5B9332073F9192B9498630E3FD6C55F70D9CE17657`;
  native-MXFP8 route
  `reports/vivado/baselines/mxfp8/mxfp8_vivado_summary.json`, SHA256
  `7BC8C936DC03D75BEB810AC61F30C7F58FDCBB6CDEE75CD3CA0B95384D93FD0D`;
  BF16 physical attempt
  `reports/vivado/baselines/bf16/bf16_vivado_summary.json`, SHA256
  `E477E43465AC3EB695BB8D7545B3525506173E958C8323CFE5F69A3ECB5A58E5`.
- Result: native E4M3/E8M0 passes bounded arithmetic C simulation, one exact
  persistent transition, C synthesis, and all explicit II=1 constraints. Its
  routed image fits at 58,582 LUTs and 576 URAMs, fails 250 MHz, and first
  closes at the tested 166.67 MHz point. The BF16 image completes synthesis but
  exceeds U55C memory capacity before placement; no smaller layout is
  substituted.
- Timestamps: MXFP8 HLS `2026-08-05T06:24:49.217212+00:00`; MXFP8 route
  `2026-08-05T18:01:47.232609+00:00`; BF16 attempt
  `2026-08-05T06:32:03.104535+00:00`.

### E-G5-003 - Corrected-Candidate RTL Completion Audit

- Status: `PARTIAL`; required 64-token corrected-candidate RTL parity is
  `NOT_ESTABLISHED`.
- Evidence:
  `reports/cosim/corrected/e2m0_trace64/e2m0_trace64_cosim_summary.json`,
  SHA256
  `538E7A615A3DCA00D2705D4C63D06B6CF6148F794C3E751F364B1AE4BCE5E20D`.
- Result: exact 64-token HLS C simulation passes. Two isolated official XSIM
  attempts exhaust host memory before transaction one. Verilator 5.050
  compiles the candidate generated RTL and completes one exact LOAD in
  4,797,322 cycles, but zero recurrent STEPs complete and zero output values
  are compared. Uniform-MXFP4 64-token RTL parity is not transferred.
- Timestamp: `2026-08-05T20:35:41.430837+00:00`.

### E-G5-004 - Short Model-Derived Qwen Recurrence Diagnostic

- Status: `PASS` for the bounded diagnostic; closed-loop and full-model quality
  remain unavailable.
- Evidence: `reports/benchmark/qwen_recurrent_stability_manifest.json`, SHA256
  `CA39E60BCE92D72C80D2772E63C23730D95C02816D9DF93E7A183ACC01CED117`.
- Result: matching pinned checkpoint projections reconstruct q, k, v, alpha,
  and beta for four layer-12 prompt traces totaling 60 valid tokens, with
  12--18 tokens per prompt. The comparison includes FP32, BF16, MXFP4-state,
  MXFP8-state, and flat INT4 floating-Q/DQ paths. It is not long-horizon,
  closed-loop, perplexity, or downstream-accuracy evidence.
- Timestamp: `2026-08-05T16:47:28.358031+00:00`.

### E-G7-002 - Corrected Paper Source Assets

- Status: `PASS` for source-asset generation and provenance validation;
  final-PDF status is `NOT_RUN`.
- Requirement: generate paper-facing values, tables, and macro snippets only
  from corrected evidence; validate figure hashes; prohibit paper PDF
  generation while any final gate is non-PASS.
- Command and exit code: `python -m scripts.corrected_paper_assets`, exit `0`.
- Source revision/dirty-patch and inputs: the asset manifest records the current
  revision and SHA256 for every accepted input, including the numerical
  contract, synthetic-trace protocol, preregistration, held-out and extended
  stability summaries, two full-shape supplemental stress traces, all-layer
  capacity lower bound, HLS summaries, and five verified figure PDFs. Release
  status is deliberately excluded from numerical asset generation. The
  generated `numbers.json` contains 295 traced values.
- Raw outputs/hashes: asset manifest
  `paper/corrected/asset_manifest.json`, SHA256
  `DD276D7009A7E0DB4549B3E9E56A8A0907D949DD417002AEC610173E2777FE3A`;
  numbers and provenance each SHA256
  `40AF897A38C78C79674797D49FBA8858244D287218BC3F0FE003E6ACF0768153`;
  manuscript source `paper/corrected/paper.tex`, SHA256
  `E9845A599C78F98EF40DDBD00013054E457049A8A944EDBF22B2616DF5D858D2`;
  result macros SHA256
  `3D3BE7E3C301FB90260D3E2069BBCA899F3859809C11195DCF4E07FFECAE73B4`;
  extended-results table SHA256
  `894F804599CDE5B4C9CF5D08FD0CD4FDE849E1CF0FC4949816DEC665B094BCD2`;
  controlled-HLS table SHA256
  `EDFDF6B993B18EBBB0688FC16D97F159E0E4A671E6D915BD56543F207A912E8D`;
  hierarchy-ablation table SHA256
  `B740AD529781D3218FA8E8676BA29DF7F8FB07C8191B8FD605CD241E8EAD41AB`;
  consolidated candidate-quality table SHA256
  `96A41D79CF2507B6F38291F99176703EC4D96403E47C9CD5D7B22FA1F16F74A3`.
- Validation: paper-asset, manuscript-macro, claim-language,
  source-snapshot, citation, final-gate, status-document, and
  replacement-summary tests pass. The decision-review focused suite reports
  35 passed, JUnit SHA256
  `4B8B57150808651DBC03F5F38F4CFE34D882B4AC77D89AA2D78BE23B88948784`;
  the complete suite reports 269 passed and two expected skips, JUnit SHA256
  `C46E7ADAE4A2721F2E9CC19B5FCD9E5E6AD5CD2BDE7B1FC7E3A4DE70F21E0424`.
  Existing plot PDFs are accepted only when their manifest hashes match.
- Result: evidence-backed LaTeX source exists; `paper_pdf_permitted=false`.
  No corrected manuscript PDF was generated.
- Timestamp: asset manifest `2026-08-04T01:32:59.724572+00:00`.

### E-G7-003 - Corrected Datapath Figure

- Status: `PASS` for evidence-backed vector generation and standalone visual
  inspection; final manuscript-page inspection remains `NOT_RUN`.
- Requirement: replace the invalidated architecture graphic with a legible
  two-column figure that identifies the inherited five-phase schedule, native
  MX arithmetic, corrected state representation, widths/rates, scale flow,
  logical STEP/output/state payload sizes, and periodic fold.
- Commands and exit codes: bundled Python
  `python -m scripts.corrected_datapath_figure`; bundled Poppler
  `pdftoppm -png -r 220 -singlefile`; `pdfinfo`; and
  `pytest tests/test_corrected_datapath_figure.py`; all exit code `0`.
- Source revision and dirty-patch identity: revision
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; source-specific dirty-patch
  SHA256
  `8EBEF0237830835F7543BC8FF2BFAF36E71FAA02F2760AC2CAB2794907ECDE18`.
  The manifest hashes the generator plus frozen corrected HLS top and header.
- Inputs/configuration/tools: all displayed numeric dimensions, widths,
  parallelism, block size, target clock, accumulator/guard widths, log
  capacity, and logical payload are read from
  `paper/corrected/numbers.json`; ReportLab `4.4.9`; bundled Poppler; one-page
  515.52-by-252-point PDF rendered at 220 dpi.
- Raw outputs/hashes: PDF
  `paper/figures/corrected/corrected_candidate_datapath.pdf`, SHA256
  `74904121BF4B59EDE16E6667069EE4D2764851F22B4F30121DF7BA87A19625ED`;
  manifest SHA256
  `4AC1D135C64F8DB49F6D77AB6470C66FE39C1A07FE063B5E4EC8178E3C78BBA9`;
  220-dpi audit render SHA256
  `146A7E2CDEDF385722F61F485C4B1DED4A098FD024F0D009E48A3A50B71E201A`
  at `docs/evidence/corrected_candidate_datapath_220dpi_20260803.png`.
- Independent verification: the unit test regenerates the PDF, checks its
  signature and page count, extracts required labels, rechecks every used value
  against corrected numbers, and verifies source identity. Visual inspection
  confirms legible text, complete arrows, no clipping or overlap, a clear
  legend, and an explicit logical-not-physical qualification.
- Timestamp: `2026-08-03T17:50:07.173392+00:00`.

### E-G7-004 - Paper-Scale Long-Sequence Stability Panel

- Status: `PASS` for verified panel generation and standalone visual
  inspection; final manuscript-page inspection remains `NOT_RUN`.
- Requirement: preserve the full-resolution output-cosine and state-error
  plots while providing a legible full-width paper panel for the central
  8,192-token synthetic comparison.
- Commands and exit codes: bundled Python
  `python -m scripts.corrected_long_trace_panel`; bundled Poppler
  `pdftoppm -png -r 220 -singlefile`; and
  `pytest tests/test_corrected_long_trace_panel.py`; all exit code `0`.
- Source revision and dirty-patch identity: revision
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; source-specific dirty-patch
  SHA256
  `E53E3A552BF118C698B8826D807E7521D92DD5226AA9478A0DFD8EF79D5E16DF`.
- Inputs/configuration/tools: the generator accepts only the PASS
  `long_trace_plot_manifest.json`, rechecks both source CSV hashes, and uses
  the identical six plotted variants and metric definitions; ReportLab
  `4.4.9`; bundled Poppler; one-page full-width vector PDF rendered at 220 dpi.
- Raw outputs/hashes: PDF
  `paper/figures/corrected/long_sequence_stability_panel.pdf`, SHA256
  `E28205DA2DD32559C9B90A625AB2FD4A46DD2F6362388ECCCCCF09039BF20B70`;
  manifest SHA256
  `5E07BFD160550EE0B389A3048BBD1C84E9417CF2E8BE31845E11BFF9E2F96D9C`;
  220-dpi audit render SHA256
  `18CFBF14F10B747D68B8A0DC75558AB52453E98C2A819D7951401DE6BC898CB8`
  at `docs/evidence/long_sequence_drift_panel_220dpi_20260802.png`.
- Validation: the unit test regenerates the panel, validates
  source hashes, PDF signature, page count, required labels, output hash, and
  source identity. Visual inspection confirms readable legends/ticks,
  foreground threshold labels, distinct series, no overlap or clipping, and
  accurate left/right metric assignment. The title says ``drift,'' not
  ``stability,'' and floating Q/DQ is visually distinct from native encoded
  MXFP4.
- Timestamp: panel manifest `2026-08-02T18:17:45.346803+00:00`.

### E-G7-005 - Staged Release, Venue, and Citation Safeguards

- Status: `PASS` for source-level venue, citation, provenance, and release
  enforcement; reviewer-complete PDF status remains `NOT_RUN`.
- Requirement: bind venue constraints and cited implementation constants to
  inspectable sources, require all reviewer rows to pass against a final PDF,
  and prevent both PDF and submission-pack creation while any final gate is
  non-PASS.
- Commands and exit codes: `python -m scripts.reviewer_traceability_status`,
  expected exit code `1`; `python -m scripts.build_corrected_paper`, expected
  exit code `1`; and `python -m scripts.paper_pack`, expected exit code `1`.
  All three guards stop before producing a release artifact.
- Raw paths/hashes: venue record
  `docs/venue_requirements_2026_08_02.md`, SHA256
  `E0D07B44BB6928B1A3E843AF2ED69196299A8C186F4023009C1ACA0962073C95`;
  citation audit `docs/evidence/citation_archival_audit_2026_08_03_v3.csv`, SHA256
  `8E44CE1AE4C826B1ED88EF504085E8C45A8CAA786EFBDC1036D12AB0C4E8EDA3`;
  citation audit note `docs/evidence/citation_archival_audit_2026_08_03_v3.md`,
  SHA256
  `6162E4D3F5FCFE7ED58FABFC9DD34FF9274A433B1B429D533C2B61DF9AA6CB95`;
  reviewer status `docs/reviewer_traceability_status.json`, SHA256
  `B0A04FD6B6882B9E51AEBC4C376C5A28E3FFE9EC3D57EB49328C10F784155B69`.
  Current blocked-build and blocked-pack log SHA256 values are
  `4EE75937C79FB296FB795DB2432ED7B27468C730C7892E021711028659D0312E`
  and
  `3F532280F64B569A7E125222A34B8703E359437FF8528F97818BF2B04635A402`.
- Validation: tests enforce the venue source, pinned official
  Qwen model revision, bibliography first-use order, generated-measurement
  macros, reviewer-status vocabulary, and all-PASS-only release rule.
- Result: the source is auditable, but no corrected paper PDF or submission ZIP
  exists because the final completion gate is not all-PASS.
- Timestamp: reviewer status `2026-08-04T01:33:40.777704+00:00`; current build
  and pack guards were last confirmed on `2026-08-02`.

### E-G7-006 - Decision-Review Response Matrix

- Status: `PASS` for complete source-level mapping; final reviewer remediation
  remains `NOT_RUN` until a permitted paper PDF is audited.
- Requirement: map every numbered concern in the three cleaned decision reviews
  without altering the authoritative 68-comment workbook ledger or treating a
  prose edit as missing experimental evidence.
- Raw path/hash: `docs/decision_review_response.md`, SHA256
  `C224371C4119DC19C47D617815278CA00B99046A3435A8545CDA04353C698E9E`.
- Validation: `tests/test_decision_review_response.py` requires all 29 unique
  decision-review IDs and the exact evidence-status distribution: 19 `PASS`,
  one `FAIL`, three `NOT_RUN`, and six `BLOCKED_EXTERNAL`. The focused suite
  containing that test and the refreshed citation audit reports 35 passed with
  JUnit SHA256
  `4B8B57150808651DBC03F5F38F4CFE34D882B4AC77D89AA2D78BE23B88948784`.
- Result: novelty attribution, method explanation, figure readability,
  quantization boundaries, reference metadata, nominal plus controlled-stress
  drift reporting, and source-level scalability are answered. Native MXFP8 hardware, closed-loop
  model quality, physical fit, board energy, and same-boundary GPU evidence
  remain nonpassing.
- Timestamp: `2026-08-03`.

### E-G7-007 - Storage/Quality/HLS Trade-Off Figure

- Status: `PASS` for evidence-backed vector generation and standalone visual
  inspection; a complete measured Pareto frontier remains unavailable.
- Requirement: answer the requested memory/performance/accuracy view without
  combining logical storage, floating Q/DQ, native HLS, physical fit, or energy
  as if they were one evidence level.
- Command and exit code: `python -m scripts.tradeoff_evidence_figure`, exit `0`;
  bundled Poppler render at 220 dpi, exit `0`; focused figure test, exit `0`.
- Source revision/dirty-patch identity: revision
  `bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe`; source-specific dirty-patch
  SHA256
  `02B1FD98401A99834AE54DF3C3A9302DDA2C6DAC92ECEE037EA44F2B0ED0FEBF`.
- Inputs: PASS all-layer logical-capacity report, verified floating and native
  token-8,192 checkpoints, and the fixed-geometry HLS comparison. The generator
  rechecks both checkpoint-manifest hashes and requires matching layer counts.
- Raw outputs/hashes: `paper/figures/corrected/tradeoff_evidence.pdf`, SHA256
  `0863C26569A99799B8A73704827496ACCA5F900266F937F563AE69B4F5EA49BF`;
  manifest SHA256
  `434D5212462D86AA5649AC78614224B7084E02AD6F92C348EF887D6CAFE4D94E`;
  220-dpi audit render SHA256
  `DF4C54DC265EB38C347B7B3A75F436BC34A2C116985AF764F7208B180151EF03`
  at `docs/evidence/tradeoff_evidence_220dpi_20260803.png`.
- Validation: the figure test checks source hashes, PDF signature and page
  count, required labels, exact displayed values, source identity, and that HLS
  values exist only for BF16 and native MXFP4. Visual inspection confirms no
  clipping, overlaps, illegible labels, or imputed not-run bars.
- Timestamp: `2026-08-03T17:47:18.247329+00:00`.

### E-G7-008 - Full-Shape Synthetic Range and Cancellation Stress

- Status: `PASS` for deterministic artifact validation; BF16 passes both
  full-trace diagnostics and every low-precision comparator fails at least one.
- Requirement: test whether the nominal arithmetic ranking survives controlled
  exponent cycling and alternating-sign cancellation through 8,192 tokens at
  the unchanged 32/16-head, K=V=128, B32 recurrence-core geometry.
- Commands and exit codes: two `python -m scripts.long_sequence_stability
  --tokens 8192` executions with `--trace-family dynamic_range` and
  `--trace-family cancellation`, then `python -m
  scripts.aggregate_long_trace_stress`; all exit `0`.
- Dynamic-range outputs/hashes: token CSV
  `501BE9CA33CCC2B743531FDCDA60C429FA95FD4ED6964E1C00C93E55C11AECCD`;
  checkpoint CSV
  `E91F994A7565DDD1EA5006CD261CA89871599C1382B23799155559DE6EDDBB1A`;
  manifest
  `A0DAA859153443D2C0EC7577B07CD69BFC14A3C040A887CE1EFC11A189521107`.
- Cancellation outputs/hashes: token CSV
  `5E85652C3B33D4F3E333E0A86EA4B6E3562C67C5D76C6D75E12AF3A4D4214FCA`;
  checkpoint CSV
  `F635FC0509C25F84710256320962BBDF11B4E1BFB0527269271976FF4B32982C`;
  manifest
  `7F1D7F7F136DF31530B23831D1CB289C2EC6163CC388F8A0E2F97ACE2DE746C7`.
- Aggregate outputs/hashes: summary CSV
  `62B55A7BAF51F9DEA4A5F393A956E6468340BB7BD4E839BF6162F18D58869C3C`;
  Markdown report
  `6F565374AB445AA42AB8BB10CF19B55A23FCE684742CEFE203726A857E01DCDC`;
  manifest
  `1F0315E79A237775889DB4D3617A98F038F1CF4C5853F5F8379F281B48416521`.
  Aggregator source SHA256 is
  `5509C873BFE432185D41C6E42679DAC9ED9BBCFC85FEBA8258F9E7449649802D`.
- Validation: the aggregator checks 81,920 unique token rows, 50 exact
  checkpoint projections, commands, seed, geometry, method grid, FP32
  identity, event-status boundaries, source hashes, and output hashes. Three
  focused aggregator tests pass inside the 33-test reviewer suite; the complete
  suite reports 269 passes and two expected skips.
- Result: at token 8,192, dynamic-range BF16/MXFP4/MXFP8-state cosine and state
  relative L2 are `0.999875/0.016476`, `0.410379/26.772181`, and
  `0.698070/2.314652`; cancellation values are `0.999997/0.008844`,
  `0.981307/1.667123`, and `0.997011/0.255859`. MXFP8 remains the best
  low-precision comparator but does not meet the state criterion.
- Limitation: these are synthetic floating-Q/DQ stressors, not native encoded
  event evidence, fitted activation distributions, or closed-loop model
  quality. The real-activation reviewer concern remains `BLOCKED_EXTERNAL`.
- Timestamp: aggregate `2026-08-04T00:34:09.558272+00:00`.

## Final Completion Evidence

### E-G7-001 - Machine-Readable Final Completion Gate

- Status: `FAIL`; release state `NOT PAPER READY`.
- Requirement: evaluate every final completion requirement using only
  `PASS`, `FAIL`, `NOT_RUN`, or `BLOCKED_EXTERNAL`, and prohibit final PDF
  release unless every requirement is `PASS`.
- Command and exit code: `python -m scripts.final_completion_gate`; expected
  exit code `1` while the release is blocked. The current focused paper/source
  suite returns exit code `0` with 35 passed, and the complete suite returns
  exit code `0` with 269 passed and two expected skips. A guarded `python -m
  scripts.paper_pack` invocation also returns exit code `1` before producing
  an archive.
- Source Git revision and dirty-patch hash: manifest header.
- Input/configuration: eleven mandatory completion gates transcribed from the
  authoritative remediation directive, with evidence paths and nested HLS
  C/RTL statuses.
- Tool versions: Python `3.12.10`, pytest `9.1.1`.
- Raw paths and hashes: `reports/final_completion_gate.json`, SHA256
  `75440E1B728F96B8021C31F3622BB6B25B5D2F8ED3023E37726E7FB5E2AABF50`;
  `docs/final_completion_gate.md`, SHA256
  `916293B9F5C7766931DC980449FF9462DC3FBE4DCAABF8DE0ABBB77A5E53EB41`;
  focused paper/source-test JUnit
  `4B8B57150808651DBC03F5F38F4CFE34D882B4AC77D89AA2D78BE23B88948784`;
  full-suite JUnit
  `C46E7ADAE4A2721F2E9CC19B5FCD9E5E6AD5CD2BDE7B1FC7E3A4DE70F21E0424`;
  blocked paper-pack log
  `3F532280F64B569A7E125222A34B8703E359437FF8528F97818BF2B04635A402`.
- Validation: `tests/test_final_completion_gate.py` proves that
  the current statuses block PDF release, all-PASS is the only ready state,
  and unknown status labels are rejected.
- Result: 3 of 11 gates pass; one fails, five are unrun, and two are externally
  blocked;
  `paper_pdf_permitted` is `false`, and `paper/pack/` contains no generated
  submission archive.
- Timestamp: gate `2026-08-04T01:33:44.428746+00:00`.

## Non-Passing Evidence Requirements

| Requirement | Status | Reason / expected raw evidence |
|---|---|---|
| Final reviewer remediation | NOT_RUN | The release-after-review policy is recorded, but all 68 rows must later be verified against an evidence-supported final PDF. |
| Uniform-state synthetic candidate gate | FAIL | Uniform MXFP4, MXFP8-state fallback, flat INT4, and all six scale policies fail the nominal development thresholds. |
| Corrected-candidate test-set high-retention quality | PASS | Three token-stream seed blocks crossed with random and zero initial state (six paired conditions) pass the locally registered quality and three-hard-counter gate; same-implementation deterministic recomputation passes artifact-integrity checks. |
| Corrected-candidate extended 8,192-token quality | PASS | The random- and zero-initialized development conditions share one token stream and pass the frozen synthetic gate plus same-implementation deterministic recomputation; they do not estimate trace-population uncertainty. |
| Legacy Vitis-wrapper one-token RTL smoke | FAIL | The preserved UVM-wrapper attempt exhausts XSIM memory after 3 of 15 transactions, before the first valid recurrent STEP completes. |
| Current-source direct one-token RTL smoke | PASS | The bounded direct AXI harness completes RESET, STEP, and READBACK against current generated Verilog with exact selected checks. |
| Uniform-MXFP4 required 64-token RTL parity | PASS | All outputs/counters and complete final state/scales/status/generation match in the archived direct generated-Verilog run. |
| Corrected-candidate 64-token HLS C parity | PASS | All outputs, counters, folds, and final snapshot match the independent encoded trace. |
| Corrected-candidate 64-token RTL parity | NOT_RUN | The uniform-MXFP4 generated-Verilog result cannot validate the changed design. |
| Uniform MXFP4 versus matched BF16 HLS cost | FAIL | At the same boundary and 2.920 ns estimate, uniform MXFP4 uses 1.636x BF16 LUTs and 1.437x BF16 maximum STEP cycles. |
| Uniform MXFP4 energy advantage | NOT_RUN | No matched post-route or measured-board energy result exists. |
| Model-wide MXFP4 physical state-bank fit | NOT_RUN | Logical-capacity lower bounds pass for MXFP4, but allocation, banking, replication, ports, scratch, SLR placement, and post-route fit are unmeasured. |
| Closed-loop Qwen quality | BLOCKED_EXTERNAL | Approved model/data acquisition and adequate compute required. |
| Selected method Pareto result | FAIL | Corrected synthetic quality and the raw reciprocal 200 MHz check pass, but the configured target-minus-uncertainty timing margin, HLS LUT/STEP cost, and explicit II=1 criteria fail; allocated physical memory, average/p99 latency, and energy remain `NOT_RUN`. |
| All-layer physical state fit | NOT_RUN | Post-route BRAM/URAM allocation, banking, SLR, and service-rate reports required. |
| Timing and DRC | NOT_RUN | Corrected post-route timing summary and clean DRC report required. |
| U55C board parity and energy | BLOCKED_EXTERNAL | Board/XRT logs, bitstream hash, telemetry time series, and parity trace required. |
| Corrected paper source provenance | PASS | Generated numbers, provenance, tables, macros, and hash-checked plot references exist. |
| Final paper PDF audit | NOT_RUN | PDF generation, build log, page renders, and visual audit are prohibited until every upstream gate passes. |

## Current RS2/R3 Addendum (2026-08-09)

This addendum supersedes earlier current-status statements about the corrected
candidate, test totals, tool availability, and release state. Earlier entries
remain historical evidence and are not silently rewritten.

### E-G7-009 - Frozen Long-Trace RS2/R3 Stability

- Status: `PASS` for the preregistered layer-level synthetic gate.
- Evidence: `reports/benchmark/corrected/rs2_encoded/rs2_encoded_candidate_summary.json`,
  SHA256 `DE2E8A7873E21CC2DF31B1104115A6A8167C07B6A3979F7561520C12FC80A3A3`.
- Result: six held-out 1,024-token runs and two development 8,192-token runs
  pass the registered cosine, state-relative-L2, max-error, and hard-event
  criteria. The worst all-token state relative L2 is `0.082666` held out and
  `0.082737` extended; minimum all-token output cosine is `0.996099` and
  `0.995974`, respectively. Accumulator, element, and scale-clamp events are
  zero.
- Boundary: synthetic one-layer encoded-integer evidence only; it is not
  perplexity, downstream-task, or closed-loop model evidence.

### E-G7-010 - Current HLS and Generated-RTL Evidence

- HLS summary: `reports/csynth/corrected/rs2_hls_summary.json`, SHA256
  `9E780192929DFD2A8947AED9C0081BA93F4BC672C36BA8E7318271B0FD42CA5B`.
  Exact 64-token C simulation, arithmetic C simulation, resident smoke, and all
  explicitly targeted `II=1` loops pass. The selected HLS result is 167,082
  LUTs, 73,831 FFs, 74 BRAM18Ks, 88 URAMs, 26 DSPs, 13,522,144 maximum STEP
  cycles, and 43,065,280 amortized cycles.
- Matched result: the corrected candidate uses `1.958x` BF16 LUTs, `3.200x`
  BF16 maximum non-fold STEP cycles, and `10.191x` BF16 amortized cycles.
  Therefore the HLS cost/latency advantage is `FAIL`, despite a `0.550x`
  logical-state-byte ratio.
- Full direct generated-RTL trace: `reports/cosim/corrected/rs2_current/trace64_direct/rs2_trace64_direct_summary.json`,
  SHA256 `BA6B553B612A0BBD941DD14E22E45191318F7384C7B296E19BF9914970087926`.
  The same generated Verilog passes 66 commands, 262,144 output values,
  counters, and final recurrent state exactly.
- Official XSim runtime bound: `reports/cosim/corrected/rs2_current/xsim_runtime/rs2_xsim_runtime.json`,
  SHA256 `26222F4605E5CA788E3A18BD165271C332888CA4C0E697B9759D0ADBAC9F22A0`;
  generator SHA256 `C80B8F9BC62E2CE7A8B48A4249C4B4EC5FF301BB0EBECC1D75A7AB1C860214F4`.
  A random-state LOAD completes 4,447,475 cycles in 502 seconds. Applying that
  measured rate to the known 2,875,491,178-cycle trace projects 90.157 hours.
  This is runtime evidence, not official 64-token XSim parity; that item remains
  `NOT_RUN`.
- Rejected optimization: the packed-register experiment is archived under
  `reports/csynth/experiments/rs2_pack_registers_20260809/` with README SHA256
  `F29E182F154E70814944CB129BF9239E0118A2130C6BA09D48CEEE3E12290962`.
  It saved only 370 LUTs (`0.22%`) while adding 28 FFs and changing neither
  latency nor estimated Fmax, so the selected source was restored unchanged.

### E-G7-011 - Current Physical Evidence

- Evidence: `reports/vivado/corrected/rs2_current/rs2_vivado_summary.json`,
  SHA256 `CFAEE3EF46C4A635A7D6ADB3BCB7C84B1E290120348BBC2B187938BB94AED256`.
- Result: all 36 logical state slots fit in the U55C out-of-context kernel. DRC
  has 26 warnings, zero critical warnings, and zero errors. The first passing
  tested fixed-route point is 166.67 MHz with 0.264 ns WNS; 250 MHz remains
  `FAIL`.
- Five post-route repair attempts are recorded. General Explore and
  AggressiveExplore both improve the original -1.736 ns WNS to -1.690 ns but
  do not close timing; the best remains -1.656 ns from the fanout/retiming
  attempts. The AggressiveExplore raw timing SHA256 is
  `550814185D22B2757CCBE3785E8B54BA0BA8F613379D6A1A1A3C0641C3DE37E9`.
- The 5.242 W result is a vectorless estimate at 6.0 ns, not measured board
  power or energy per token.

### E-G7-012 - External Asset and Hardware Audit

- Local hardware/tool audit:
  `reports/environment/hardware_availability.json`, SHA256
  `23C34ACFE928318315A93E75AD5DA3C68107ED713B6C44BA662DF220BEA83325`.
  Vitis HLS, Vivado, Vitis compiler, platforminfo, and XSim are installed. No
  attached U55C, U55C XRT platform, `xbutil`/`xrt-smi`, xclbin, or telemetry
  interface is present. The detected RTX 3070 lacks native FP4 support.
- Public model/data audit:
  `reports/environment/qwen_public_asset_audit.json`, SHA256
  `FCBF7E8FC1435D77FE037FAE7C08CE1742077D5D60BA6D9C6375C4429167A6D1`;
  generator SHA256 `A197A18060889E2735D3DDFFB8D37D0EE8FD2F7FDB6F753524AB0CFF034FB6EB`.
  Four bounded Hugging Face API searches return 100 dataset records, no usable
  Qwen3-Next recurrent activation capture, and only 80B-class official
  Qwen3-Next models. Closed-loop quality remains `BLOCKED_EXTERNAL`.

### E-G7-013 - Working Draft, Regression, and Release Guard

- Working draft PDF: `paper/corrected/mxfp4_gdn_working_draft.pdf`, SHA256
  `BA4A00C42B78F3C15A90349D3D1A1D2215CF9E54C80588D03C7E5945577316C0`.
  Build-manifest SHA256 is
  `8D21613C34D6E2028E1BC443688D9A9BF67B02728A605ECF308B0FCC67BE61C7`;
  page-by-page visual-audit SHA256 is
  `7500F8AD8350C89C0FC889E0D6596E0D03C2F818B9129CDBC99E4CEBF1C9D4EB`.
  All nine 220-DPI page renders pass checks for text, equations, figures,
  legends, tables, captions, references, margins, and clipping. The PDF is
  visibly watermarked and not submission eligible.
- Full regression: 359 passed, two intentional skips, zero failures; JUnit
  `reports/test_results/final_pytest_20260809.xml`, SHA256
  `8A1487EAB084BF1393802560FEB41C40CE4A82CBD45DCEAF39E6BD7106A56E50`.
  The skips preserve the stale legacy HLS-cosim boundary and prohibit a Phase-7
  pack while the release gate is nonpassing.
- Final gate: `reports/final_completion_gate.json`, SHA256
  `591E5F8E3FF16E787E1491DD510128EA9F080B6F7ABE1652DAC22E99D1164A52`;
  Markdown SHA256
  `6507527F05649AEE24AB9C49EE3B9E59F84B83B88835E4657CCDE7E755AF72B8`.
  Four of eleven release gates pass. Official full-trace XSim is `NOT_RUN`;
  closed-loop model quality and board measurements are `BLOCKED_EXTERNAL`;
  selected-method Pareto advantage and 250 MHz timing are `FAIL`. Reviewer
  rows are source-mapped, but the unwatermarked audit and submission pack remain
  intentionally prohibited until all upstream gates pass.

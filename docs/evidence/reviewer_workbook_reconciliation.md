# Reviewer Workbook Reconciliation

- Timestamp (UTC): `2026-08-01T20:32:24.629729Z`
- Preserved source: `legacy/reviewer_sources/overleaf-comments-2026-06-18.xlsx`
- Source SHA256: `C4A70E704BEBDC8126540B2FEEBB25A26FA3672DBE79F9AE08157E27FDA7E54E`
- Source size: `138359` bytes
- Worksheet/table: `Comments!A1:H94`
- Artifact-tool extraction: `docs/evidence/reviewer_workbook_artifact_tool_values.json`
- Artifact extraction SHA256: `1D0C633198BB4C69E0AB1689B721B32E76DB570D099ABFAAFEEFC4A5B5C1B6BC`
- Independent verification: Python standard-library ZIP/XML parse matched the artifact-tool 94x8 semantic value matrix after canonicalizing empty-string cells to null.
- Raw exported message rows: `93`
- Distinct thread/reply message keys: `72`
- Distinct reviewer messages: `68`
- Distinct author messages excluded from reviewer ledger: `4`
- Exact duplicate extra rows: `20`
- Additional same-message variant rows: `1`
- Reconciliation result: `PASS`

The 67-topic derivative note is not a one-row-per-source-message export. It splits two multi-part reviewer messages and combines three comment pairs. The authoritative ledger therefore contains 68 rows, one for each distinct `jason.blocklove` thread/reply message. Duplicate exporter rows are retained in the raw CSV and referenced by row number.

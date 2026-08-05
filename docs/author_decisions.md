# Author Decisions

Decision date: `2026-08-01`

Source: the author instructed Codex to "keep going till paper ready" after the
three pending choices were presented explicitly.

| Decision | Selection | Status | Consequence |
|---|---|---|---|
| Pinned open-source parity runtime | Proceed with installation | PASS | PyTorch/Transformers/FLA operator parity may run locally; this does not authorize an 80B checkpoint download. |
| Post-failure G3 direction | Pursue the residual/write-log candidate | PASS | Prove exact equivalence and software Pareto value before any candidate-specific HLS work. |
| Paper research question | Controlled MXFP4-for-BF16 arithmetic replacement | PASS | Hold the recurrence, persistent-state layout, five-phase dataflow, U55C target, block size, P_K, and P_V fixed; judge cost and long-sequence recurrent stability. |
| Architecture novelty | Treat persistent state and five phases as inherited | PASS | Attribute both to Gupta et al.; do not present them as contributions. |
| Write-log role | Secondary mitigation, not headline novelty | PASS | Report it only with explicit constituent prior art and only at the evidence level actually completed. |
| Artifact wording | Release after review, subject to venue anonymity rules | PASS | The future paper may promise release after review; no repository is published during anonymous review. |

The instruction does not authorize paid compute, licensed-tool installation,
an 80B model/dataset download, FPGA programming, or a multi-hour synthesis
sweep. Those resource decisions remain separate.

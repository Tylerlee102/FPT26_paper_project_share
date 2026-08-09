# Native MXFP4 Gated DeltaNet FPGA Recurrence Core

FPGA research artifact for a controlled arithmetic-replacement study:
can native OCP MXFP4-B32 replace BF16-style arithmetic in the same
persistent-state Gated DeltaNet recurrence core while reducing FPGA cost and
retaining long-sequence recurrent-state stability?

Current release state: **NOT PAPER READY**. The corrected evidence answers no
for the current implementation. Uniform MXFP4 drifts substantially relative to
FP32, while BF16 passes the frozen 8,192-token synthetic stability gate. The
registered two-term E2M1/E8M0 state and token path with a three-entry write log
(RS2/R3) passes six held-out 1,024-token traces and two 8,192-token development
traces. Across the long traces, its minimum all-token output cosine is 0.995974
and its maximum all-token state relative L2 error is 0.082737, with zero element
saturations, accumulator saturations, or scale clamps.

RS2/R3 is a recurrence-aware mitigation rather than the controlled uniform
replacement. It stores 576,912 logical bytes per layer, but the matched HLS
estimate uses more LUTs and cycles than BF16. Its all-layer recurrence-state
bank routes on the U55C out of context and first passes the tested fixed-route
sweep at 166.67 MHz, not the declared 250 MHz target. Power is vectorless;
closed-loop model quality, physical board parity, and measured energy remain
unavailable.

Persistent on-chip state and the five-phase pipeline are inherited baseline
dataflow, not novelty claims. See `docs/implementation_status.md` and
`reports/final_completion_gate.json` before using any result.

## Repository Contents

- `golden/`: FP32, MXFP4, and INT4 software references plus deterministic vector generation.
- `hls/`: Vitis HLS C++ source, headers, testbenches, and Tcl entry points.
- `scripts/`: calibration, HLS/Vivado launchers, benchmark extraction, and paper artifact generation.
- `tests/`: reproducibility and provenance tests.
- `reports/`: raw and independently verified corrected evidence, plus preserved
  legacy reports outside the `corrected/` subtrees.
- `paper/`: preserved legacy artifacts plus evidence-backed corrected LaTeX,
  generated numbers/provenance, tables, and figures under `paper/corrected/`
  and `paper/figures/corrected/`.
- `vivado/`: Vivado Tcl and timing constraints.

## Quick Start

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m scripts.aggregate_rs2_encoded_candidate --require-extended
python -m scripts.rs2_hls_report
python -m scripts.rs2_vivado_report
python -m scripts.final_completion_gate
```

The completion-gate command currently exits nonzero by design because required
paper evidence is failed, unrun, or externally blocked. Consult its JSON output
instead of treating that expected exit as an infrastructure failure.

To regenerate deterministic base vectors on Windows without `make`:

```powershell
python -m golden.calibrate
python -m golden.vectors --kind synthetic --count 16 --output-dir data/vectors
```

## Corrected Evidence

The corrected software evidence can be checked with:

```powershell
python -m pytest
python -m scripts.verify_official_parity
python -m scripts.aggregate_rs2_encoded_candidate --require-extended
python -m scripts.rs2_hls_report
python -m scripts.rs2_vivado_report
python -m scripts.rs2_paper_assets
python -m scripts.build_working_draft
python -m scripts.final_completion_gate
```

`paper/numbers.json`, `paper/provenance.json`, the existing manuscript PDFs,
and the legacy paper-pack outputs predate the corrected recurrence and kernel
boundary. They remain preserved for auditability and are not current evidence.
Current source assets live under `paper/corrected/`; their manifest verifies
the corrected figure hashes and records source identity. The working-draft
builder produces a visibly watermarked, non-submission PDF even while release
gates remain open. Canonical PDF handling is staged to avoid a circular or
premature release. After all experimental and hardware gates pass,
`python -m scripts.build_corrected_paper` (or
`make corrected-paper-audit`) may create only
`paper/corrected/paper_audit_candidate.pdf`, which is explicitly ineligible
for submission. Rendered pages and a page checklist are validated by
`python -m scripts.record_paper_visual_audit`. Only after all eleven completion
gates pass may `python -m scripts.finalize_corrected_paper` (or
`make corrected-paper-pdf`) copy those exact audited bytes to the final PDF.
`python -m scripts.paper_pack` then packages corrected canonical numbers,
source, figures, reports, audit evidence, and the final PDF. The current gate
blocks every canonical PDF stage.

## Toolchain Scope

Regenerating HLS and post-implementation Vivado evidence requires AMD/Xilinx
Vitis HLS and Vivado for the Alveo U55C target (`xcu55c-fsvh2892-2L-e`):

```powershell
make hls-csim
make hls-csynth
make hls-cosim
make vivado-synth
make vivado-impl
```

The scripts search common Xilinx installation locations. If the tools are
installed elsewhere, set the relevant executable paths or adapt
`scripts/xilinx_tools.py`.

## Data Availability

The corrected long-sequence study uses deterministic synthetic vectors so it
can run offline. Four short model-derived layer-12 recurrence traces are also
reported as diagnostics. Neither source establishes closed-loop perplexity,
downstream accuracy, or complete-model quality. Closed-loop Qwen3-Next-80B
evaluation requires the checkpoint and substantially more execution memory
than is available on this host.

Exact nominal and high-retention input distributions are recorded in
`docs/synthetic_trace_protocol.json` and checked against the executed generator
paths by `tests/test_synthetic_trace_protocol.py`.

Large generated vectors, local calibration `.npz` captures, tool downloads,
Vivado/HLS build directories, and logs are intentionally ignored. The checked-in
SHA manifests and `docs/evidence_manifest.md` document the current evidence
boundary.

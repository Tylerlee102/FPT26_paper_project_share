# Native MXFP4 Gated DeltaNet FPGA Recurrence Core

Simulation-only research code for a controlled arithmetic-replacement study:
can native OCP MXFP4-B32 replace BF16-style arithmetic in the same
persistent-state Gated DeltaNet recurrence core while reducing FPGA cost and
retaining long-sequence recurrent-state stability?

Current release state: **NOT PAPER READY**. The corrected evidence answers no
for the present uniform-MXFP4 implementation. BF16 passes the frozen 8192-token
synthetic stability gate; native encoded MXFP4 does not. The matched HLS
MXFP4 implementation also uses more LUTs and a longer estimated STEP loop than
the BF16 baseline. Energy, physical all-layer fit, closed-loop model quality,
and board behavior remain unmeasured or externally blocked.

One recurrence-aware E2M1-primary/signed-E2M0-residual candidate passes six
separately recomputed 1024-token high-retention traces and 64-token HLS C
simulation. It also passes two fully recomputed 8192-token development runs;
their minimum all-token cosine is 0.994389 and maximum all-token state relative
L2 is 0.099057. It is a mitigation rather than the controlled uniform
replacement, and its HLS LUT, STEP-cycle, and II results fail the Pareto gate.
The longer runs remain development-only and share the registered seed.

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
python -m scripts.verify_synthetic_stability
python -m scripts.verify_native_encoded_long_trace
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
python -m scripts.verify_hls_command_trace
python -m scripts.verify_synthetic_stability
python -m scripts.verify_native_encoded_long_trace
python -m scripts.corrected_datapath_figure
python -m scripts.corrected_long_trace_panel
python -m scripts.corrected_paper_assets
python -m scripts.replacement_question_summary
python -m scripts.final_completion_gate
```

`paper/numbers.json`, `paper/provenance.json`, the existing manuscript PDFs,
and the legacy paper-pack outputs predate the corrected recurrence and kernel
boundary. They remain preserved for auditability and are not current evidence.
Current source assets live under `paper/corrected/`; their manifest verifies
the corrected figure hashes and records source identity. PDF handling is
staged to avoid a circular or premature release. After all experimental and
hardware gates pass, `python -m scripts.build_corrected_paper` (or
`make corrected-paper-audit`) may create only
`paper/corrected/paper_audit_candidate.pdf`, which is explicitly ineligible
for submission. Rendered pages and a page checklist are validated by
`python -m scripts.record_paper_visual_audit`. Only after all eleven completion
gates pass may `python -m scripts.finalize_corrected_paper` (or
`make corrected-paper-pdf`) copy those exact audited bytes to the final PDF.
`python -m scripts.paper_pack` then packages corrected canonical numbers,
source, figures, reports, audit evidence, and the final PDF. The current gate
blocks every PDF stage.

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
can run offline. It does not establish realistic activation fidelity,
perplexity, downstream accuracy, or complete-model quality. Closed-loop
Qwen3-Next evaluation requires an approved checkpoint/data path and adequate
compute.

Exact nominal and high-retention input distributions are recorded in
`docs/synthetic_trace_protocol.json` and checked against the executed generator
paths by `tests/test_synthetic_trace_protocol.py`.

Large generated vectors, local calibration `.npz` captures, tool downloads,
Vivado/HLS build directories, and logs are intentionally ignored. The checked-in
SHA manifests and `docs/evidence_manifest.md` document the current evidence
boundary.

# Native MXFP4 Gated DeltaNet FPGA Accelerator

Simulation-only research code for an MXFP4 persistent-state dataflow accelerator for
one Gated DeltaNet decode layer.

The repository contains the FP32/MXFP4 golden path, HLS sources, checked-in
cosim/Vivado evidence, and the paper-number pipeline. Some full-acceptance
evidence is still blocked locally: Qwen3-Next activation capture is not
available, so realistic PPL/model-quality claims are not made.

## Repository Contents

- `golden/`: FP32, MXFP4, and INT4 software references plus deterministic vector generation.
- `hls/`: Vitis HLS C++ source, headers, testbenches, and Tcl entry points.
- `scripts/`: calibration, HLS/Vivado launchers, benchmark extraction, and paper artifact generation.
- `tests/`: reproducibility and provenance tests.
- `reports/`: checked-in evidence used by the paper-number pipeline.
- `paper/`: canonical `numbers.json`, `provenance.json`, generated tables, snippets, and figures.
- `vivado/`: Vivado Tcl and timing constraints.

## Quick Start

```powershell
python -m pip install -e ".[dev]"
python -m unittest discover -s tests
python -m scripts.benchmark
python -m scripts.paper_tables
python -m scripts.paper_figures
python -m scripts.paper_pack
```

If `make` is not available on Windows, run the equivalent commands directly:

```powershell
python -m unittest discover -s tests
python -m golden.calibrate
python -m golden.vectors --kind synthetic --count 16 --output-dir data/vectors
python -m scripts.benchmark
python -m scripts.paper_tables
python -m scripts.paper_figures
python -m scripts.paper_pack
```

## Reproducing the Reported Numbers

The fastest reproducibility path uses the checked-in reports and regenerates the
paper artifacts from them:

```powershell
python -m unittest discover -s tests
python -m scripts.benchmark
python -m scripts.paper_tables
python -m scripts.paper_figures
python -m scripts.paper_pack
```

The canonical paper measurements are stored in `paper/numbers.json`, and each
entry is mapped to its source in `paper/provenance.json`. The current Phase 7
pack validation report is `reports/phase7_validation.md`.

## Full Toolchain Reproduction

Regenerating HLS and post-implementation Vivado evidence requires AMD/Xilinx
Vitis HLS and Vivado for the Alveo U55C target (`xcu55c-fsvh2892-2L-e`):

```powershell
make hls-csim
make hls-csynth
make hls-cosim
make vivado-synth
make vivado-impl
make phase6
make paper-pack
```

The scripts search common Xilinx installation locations. If the tools are
installed elsewhere, set the relevant executable paths or adapt
`scripts/xilinx_tools.py`.

## Data Availability

The default calibration path uses deterministic synthetic vectors so the repo can
run offline. Full Phase 2 acceptance still requires the external Qwen3-Next
activation capture and Microsoft `microxcaling` parity run.

Large generated vectors, local calibration `.npz` captures, tool downloads,
Vivado/HLS build directories, and logs are intentionally ignored. The checked-in
SHA manifests and provenance files document the current evidence boundary.

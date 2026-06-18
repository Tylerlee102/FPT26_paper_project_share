# AGENTS.md - Native MXFP4 Persistent-State Dataflow Accelerator for Gated DeltaNet

Specification for autonomous coding work in this repository. This file is the
source of truth for implementation decisions. If a decision is not covered here,
stop and ask before acting.

Version 2, dated 2026-05-03. This version pivots from INT4-only to MXFP4-primary
with an INT4 fallback gate at the end of Phase 4. Every number that appears in
the manuscript must be machine-traceable to a source file.

## Mission

Build a simulation-only native MXFP4 datapath on FPGA for one Gated DeltaNet
decode layer of Qwen3-Next. The accelerator uses block-scaled FP4 elements
(E2M1 with E8M0 shared scales per 16- or 32-element block), persistent-state
dataflow, and LUT-based FP4 multiply logic. FP4 MACs must not use DSPs.

Target device and tool flow:

- Xilinx Alveo U55C, `xcu55c-fsvh2892-2L-e`
- Vitis HLS, 250 MHz target clock
- Vivado post-implementation reports for area, timing, and power
- HLS C/RTL cosimulation for authoritative latency/parity

Headline claim template:

> We present the first native MXFP4 FPGA accelerator for Gated DeltaNet decode,
> with a parameterized LUT-based E2M1 MAC fabric and block-exponent-aware
> persistent-state dataflow, achieving N x speedup and M x energy efficiency
> over the BF16 baseline at iso-area while preserving model quality on
> Qwen3-Next-80B layers.

The numerical placeholders must be filled from `paper/numbers.json`; never type
paper numbers by hand.

## Scope

In scope:

- One GDN decode kernel, batch=1, single-token autoregressive.
- Native MXFP4 weights, activations, and preferably recurrent state.
- MXFP8 recurrent-state fallback if MXFP4 state does not meet quality.
- INT4 fallback path only if the Phase 4 human decision gate selects it.
- Deterministic synthetic vectors and realistic Qwen3-Next activation captures.
- Bit-exact Python/HLS parity and report-driven paper tables/figures.

Out of scope:

- Prefill, parallel scan, full end-to-end inference, training, QAT, and
  side-channel work.
- DSP-based FP4 multiply.
- Hand-edited paper numbers or hand-edited generated result macros.

## Repository Layout

Required top-level structure:

```text
gdn-fpga/
  AGENTS.md
  README.md
  pyproject.toml
  Makefile
  golden/
  hls/
  vivado/
  tests/
  data/
  reports/
  paper/
```

The paper LaTeX lives in a separate repository. It must import generated macros,
tables, and figures from this repository.

## Make Targets

Required entry points:

- `make setup`
- `make golden`
- `make vectors`
- `make hls-csim`
- `make hls-csynth`
- `make hls-cosim`
- `make vivado-synth`
- `make vivado-impl`
- `make benchmark`
- `make paper-tables`
- `make paper-figures`
- `make paper-pack`
- `make ci`
- `make clean`

On Windows systems without `make`, equivalent `python -m ...` commands are
acceptable, but generated artifacts must remain in the same paths.

## Phases

There are seven phases.

1. Golden FP32 model and deterministic vectors.
2. MXFP4 quantization reference and synthetic/realistic accuracy checks.
3. HLS implementation, including the novel `mac_e2m1.cpp` and
   `block_exp_align.cpp` modules.
4. MXFP4 decision gate. The workflow must halt and ask a human for the MXFP4-vs-INT4
   decision.
5. HLS cosimulation and Vivado synth/implementation.
6. Benchmark sweeps and paper-number extraction.
7. Paper pack generation.

## Phase 1 Requirements

`golden/gdn_fp32.py` implements:

```python
S_t = S_{t-1} - beta_t * (S_{t-1} k_t - v_t) k_t^T
```

followed by the output gate. Default Qwen3-Next constants are `num_heads=32` and
`head_dim=128`.

## Phase 2 Requirements

`golden/mx_format.py` owns E2M1, E8M0, E4M3, block grouping, and round-to-nearest
even behavior. `golden/gdn_mxfp4.py` is the bit-exact software reference for HLS.

Quantization recipe:

- Weights: MXFP4, block size 32, per-output-channel.
- Activations: dynamic per-token MXFP4, block size 32.
- State: MXFP4 state, block size 16, unless quality requires MXFP8.
- Beta: symmetric INT8.
- Element multiply: E2M1 x E2M1 to fixed Q4.3 partials.
- Block accumulator: INT24.
- Final pre-dequant output: FP16.

If MXFP4 PPL degradation exceeds the allowed threshold after mitigations, stop
and ask.

## Phase 3 Requirements

HLS files under `hls/src` and `hls/include` must implement a five-phase
persistent-state dataflow. FP4 multiply must be LUT-based and native:

- sign XOR
- 2-bit exponent add with bias adjustment
- implicit-leading-one mantissa multiply
- subnormal handling
- Q4.3 fixed-point partial output

`block_exp_align.cpp` must align partial products using shared E8M0 block scales
and accumulate into INT24.

Default compile-time parameters:

```cpp
constexpr int NUM_HEADS = 32;
constexpr int HEAD_DIM = 128;
constexpr int P_K = 16;
constexpr int P_V = 8;
constexpr int BLOCK_SIZE = 32;
constexpr float CLOCK_NS = 4.0f;
constexpr bool USE_MXFP4 = true;
```

## Phase 4 Decision Gate

The workflow must halt for explicit human decision. Proceed with MXFP4 only if all are
true:

- C-sim bit-exact vectors pass.
- C-synthesis Fmax is at least 200 MHz.
- Inner loops have II=1.
- LUT and BRAM utilization are below 80%.
- Remaining work to Phase 5 is no more than 3 person-days.

If any criterion fails and the human chooses fallback, set `USE_MXFP4=false` and
document the INT4 fallback decision in `reports/decision_gate.md`.

## Phase 5 Requirements

HLS cosimulation must run for at least 64 tokens and be bit-exact. Vivado reports
must include timing, utilization, and power. Do not proceed if any cosim bit
differs from the golden reference.

## Phase 6 Requirements

Required sweeps:

- `(P_K, P_V) in {(8,4), (16,8), (32,16)}`
- `BLOCK_SIZE in {16, 32}`
- MXFP8 state comparison if MXFP4 state holds

Every table/figure cell must trace through `paper/provenance.json`.

## Phase 7 Requirements

`make paper-pack` produces `paper/pack/submission_<git_sha>.zip` containing:

- `paper/numbers.json`
- `paper/provenance.json`
- generated tables, snippets, and PDF figures
- Vivado reports
- HLS C-synthesis reports
- cosim latency CSVs and reports
- calibration data SHA256 manifest
- git log or explicit no-commit note
- this `AGENTS.md`

## Paper Data Pipeline

`paper/numbers.json` is the canonical source of every paper measurement. Each key
is snake_case and stores `value`, `units`, `source`, `source_line`, `extractor`,
`git_sha`, and `timestamp`. External citations must use `source: "external"` and
must include precise citation notes.

`paper/provenance.json` maps every `numbers.json` key to the source file, line,
extractor, timestamp, and git SHA.

Generated LaTeX files under `paper/snippets` and `paper/tables` must not be
edited by hand. Generated figures under `paper/figures` must read exclusively
from `paper/numbers.json`.

## Cross-Phase Rules

- Use deterministic seeds. Default seed is `0xFB72` or `GDN_SEED`.
- No bare equality on floats.
- `gdn_mxfp4.py` is the bit-exact reference for HLS.
- HLS cosim is the bit-exact reference for synthesized RTL.
- Skipped or xfailed tests require entries in `reports/known_issues.md`.
- Do not loosen tolerances or regenerate failing vectors to hide a bug.
- Do not edit `paper/numbers.json` or generated LaTeX macros by hand.

## Stop And Ask

Stop for human input if:

- Phase 2 PPL degradation exceeds the hard floor after documented mitigations.
- Phase 4 decision gate is reached.
- HLS cannot close 200 MHz after reasonable pipelining/retiming attempts.
- Cosim disagreement cannot be localized after one debug pass.
- Vivado implementation fails to fit.
- Calibration data cannot be collected.
- Test expectations in this file conflict.
- `paper-pack` fails provenance validation.

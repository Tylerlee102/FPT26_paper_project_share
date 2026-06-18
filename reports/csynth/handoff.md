# Phase 3 HLS Handoff

Implemented source files:

- `hls/src/mac_e2m1.cpp`: table-driven E2M1 element multiply returning signed Q*.3 fixed-point partials. The product table is fully partitioned so HLS maps it to LUT logic rather than a DSP multiply.
- `hls/src/block_exp_align.cpp`: block-exponent alignment, dominant-exponent selection, II=1 accumulation, and INT24 saturation.
- `hls/src/phase1_prepare.cpp` through `phase5_output.cpp`: phase split matching the persistent-state dataflow structure.
- `hls/src/gdn_top.cpp`: fixed-point prediction, delta-state writeback, and output projection over MXFP4 elements.
- `hls/tb/*.cpp`: unit benches for MAC, block exponent alignment, phase helpers, and 32-vector top-level parity.

Known divergence from the USC BF16 dataflow:

- The datapath stores E2M1 elements and E8M0 block scales separately instead of BF16 state and activation words.
- The FP4 MAC path is LUT-table based and does not request DSP resources.
- The current `gdn_top` uses the local fixed-point HLS parity path. Qwen3-Next captured realistic-vector parity remains a data-availability improvement for the full paper pipeline.

Tool status:

- Vitis HLS 2024.2 is available through the repository runner's Xilinx path discovery and temporary `X:\` workspace mapping.
- `reports/csim/results.md` records `tb_gdn_top PASS vectors=32/32`.
- `reports/csynth/util.md` records Fmax, II, LUT, and BRAM evidence for the Phase 4 gate.

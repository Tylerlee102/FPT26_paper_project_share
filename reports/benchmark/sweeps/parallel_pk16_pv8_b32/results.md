# HLS C-Simulation Results

Generated: 2026-05-04T23:36:37.417734+00:00

- Source log: `gdn_mxfp4_hls/u55c_250mhz/csim/report/gdn_top_csim.log`
- Status: current
- Freshness: latest source `hls/src/gdn_top.cpp` modified 2026-05-04T22:10:57.291130+00:00; C-sim log modified 2026-05-04T23:36:22.255315+00:00
- `tb_gdn_top PASS vectors=64/64`
- `CSim done with 0 errors`

Coverage notes:

- The vectors are deterministic HLS fixed-point parity cases generated inside `hls/tb/tb_gdn_top.cpp`.
- The testbench checks both output and MXFP4 state writeback.
- Qwen3-Next captured realistic-vector parity remains blocked on calibration-data availability.

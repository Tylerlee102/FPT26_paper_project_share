# HLS C-Simulation Results

Generated: 2026-05-21T18:17:34.968720+00:00

- Source log: `gdn_mxfp4_hls/u55c_250mhz/csim/report/gdn_top_csim.log`
- Status: current
- Freshness: latest source `hls/tb/tb_gdn_top.cpp` modified 2026-05-20T17:37:05.909653+00:00; parity log `gdn_mxfp4_hls/u55c_250mhz/csim/report/gdn_top_csim.log` modified 2026-05-21T18:17:34.635485+00:00
- `tb_gdn_top PASS vectors=64/64`
- `CSim done with 0 errors`

Coverage notes:

- The vectors are deterministic HLS fixed-point parity cases generated inside `hls/tb/tb_gdn_top.cpp`.
- The testbench checks packed output parity; MXFP4 state writeback checks are enabled when `GDN_STATE_READBACK=1`.
- Qwen3-Next captured realistic-vector parity remains pending until the real calibration capture is available.

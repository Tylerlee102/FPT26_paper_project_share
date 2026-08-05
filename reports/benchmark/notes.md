# Benchmark Notes

Generated Phase 6 benchmark extraction from currently available reports.

## Completed

- Extracted current MXFP4 B=32, P_K=16, P_V=8 latency, power, area, and synthetic quantization metrics.
- Added B=16 synthetic block-size accuracy metrics from the deterministic calibration run.
- Added external H100 and USC FPGA baselines with citation notes.
- Wrote a Phase 6 sweep plan; non-default rows now include Vivado post-implementation area/power when available.
- Non-default RTL cosim latency is available for 4/4 sweep rows.
- Default RTL cosim is unavailable or stale; default latency falls back to HLS csynth.
- HLS C-sim report is fresh for the current HLS sources.
- Added long-token state drift, stress-distribution, state-boundary, storage-overhead, and off-chip traffic metrics when their reports are present.
- Git SHA resolved from repository HEAD.

## Remaining Phase 6 Gaps

- Rerun 64-token RTL cosim for the final tile-streamed RTL; current default latency uses csynth because cosim is stale or unavailable.
- Add Qwen-captured realistic accuracy/PPL numbers; current metrics are synthetic only. See `reports/golden/qwen_capture_status.md`.

## Headline Target Check

- Fmax target: target met (342.47 MHz; target >= 300 MHz, hard floor >= 200 MHz).
- Latency target: hard floor met (51.408 us/token; target <= 50 us, hard floor <= 100 us).
- BRAM target: target met (3.67%; target <= 50%, hard floor <= 80%).
- DSP target: target met (7.27%; target <= 30%, hard floor <= 80%).
- LUT target: target met (6.64%; target <= 70%, hard floor <= 90%).
- Power target: target met (8.976 W; target <= 10 W, hard floor <= 18 W).
- Speedup vs USC target: hard floor met (1.229x; target >= 2x, hard floor >= 1x).
- Speedup vs H100 target: hard floor met (5.544x; target >= 6x, hard floor >= 4.5x).

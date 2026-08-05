# Matched BF16 Physical-Fit Attempt

Generated: `2026-08-05T06:32:03.104535+00:00`
Extraction status: `PASS`

- Synthesis: `PASS`
- Placement: `FAIL_CAPACITY`
- Physical fit: `FAIL`
- Synthesized resources: `46,894` CLB LUT, `38,165` FF, `9,216` BRAM tiles, `0` URAM, `15` DSP
- Capacity DRC: `9,216` RAMB36/FIFO required versus `2,016` available
- Independent state-only lower bound: `1,024` URAM versus `960` available
- Routed timing, vectorless power, and energy: unavailable because placement failed

A reduced-layer route is not substituted because it would change the controlled all-layer state layout.

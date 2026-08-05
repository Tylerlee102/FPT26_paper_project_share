# Corrected RTL Co-simulation Smoke

Generated: `2026-08-02T01:09:43.488528+00:00`

- Smoke status: `FAIL`
- C testbench: `PASS` (12 hand commands, 1 oracle step)
- Verilog RTL simulation: `FAIL` (XSIM out of memory)
- Progress: `3 / 15` transactions
- HLS-reported elapsed time: `673` seconds
- Failed allocation request: `8388608` bytes
- First valid recurrent STEP completed: `no`
- Required 64-token RTL parity: `NOT_RUN`
- Current HLS source matches smoke source: `no`

The bounded smoke failed during transaction 4, the first valid full
STEP after three early control-path transactions. A 64-token testbench
would issue 141 top-level transactions. It was not launched because the
smoke exhausted simulator memory before completing one recurrent update.
A later transport-pipeline cleanup changed synthesis directives and
validation-loop pragmas; this frozen smoke is retained as a failed attempt
and does not establish parity for current source.

This result is not evidence of RTL correctness, selected-candidate
physical feasibility, timing closure, or FPGA energy.

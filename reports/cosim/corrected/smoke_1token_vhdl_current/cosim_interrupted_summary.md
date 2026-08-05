# Interrupted RTL Co-simulation Smoke

Generated: `2026-08-02T01:58:49.130574+00:00`

- Status: `FAIL`
- Scope: one-token current-source VHDL RTL co-simulation smoke
- RTL language: `vhdl`
- Progress: `3 / 15` transactions
- First valid recurrent STEP completed: `no`
- Observed private memory at termination: `26.67` GiB
- Minimum observed free physical memory: `0.21` GiB
- Required 64-token RTL parity: `NOT_RUN`

The simulator remained at 3/15 transactions while private memory grew to 26.67 GiB; the process was stopped before exhausting host memory.

This is preserved failed-attempt evidence. It does not establish RTL
correctness, selected-candidate physical feasibility, timing closure,
or FPGA energy.

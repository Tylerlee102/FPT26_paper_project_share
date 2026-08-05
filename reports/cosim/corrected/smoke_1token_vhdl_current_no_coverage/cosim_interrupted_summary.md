# Interrupted RTL Co-simulation Smoke

Generated: `2026-08-02T01:58:49.427727+00:00`

- Status: `FAIL`
- Scope: one-token current-source VHDL RTL co-simulation smoke with coverage and assertions ignored
- RTL language: `vhdl`
- Progress: `3 / 15` transactions
- First valid recurrent STEP completed: `no`
- Observed private memory at termination: `12.26` GiB
- Minimum observed free physical memory: `13.09` GiB
- Required 64-token RTL parity: `NOT_RUN`

The simulator remained at 3/15 transactions while private memory reached 12.26 GiB on the same growth curve; the run was stopped early because further pressure added no diagnostic value.

This is preserved failed-attempt evidence. It does not establish RTL
correctness, selected-candidate physical feasibility, timing closure,
or FPGA energy.

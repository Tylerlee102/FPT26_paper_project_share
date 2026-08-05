# Interrupted RTL Co-simulation Smoke

Generated: `2026-08-02T01:58:49.311640+00:00`

- Status: `FAIL`
- Scope: one-token current-source VHDL RTL co-simulation smoke with xelab multithreading disabled
- RTL language: `vhdl`
- Progress: `3 / 15` transactions
- First valid recurrent STEP completed: `no`
- Observed private memory at termination: `20.53` GiB
- Minimum observed free physical memory: `3.97` GiB
- Required 64-token RTL parity: `NOT_RUN`

The simulator remained at 3/15 transactions while private memory grew to 20.53 GiB; disabling xelab multithreading did not remove the growth.

This is preserved failed-attempt evidence. It does not establish RTL
correctness, selected-candidate physical feasibility, timing closure,
or FPGA energy.

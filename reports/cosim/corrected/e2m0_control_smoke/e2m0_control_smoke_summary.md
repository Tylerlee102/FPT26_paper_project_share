# Corrected E2M0 Generated-RTL Control Smoke

- Official Vitis HLS C/RTL co-simulation: `PASS`
- Simulator: `XSIM 2025.2`
- Completed transactions: `2 / 2`
- Per-command latency: `19971` cycles
- Reported interval: `20081` cycles
- Total execution: `40052` cycles
- Recurrent state transition covered: `no`
- Required 64-token candidate RTL parity: `NOT_RUN`
- Separate 64-token candidate C-sim parity: `PASS`

The official vendor flow establishes generated-RTL parity for two early-return control paths. It does not execute a recurrent state transition and is not the required 64-token RTL parity test.

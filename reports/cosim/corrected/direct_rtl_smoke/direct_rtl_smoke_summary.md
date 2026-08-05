# Direct RTL Smoke

- Status: `PASS`
- Scope: one HLS-generated Verilog RESET/STEP/READBACK sequence
- Harness: custom direct AXI-Lite/AXI memory models
- XSIM kernel peak: `83580` KB
- Required 64-token RTL parity: `NOT_RUN`

## Commands

- `0`: `33386` cycles, status `0`, generation `0`
- `2`: `5597299` cycles, status `0`, generation `1`
- `3`: `2192044` cycles, status `0`, generation `1`

The direct harness establishes a bounded-memory one-token RTL smoke for the generated snapshot. It is not the required 64-token HLS C/RTL parity result and does not establish implementation timing, power, energy, or selected recurrent-correction hardware.

# Selected RS2/R3 Direct RTL 64-Token Parity

- Status: `PASS`
- Simulator: `Verilator 5.050 2026-07-01 rev v5.050` under WSL Ubuntu-24.04
- Harness mode: `scheduler_free_cpp`
- Sequence: one LOAD, 64 sequential STEP commands, one READBACK
- Token outputs: all `262144` mantissa/exponent pairs
- Final snapshot: primary/residual stacks, scales, logs, coefficients, and metadata
- STEP cycles: min `21883985`, mean `44824404.88`, max `91842379`
- Required 64-token generated-RTL parity: `PASS`

This is a custom direct AXI harness over the Vitis-HLS-generated Verilog.
It is not the memory-exhausting Vitis UVM wrapper, post-route simulation, or board evidence.

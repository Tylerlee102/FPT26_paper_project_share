# Direct RTL 64-Token Parity

- Status: `PASS`
- Sequence: one RESET, 64 sequential STEP commands, one READBACK
- Per-token outputs: all `4096` mantissas and `4096` exponents
- Final state: all `524288` elements and `16384` block scales
- STEP cycles: min `5461867`, mean `6123314.88`, max `6137971`
- XSIM kernel peak: `89988` KB
- Required 64-token RTL parity: `PASS`

The custom direct harness bypasses the Vitis UVM wrapper but executes
the current HLS-generated Verilog and compares it bit exactly with the
verified encoded trace. This does not validate post-route hardware or
the selected recurrent-correction candidate.

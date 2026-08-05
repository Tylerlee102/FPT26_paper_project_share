# Corrected Candidate 64-Token RTL Completion

- HLS C simulation, 64 tokens: `PASS`
- Vitis/XSIM RTL transactions: `0 / 66` (host OOM in two isolated attempts)
- Verilator direct RTL LOAD: `PASS` in `4797322` cycles
- Corrected recurrent STEP transactions completed in RTL: `0`
- Required corrected-candidate 64-token RTL parity: `NOT_ESTABLISHED`
- Diagnostic projected host runtime: `16.3` to `27.2` hours

The host-runtime projection is a simulator feasibility diagnostic, not FPGA latency or energy evidence.

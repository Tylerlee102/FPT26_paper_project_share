# Generated-UVM XSim Memory Diagnostics

These logs preserve the August 10, 2026 investigation of the Vitis HLS 2025.2
generated UVM wrapper for the 66-command RS2/R3 trace. The runs were stopped
before host exhaustion and are not parity evidence.

- Official wrapper status: `NOT_RUN`
- Completed recurrent tokens: `0`
- Completed transactions: `1 / 66`
- Elaboration threads tested: `8` and `off`

Controlled variants include:

- accelerated generated wrapper with its default waveform configuration;
- waveform configuration removed, assertions and coverage ignored;
- HLS dataflow profiler replaced by a no-op monitor;
- AXI transfer counters added;
- AXI monitor polling gated on handshakes;
- AXI latency-counter queues gated while idle; and
- original generated UVM elaborated with `--mt off`.

Every variant reaches at most the reset completion marker (`1 / 66`) before
the XSim kernel's private memory grows beyond the host-safe diagnostic budget.
No run emits the exact HLS C post-check marker, so the strict archive and paper
evidence readers correctly reject this directory as a completed official
cosimulation.

The separate direct-XSim harness is the recurrent generated-RTL evidence. It
executes the same HLS-generated Verilog without the generated UVM wrapper and
passes RESET, 64 sequential STEPs, READBACK, every output/counter, and the full
final encoded state. Its evidence is under
`reports/cosim/corrected/direct_rtl_trace64/`.

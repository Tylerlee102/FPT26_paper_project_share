# Latency Target Root Cause

Generated: 2026-05-07

The original Phase 6 kernel missed the latency and speedup hard floors because
the top-level interface streamed the full recurrent state through memory ports
on every token. That failure mode has been removed in the current default RTL:
the recurrent state is resident in partitioned on-chip memory, and the output
interface is packed by `P_V` lanes.

Resolved baseline:

- Previous state-streamed csynth latency: `1,738,881` cycles
- Current packed-output csynth latency: `12,852` cycles
- Current 128-token RTL cosim average latency: `12,868` cycles
- Current RTL cosim latency at 250 MHz: `51.472` us/token

Current dominant costs:

- Token input load is still scalar at 4,096 cycles for q/k/v/gate.
- Predict and update each take about 4,100 cycles.
- Packed output write is reduced to 512 stores instead of 4,096 scalar stores.

Further speedup would require packed token-input ingress or a streaming token
front-end, but the hard floors are no longer missed by the default Phase 6
artifact.

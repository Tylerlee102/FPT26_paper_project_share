# Corrected HLS C-Simulation Results

Generated: `2026-08-02T01:04:14.518500+00:00`

- Status: `PASS`
- Target: `xcu55c-fsvh2892-2L-e` at 4.0 ns
- Hand-derived command checks: `75`
- Full-dimension encoded-oracle steps: `64`
- Trace SHA256: `677A4C1673754AD7603EC05FBA4FFC7B5417B5763B293F69B5E798C1769659C0`
- Raw C-sim log SHA256: `6DE97D87AEF498E03A65105619885F6D48A10BADA78670A7D953F14B3AE91CC8`
- Freshness: latest input `hls/src/phase1_prepare.cpp` modified 2026-08-02T01:03:22.951515+00:00; log modified 2026-08-02T01:04:06.271990+00:00

The testbench compares status, generation, all eight per-command and
cumulative counters, every output mantissa/exponent tuple, and the
complete final recurrent-state element/scale readback. It does not
establish RTL or board parity.

Trace input-stream SHA256: `617F8F961DABA23CC7F161527F2AB60E3B09017BD2019EFA4A0C698222782BDA`.

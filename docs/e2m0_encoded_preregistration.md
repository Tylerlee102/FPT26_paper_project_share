# Encoded E2M0 Candidate Preregistration

Registered: `2026-08-02T10:10:40.7553223Z`

Candidate evidence status: `NOT_RUN`

## Frozen Candidate

The encoded candidate uses two residual-stacked MXFP4-B32 terms for Q, K, V,
write-log keys, and write-log updates; an E2M1/E8M0 primary state plus a dense
signed three-bit E2M0-style residual; Q1.15 base/log decay coefficients; a
seven-entry fixed all-head write log; and signed INT32 accumulation aligned to
five guard powers below the largest raw term exponent.

Its logical recurrent payload is 537,744 bytes per controlled recurrence core,
including base, log, coefficients, and 16 bytes of metadata. This is 2,928
bytes below uniform MXFP8-E4M3-B32 at the same state shape. Logical payload is
not a physical-memory or energy result.

## Development Result

Seed `0xFB72`, high-retention traces, random and zero initial states, and
checkpoints 64/256/1024 passed the frozen quality gate. Both complete reruns
matched every saved token/checkpoint field and source/output hash. These are
development results and were inspected before this registration.

## Held-Out Gate

The untouched seeds are `0xA17E5EED`, `0xC4D3B2A1`, and `0x06E5A1D0` in that
order. Each seed will run random then zero initial state for 1,024
high-retention tokens. Every run must satisfy:

- output cosine at 64, 256, and 1,024 tokens at least 0.99;
- final state relative L2 at most 0.10;
- zero E2M1 element saturation;
- zero INT32 accumulator saturation; and
- zero E8M0 scale clamps.

Alignment underflows and deliberate E2M0 residual clips are reported but not
thresholded. All six runs must pass. Source hashes are frozen in
`reports/benchmark/corrected/e2m0_encoded_preregistration.json`; any mismatch
invalidates execution rather than silently amending this registration.

## Extended Development

After the held-out gate, seed `0xFB72` may be extended to 8,192 tokens for both
initial-state modes at checkpoints 64/256/1024/4096/8192. This remains
development evidence and cannot replace the held-out gate.

## Boundaries

This preregistration covers encoded software stability only. It does not make
HLS, RTL, fit, timing, board-energy, closed-loop Qwen, perplexity, or novelty
claims. A new paper PDF remains prohibited while those gates are not `PASS`.


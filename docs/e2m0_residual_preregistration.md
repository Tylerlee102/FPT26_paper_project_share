# E2M0 Fold-Residual Candidate Preregistration

Status: `PASS` for development-only configuration freeze. Candidate evidence
outside the selection traces is `NOT_RUN` at registration time.

## Failure Diagnosis

The frozen sparse-MXFP4/write-log candidate fails only the two high-retention
development traces in the registered five-family stress matrix. At token 256,
replacing the MXFP8 log with FP32 changes state relative L2 from 0.171711 to
0.165040, while adding a third base-residual term changes it to 0.060112. The
dominant error therefore enters when a full log is folded back into the
resident base rather than when a write is stored in the log.

Development-only experiments then evaluated two fixed-storage corrections.
Allocating the sparse residual-block budget by global L2 energy improved the
token-256 error only to 0.156432. A dense 3-bit E2M0-style residual term with
adjacent-scale SSE selection reached 0.099990 when combined with a two-term
MXFP4 write log. These exploratory values select the candidate; they are not
held-out evidence.

## Frozen Candidate

- Two residual-stacked MXFP4 terms for Q, K, and V.
- One dense E2M1/E8M0 MXFP4 resident-base term.
- One dense signed 3-bit residual term with magnitudes `[0, 0.5, 1, 2]` and one
  E8M0 scale per 32 elements.
- For each residual block, compare the overflow-free E8M0 scale with the
  adjacent scale one exponent lower and select the smaller squared error; ties
  keep the overflow-free scale.
- Two residual-stacked MXFP4 terms for each write-log key and update.
- Seven log entries and the existing fixed atomic all-head fold schedule.
- The same corrected recurrence, K-by-V layout, 16 Q/K heads, 32 value heads,
  K=V=128, B32 grouping, and Q1.15 alpha/beta controls.

The candidate uses 538,256 logical recurrent-state bytes: 48.6755% below BF16
and 0.4467% below a uniform MXFP8-E4M3-B32 state. This is logical accounting,
not physical BRAM/URAM, routing, service-rate, or energy evidence.

## Gates

The development robustness matrix uses seed `0xFB72` across dynamic-range,
cancellation, high-retention, decay-sweep, and adversarial traces with random
and zero initial state. High-retention is additionally run at seeds `0xFB73`
and `0xFB74`. Every 64/256/1024 checkpoint must have output cosine at least
0.99, token-1024 state relative L2 must be at most 0.10, and no write may drop.

If that matrix passes, seed `0xFB72` high-retention random/zero traces extend to
8192 tokens with checkpoints 64/256/1024/4096/8192 under the same limits. Only
if both development gates pass may the frozen candidate run on new held-out
seeds `0x0D15EA5E`, `0x0BADC0DE`, and `0x00051A8E` for nominal and
high-retention traces with random and zero initial states.

The machine-readable registration, including exact source hashes and stopping
rule, is `reports/benchmark/corrected/e2m0_residual_preregistration.json`.

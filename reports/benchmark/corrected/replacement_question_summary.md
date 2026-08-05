# MXFP4-for-BF16 Replacement Question

Evidence synthesis status: `PASS`
Current answer: `FAIL`

No for the current uniform-MXFP4 implementation. It reduces logical state storage, but native encoded and floating-Q/DQ diagnostics fail the frozen synthetic drift gate, and the fixed-geometry HLS implementation fails the LUT-and-STEP cost gate. Energy and physical fit remain unmeasured, so no energy or physical advantage is claimed.

| Criterion | Status | Controlled result |
|---|---|---|
| BF16 synthetic stability | PASS | Frozen 0.99 cosine / 0.10 final-state-relative-L2 gate |
| Native encoded MXFP4 stability | FAIL | token-8192 cosine 0.429834, state relative L2 2.580730 |
| Uniform MXFP4 synthetic stability | FAIL | Same trace, state layout, and recurrence boundary |
| Scale-policy rescue | FAIL | Fixed, every-token, periodic, and threshold refresh |
| Logical state storage | PASS | 278528 versus 1048576 bytes/layer (73.44% reduction) |
| HLS LUT and STEP cost | FAIL | 1.636x LUT, 1.437x max STEP cycles |
| Energy advantage | BLOCKED_EXTERNAL | No matched board or post-route energy result |
| Physical all-layer fit | NOT_RUN | Raw bit capacity is not placed/banked fit |

## Recurrence-Aware Mitigation (separate comparison)

| Criterion | Status | Result |
|---|---|---|
| Test-set 1,024-token quality | PASS | min all-token cosine 0.994430; max all-token state relative L2 0.098653 |
| Full deterministic recomputation | PASS | Same-implementation integrity check for every paired condition |
| Extended 8,192-token quality | PASS | 2 development traces; min all-token cosine 0.994389; max all-token state relative L2 0.099057; development-only random/zero initial states |
| HLS 200 MHz timing | PASS | Source-locked C-synthesis estimate |
| Configured timing margin | FAIL | Target minus reported uncertainty |
| Explicit II=1 constraints | FAIL | Every targeted loop must meet II=1 |
| HLS LUT/STEP cost vs BF16 | FAIL | Matched target and dimensions; changed state representation |
| Corrected-candidate 64-token RTL | FAIL | required parity NOT_ESTABLISHED; HLS C PASS; direct RTL LOAD PASS; 0 completed recurrent steps |
| Selected-method Pareto | FAIL | Quality alone cannot pass this gate |

This is a layer-level synthetic and HLS-estimate conclusion. It does not
establish closed-loop Qwen quality, routed uniform-MXFP4 performance, or board energy.

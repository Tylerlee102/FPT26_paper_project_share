# Full-Shape Synthetic Long-Trace Stress Summary

Generated: `2026-08-04T00:34:09.558272+00:00`

Status: `PASS` for artifact validation; threshold outcomes are reported per row.

| Trace | Variant | Token-8192 cosine | Token-8192 state rel L2 | Worst cosine | Worst state rel L2 | Diagnostic |
|---|---|---:|---:|---:|---:|---|
| dynamic_range | FP32 reference | 1.000000 | 0.000000 | 1.000000 | 0.000000 | PASS |
| dynamic_range | BF16 state/operands, FP32 reductions | 0.999875 | 0.016476 | 0.999731 | 0.022308 | PASS |
| dynamic_range | MXFP4 Q/DQ | 0.410379 | 26.772181 | 0.068745 | 27.190099 | FAIL |
| dynamic_range | MXFP4 Q/DQ + MXFP8 state | 0.698070 | 2.314652 | 0.644646 | 2.388372 | FAIL |
| dynamic_range | Flat INT4 Q/DQ | 0.402932 | 4.810968 | 0.169312 | 11.765793 | FAIL |
| cancellation | FP32 reference | 1.000000 | 0.000000 | 1.000000 | 0.000000 | PASS |
| cancellation | BF16 state/operands, FP32 reductions | 0.999997 | 0.008844 | 0.999995 | 0.009603 | PASS |
| cancellation | MXFP4 Q/DQ | 0.981307 | 1.667123 | 0.976823 | 1.770789 | FAIL |
| cancellation | MXFP4 Q/DQ + MXFP8 state | 0.997011 | 0.255859 | 0.992684 | 0.266455 | FAIL |
| cancellation | Flat INT4 Q/DQ | 0.975327 | 1.332802 | 0.952397 | 2.319049 | FAIL |

The thresholds are output cosine at least 0.99 and state relative L2 at most 0.10 at every token.
These are synthetic floating-Q/DQ diagnostics, not native encoded arithmetic, closed-loop model quality, or real-activation outlier evidence.
Event counters remain `NOT_RUN` for every Q/DQ comparator.

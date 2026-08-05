# Synthetic Stability Verification

- Artifact integrity: `PASS`
- BF16 software stability gate: `PASS`
- Uniform MXFP4 stability gate: `FAIL`
- MXFP8-state stability gate: `FAIL`
- Flat INT4 stability gate: `FAIL`
- Any tested scale policy rescues uniform MXFP4: `FAIL`
- Overall synthetic MXFP4-for-BF16 replacement question: `FAIL`

The BF16 operand/state diagnostic passes the frozen synthetic stability thresholds, while uniform MXFP4 and every tested block-scale policy fail. Uniform native MXFP4 therefore fails the replacement question on stability for this trace, independent of the still-NOT_RUN physical cost comparison.

These conclusions are limited to the frozen synthetic floating Q/DQ
diagnostic. They are not model-quality or physical-FPGA evidence.

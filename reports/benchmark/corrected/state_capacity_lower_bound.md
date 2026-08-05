# All-Layer State Capacity Lower Bound

Generated: `2026-08-05T17:01:15.008727+00:00`
Calculation status: `PASS`
Uniform-MXFP4 physical all-layer bank fit: `NOT_RUN`

Declared state: `1` sequence x `36` layers x `32` value heads x `128` K x `128` V = `18874368` elements.

| State format | Bytes/layer | Bytes/36 layers | Ideal min URAM | Ideal min BRAM18K | Raw capacity | HLS covers bound | Physical fit |
|---|---:|---:|---:|---:|---|---|---|
| BF16 | 1048576 | 37748736 | 1024 | 0 | FAIL | FAIL | FAIL |
| uniform_mxfp4_e2m1_e8m0_b32 | 278528 | 10027008 | 256 | 256 | PASS | FAIL | NOT_RUN |
| mxfp8_e4m3_e8m0_b32 | 540672 | 19464192 | 512 | 256 | PASS | FAIL | NOT_RUN |
| flat_int4 | 262144 | 9437184 | 256 | 0 | PASS | NOT_RUN | NOT_RUN |

The BF16 state alone requires an ideal minimum of 1,024 URAM288
primitives, exceeding the device total of 960. Uniform MXFP4
requires at least 256 URAM288 for E2M1 elements and 256 BRAM18K for
E8M0 scales, before any implementation overhead.

The HLS totals for BF16, MXFP4, and MXFP8 are below their state-only
lower bounds. They are therefore
not valid physical-capacity evidence. A placed, banked all-layer design
is required before claiming fit for each variant.

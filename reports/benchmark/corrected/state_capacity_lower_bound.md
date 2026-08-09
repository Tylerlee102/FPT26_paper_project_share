# All-Layer State Capacity Lower Bound

Generated: `2026-08-06T07:20:01.141589+00:00`
Calculation status: `PASS`
Physical fit is reported per variant; BF16 and MXFP8 have routed results while uniform MXFP4 and flat INT4 remain `NOT_RUN`.

Declared state: `1` sequence x `36` layers x `32` value heads x `128` K x `128` V = `18874368` elements.

| State format | Bytes/layer | Bytes/36 layers | Ideal min URAM | Ideal min BRAM18K | Raw capacity | HLS covers bound | Physical fit |
|---|---:|---:|---:|---:|---|---|---|
| BF16 | 1048576 | 37748736 | 1024 | 0 | FAIL | FAIL | PASS |
| uniform_mxfp4_e2m1_e8m0_b32 | 278528 | 10027008 | 256 | 256 | PASS | FAIL | NOT_RUN |
| mxfp8_e4m3_e8m0_b32 | 540672 | 19464192 | 512 | 256 | PASS | FAIL | PASS |
| flat_int4 | 262144 | 9437184 | 256 | 0 | PASS | NOT_RUN | NOT_RUN |

The BF16 state alone would require an ideal minimum of 1,024 URAM288
primitives if stored only in URAM, exceeding the device total of 960.
The routed BF16 implementation instead preserves all 36 logical layers with
29 layers in paired 256-bit URAM banks and seven layers in paired 256-bit BRAM banks.
Uniform MXFP4
requires at least 256 URAM288 for E2M1 elements and 256 BRAM18K for
E8M0 scales, before any implementation overhead.

HLS memory totals are not used as physical-capacity evidence. The physical-fit
column is populated only from placed and routed all-layer implementations;
variants without one remain NOT_RUN.

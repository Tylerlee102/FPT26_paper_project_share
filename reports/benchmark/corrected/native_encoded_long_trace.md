# Native Encoded MXFP4 Long-Sequence Diagnostic

- Evidence generation: `PASS`
- Frozen synthetic engineering gate: `FAIL`
- Tokens: `8192`
- Checkpoints: `64, 256, 1024, 4096, 8192`
- Seed/split/family: `0xfb72` / `development` / `nominal`
- Boundary: corrected K-by-V GDN recurrence core
- Arithmetic: encoded E2M1 elements, E8M0 B32 scales, Q1.15 alpha/beta, ordered INT32 accumulation, RNE state write

| Token | Output cosine | Output rel L2 | State rel L2 | State max abs | Cum. element sat. | Cum. accum. sat. | Cum. scale clamps | Cum. align underflows |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 0.793927 | 0.963340 | 0.981956 | 0.491953 | 0 | 0 | 0 | 17273405 |
| 256 | 0.602197 | 1.755644 | 1.813634 | 0.642975 | 0 | 0 | 0 | 77557539 |
| 1024 | 0.456715 | 2.428815 | 2.349721 | 0.810808 | 0 | 0 | 0 | 330221280 |
| 4096 | 0.409596 | 2.664650 | 2.628354 | 1.128830 | 0 | 0 | 0 | 1335179208 |
| 8192 | 0.429834 | 2.589596 | 2.580730 | 1.110176 | 0 | 0 | 0 | 2685620693 |

This is a deterministic layer-boundary synthetic trace. It is not closed-loop model, routed FPGA, or board evidence.

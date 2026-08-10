# RS2 fold-write contiguous-bank experiment

This isolated variant adds two contiguous layer banks to the strongest fold-write parent.

Exact Csim passes. Final WNS is -2.966 ns, TNS is -66,301.594 ns,
and 64,439 setup endpoints fail. Hold is +0.010 ns.
Decision: `REJECT_CONTIGUOUS_BANKING_TIMING`. Vectorless power at the failed 4 ns target is diagnostic only.

## Worst-100 startpoint origins

| Origin | Paths |
|---|---:|
| `gmem4_state_input_load_fifo` | 80 |
| `load_snapshot` | 19 |
| `resident_uram_read_clock` | 1 |

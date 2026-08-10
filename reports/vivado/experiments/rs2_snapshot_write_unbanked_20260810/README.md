# RS2 unbanked snapshot-write experiment

This isolated variant adds snapshot-write locality to the strongest unbanked fold-write parent.

Exact Csim passes. Final WNS is -1.494 ns, TNS is -26,161.480 ns,
and 43,246 setup endpoints fail. Hold is +0.010 ns.
Decision: `REJECT_UNBANKED_SNAPSHOT_WRITE_TIMING`. Vectorless power at the failed 4 ns target is diagnostic only.

## Worst-100 startpoint origins

| Origin | Paths |
|---|---:|
| `fold` | 11 |
| `read_snapshot` | 1 |
| `reset_slot` | 1 |
| `resident_uram_read_clock` | 15 |
| `top_fsm` | 70 |
| `top_impl` | 2 |

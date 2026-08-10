# RS2 snapshot-write contiguous-bank experiment

This isolated variant adds snapshot-write locality to the two-bank fold-write parent.

Exact Csim passes. Final WNS is -3.623 ns, TNS is -86,731.445 ns,
and 67,782 setup endpoints fail. Hold is +0.010 ns.
Decision: `REJECT_SNAPSHOT_CONTIGUOUS_BANKING_TIMING`. Vectorless power at the failed 4 ns target is diagnostic only.

## Worst-100 startpoint origins

| Origin | Paths |
|---|---:|
| `top_fsm` | 100 |

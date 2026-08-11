# RS2 fold-write address max-fanout experiment

This RTL-only variant adds `max_fanout=16` to both registered fold-write addresses.
The matched parent RTL and inherited exact 64-token C-simulation evidence are unchanged.

Final WNS is -1.453 ns, TNS is -18,473.637 ns, and
35,126 setup endpoints fail. The targeted address
registers account for 4 of the worst 100 paths.
Decision: `REJECT_ADDRESS_FANOUT16_TIMING`. Vectorless power at the failed 4 ns target is diagnostic only.

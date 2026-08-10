# RS2 unbanked top-FSM max-fanout experiment

This RTL-only variant adds `max_fanout=16` to the exact unbanked snapshot-write parent.

Vivado created 326 replicated instances across 134 events. Final WNS is -2.686 ns, TNS is -58,498.117 ns, and 58,993 setup endpoints fail.
Decision: `REJECT_FSM_FANOUT16_TIMING`. Vectorless power at the failed 4 ns target is diagnostic only.

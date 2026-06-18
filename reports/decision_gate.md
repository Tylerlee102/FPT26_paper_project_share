# Phase 4 MXFP4 Decision Gate

Generated: 2026-05-21T18:22:35.484530+00:00

Overall status: **READY_FOR_HUMAN_GO**

Human decision required before proceeding beyond Phase 4. This report does not flip `USE_MXFP4`; proceed only after explicit human approval.

## Required Evidence

| Item | Status | Detail |
|---|---|---|
| Vitis HLS available | AVAILABLE | `C:/AMDDesignTools/2025.2/Vitis/bin/unwrapped/win64.o/vitis_hls.exe` |
| Latest `make hls-csim` | PRESENT | Found `reports/csim/results.md`; manual review required. |
| Latest `make hls-csynth` | PRESENT | Found `reports/csynth/gdn_top_csynth.rpt`; parser integration required. |
| `reports/csynth/util.md` | PRESENT | Found `reports/csynth/util.md`; manual review required. |
| Remaining work estimate | PRESENT | 0 person-days to Phase 5 readiness, assuming Vitis HLS is available. |

## Gate Criteria

| Criterion | Required | Current | Pass? |
|---|---:|---:|---|
| Csim bit-exact vectors | 32/32 | 64/64 | yes |
| Csynth Fmax | >= 200 MHz | 342.47 MHz | yes |
| Inner-loop II | 1 | 1 | yes |
| LUT utilization | < 80% | 19.02% | yes |
| BRAM utilization | < 80% | 7.34% | yes |
| Remaining work | <= 3 person-days | 0 person-days | yes |

## Recommendation

All machine-checkable Phase 4 criteria in this report pass. The human team may explicitly approve MXFP4 and proceed to Phase 5.

## Source Handoff

See `reports/csynth/handoff.md` for the Phase 3 source handoff.

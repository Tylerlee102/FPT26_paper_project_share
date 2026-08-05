# Native Encoded Long Trace Attempt 1

- Status: `FAIL`
- Command: `python -m scripts.native_encoded_long_trace`
- Termination: manual termination before completion
- Process cleanup: the shell pipeline terminated first; orphaned Python PID
  `2604` was then stopped explicitly before it reached checkpoint 4096.
- Completed snapshots: token 0, 64, 256, and 1024
- Reason: preflight review found that the runner compared against the nonexistent
  `input_stream_sha256` key in the established floating manifest; that manifest
  correctly uses `input_sha256`.

The run was stopped before token 8192 so valid compute time was not followed by
a deterministic final-write failure. These partial snapshots and the raw run
log are preserved for audit only and are not scientific evidence. Attempt-2
token-64 arrays were independently compared with this attempt and are exactly
equal; the canonical directory contains only attempt-2 checkpoint writes.

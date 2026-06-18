# Calibration Data

Calibration captures are not checked into git. The offline Phase 2 path writes
`scales.npz` from deterministic synthetic vectors and records its hash in
`manifest.sha256`.

Full acceptance still requires Qwen3-Next activation capture from HuggingFace and
Microsoft `microxcaling` parity. The Python dependencies for Qwen capture are
available through `pip install -e ".[full]"`; `scripts.qwen_status` reports
`capture_missing` when dependencies are present but the large `.npz` capture has
not been collected yet.

To collect the real acceptance artifact on a machine with enough disk, RAM, and
accelerator memory, run:

```text
make qwen-capture
make qwen-status
```

The capture path loads `Qwen/Qwen3-Next-80B-A3B-Instruct`, records layer-12
activations, writes `qwen3_next_80b_a3b_layer12.npz`, and emits a colocated
SHA256 manifest. The status checker validates the capture schema before marking
the Qwen evidence available.

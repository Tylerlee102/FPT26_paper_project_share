# Qwen Capture Status

Generated: deterministic local capture/dependency check

Status: available

- Capture file: `data/calibration/qwen3_next_80b_a3b_layer12.npz`
- Model: `Qwen/Qwen3-Next-80B-A3B-Instruct`
- Layer index: 12
- SHA256: `91fed973063039ce4519ef0276ac0f59bfec372ada0f80033047df368370f9b1`
- Size: 566285 bytes

Interpretation:

- A valid Qwen3-Next activation capture is present for calibration and range analysis.
- This status is not a GDN recurrence, perplexity, or model-quality result; those claims require a separate extraction containing the recurrent tensors.

Dependency check:

- torch: missing
- transformers: missing
- datasets: missing

Recapture note:

- The local capture can be inspected without the full Qwen runtime dependencies.
- Install the `full` optional dependency set only when refreshing or recollecting the activation capture.

# Qwen Capture Status

Generated: deterministic local capture/dependency check

Status: dependency_blocked

- Capture file: `data/calibration/qwen3_next_80b_a3b_layer12.npz`
- Model: `Qwen/Qwen3-Next-80B-A3B-Instruct`
- Layer index: 12
- SHA256: `91fed973063039ce4519ef0276ac0f59bfec372ada0f80033047df368370f9b1`
- Size: 566285 bytes

Dependency check:

- torch: missing
- transformers: missing
- datasets: missing

Resolution:

- Install the `full` optional dependency set before collecting Qwen activations.
- Capture data is intentionally not synthesized or substituted by the benchmark pipeline.

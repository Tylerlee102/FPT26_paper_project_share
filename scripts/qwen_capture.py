from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "Qwen/Qwen3-Next-80B-A3B-Instruct"
DEFAULT_OUTPUT = ROOT / "data" / "calibration" / "qwen3_next_80b_a3b_layer12.npz"
DEFAULT_PROMPTS = (
    "The quick brown fox explains block floating point arithmetic for FPGA accelerators.",
    "A single-token decode step updates recurrent state using keys, values, gates, and beta.",
    "Qwen3-Next uses a hybrid architecture with efficient activated parameters for inference.",
    "Hardware measurements must be traced to generated reports and deterministic captures.",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_output_for(model_id: str) -> Path:
    lowered = model_id.lower()
    if "80b" in lowered and "a3b" in lowered:
        return DEFAULT_OUTPUT
    if "1.5b" in lowered or "1p5b" in lowered or "1-5b" in lowered:
        return ROOT / "data" / "calibration" / "qwen3_next_1p5b_a3b_layer12.npz"
    return DEFAULT_OUTPUT


def _read_prompts(path: Path | None) -> list[str]:
    if path is None:
        return list(DEFAULT_PROMPTS)
    prompts = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in prompts if line and not line.startswith("#")]


def _find_layers(model: Any) -> Any:
    candidates = (
        ("model", "layers"),
        ("model", "decoder", "layers"),
        ("transformer", "h"),
        ("layers",),
    )
    for attrs in candidates:
        obj = model
        for attr in attrs:
            if not hasattr(obj, attr):
                break
            obj = getattr(obj, attr)
        else:
            if hasattr(obj, "__len__"):
                return obj
    raise RuntimeError("Could not locate transformer layers on the loaded model.")


def _tensor_to_numpy(value: Any, *, max_tokens: int) -> np.ndarray | None:
    try:
        import torch
    except Exception as exc:  # pragma: no cover - import guard for optional dependency
        raise RuntimeError("torch is required for Qwen capture") from exc

    if isinstance(value, (tuple, list)):
        value = next((item for item in value if isinstance(item, torch.Tensor)), None)
    if not isinstance(value, torch.Tensor):
        return None
    tensor = value.detach()
    if tensor.ndim >= 2:
        tensor = tensor[:, :max_tokens, ...]
    return tensor.to(device="cpu", dtype=torch.float32).numpy()


def _dtype_from_arg(torch: Any, value: str) -> Any:
    if value == "auto":
        return "auto"
    mapping = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    return mapping[value]


def _write_manifest(path: Path) -> Path:
    manifest = path.with_suffix(path.suffix + ".sha256")
    manifest.write_text(f"{_sha256_file(path)}  {path.as_posix()}\n", encoding="utf-8")
    return manifest


def preflight_qwen_capture(
    *,
    model_id: str,
    model_path: Path | None,
    output: Path,
    torch_dtype: str,
    experts_implementation: str | None,
    trust_remote_code: bool,
    revision: str | None,
    local_files_only: bool,
    token_env: str,
) -> dict[str, object]:
    try:
        import torch
        from transformers import AutoConfig, AutoTokenizer
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError("Install the qwen/full dependencies before running Qwen capture.") from exc

    if not model_id.startswith("Qwen/Qwen3-Next-"):
        raise ValueError(
            "Refusing to write an acceptance capture for a non-Qwen3-Next model. "
            "Use a canonical Qwen/Qwen3-Next-* model id."
        )
    if model_path is not None and not model_path.exists():
        raise FileNotFoundError(f"Local model path does not exist: {model_path}")

    output.parent.mkdir(parents=True, exist_ok=True)
    probe = output.parent / ".qwen_capture_preflight.tmp"
    probe.write_text("ok\n", encoding="utf-8")
    probe.unlink()

    load_target = str(model_path) if model_path is not None else model_id
    token = os.environ.get(token_env) or None
    load_kwargs: dict[str, Any] = {
        "revision": revision,
        "trust_remote_code": trust_remote_code,
        "local_files_only": local_files_only,
        "token": token,
    }
    tokenizer = AutoTokenizer.from_pretrained(load_target, **load_kwargs)
    config = AutoConfig.from_pretrained(load_target, **load_kwargs)
    if experts_implementation:
        config._experts_implementation = experts_implementation
    _dtype_from_arg(torch, torch_dtype)
    tokenized = tokenizer("preflight", return_tensors="pt")
    if "input_ids" not in tokenized or tokenized["input_ids"].numel() == 0:
        raise RuntimeError("Tokenizer preflight did not produce input_ids.")

    gpu_name = None
    gpu_capability = None
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_capability = ".".join(str(part) for part in torch.cuda.get_device_capability(0))
        if "B200" in gpu_name and experts_implementation != "eager":
            raise RuntimeError(
                "B200 preflight requires `--experts-implementation eager`; the default grouped MoE path "
                "uses a PyTorch grouped_mm kernel that is not supported by this image on B200."
            )

    return {
        "status": "ok",
        "model_id": model_id,
        "load_target": load_target,
        "output": output.as_posix(),
        "torch_dtype": torch_dtype,
        "experts_implementation": experts_implementation or "default",
        "tokenizer": type(tokenizer).__name__,
        "config": type(config).__name__,
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": gpu_name,
        "gpu_capability": gpu_capability,
    }


def capture_qwen_activations(
    *,
    model_id: str,
    model_path: Path | None,
    output: Path,
    prompts: list[str],
    layer_index: int,
    max_length: int,
    max_capture_tokens: int,
    torch_dtype: str,
    device_map: str,
    experts_implementation: str | None,
    trust_remote_code: bool,
    revision: str | None,
    local_files_only: bool,
    token_env: str,
) -> tuple[Path, Path]:
    try:
        import torch
        import transformers
        from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError("Install the qwen/full dependencies before running Qwen capture.") from exc

    if not model_id.startswith("Qwen/Qwen3-Next-"):
        raise ValueError(
            "Refusing to write an acceptance capture for a non-Qwen3-Next model. "
            "Use a canonical Qwen/Qwen3-Next-* model id."
        )

    token = os.environ.get(token_env) or None
    load_target = str(model_path) if model_path is not None else model_id
    load_kwargs: dict[str, Any] = {
        "revision": revision,
        "trust_remote_code": trust_remote_code,
        "local_files_only": local_files_only,
        "token": token,
    }
    tokenizer = AutoTokenizer.from_pretrained(load_target, **load_kwargs)
    dtype = _dtype_from_arg(torch, torch_dtype)
    model_kwargs = {
        **load_kwargs,
        "torch_dtype": dtype,
        "low_cpu_mem_usage": True,
    }
    if experts_implementation:
        config = AutoConfig.from_pretrained(load_target, **load_kwargs)
        config._experts_implementation = experts_implementation
        model_kwargs["config"] = config
    if device_map != "none":
        model_kwargs["device_map"] = device_map
    model = AutoModelForCausalLM.from_pretrained(load_target, **model_kwargs)
    model.eval()

    layers = _find_layers(model)
    if layer_index < 0 or layer_index >= len(layers):
        raise IndexError(f"Layer index {layer_index} is outside the model depth {len(layers)}.")
    layer = layers[layer_index]

    captures: dict[str, list[np.ndarray]] = {"layer_input": [], "layer_output": []}

    def layer_hook(_module: Any, inputs: tuple[Any, ...], output_value: Any) -> None:
        layer_in = _tensor_to_numpy(inputs[0] if inputs else None, max_tokens=max_capture_tokens)
        layer_out = _tensor_to_numpy(output_value, max_tokens=max_capture_tokens)
        if layer_in is not None:
            captures["layer_input"].append(layer_in)
        if layer_out is not None:
            captures["layer_output"].append(layer_out)

    handles = [layer.register_forward_hook(layer_hook)]

    interesting = ("q_proj", "k_proj", "v_proj", "gate", "beta", "delta", "value")
    for name, module in layer.named_modules():
        if not name:
            continue
        if any(part in name.lower() for part in interesting):
            key = name.replace(".", "_")
            captures[key] = []

            def make_hook(capture_key: str):
                def hook(_module: Any, _inputs: tuple[Any, ...], output_value: Any) -> None:
                    array = _tensor_to_numpy(output_value, max_tokens=max_capture_tokens)
                    if array is not None:
                        captures[capture_key].append(array)

                return hook

            handles.append(module.register_forward_hook(make_hook(key)))

    encoded = tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_length,
    )
    input_device = next(model.parameters()).device
    encoded = {key: value.to(input_device) for key, value in encoded.items()}

    try:
        with torch.inference_mode():
            model(**encoded, use_cache=False)
    finally:
        for handle in handles:
            handle.remove()

    arrays: dict[str, np.ndarray] = {
        "input_ids": encoded["input_ids"].detach().to("cpu").numpy().astype(np.int64),
        "attention_mask": encoded["attention_mask"].detach().to("cpu").numpy().astype(np.int64),
    }
    for key, values in captures.items():
        if values:
            arrays[key] = np.concatenate(values, axis=0).astype(np.float32, copy=False)

    if "layer_input" not in arrays or "layer_output" not in arrays:
        raise RuntimeError("Layer hook did not capture both input and output activations.")

    prompt_blob = "\n".join(prompts).encode("utf-8")
    metadata = {
        "schema": 1,
        "source": "huggingface_qwen3_next",
        "model_id": model_id,
        "model_path": str(model_path) if model_path is not None else None,
        "experts_implementation": experts_implementation or "default",
        "revision": revision or "default",
        "timestamp": datetime.now(UTC).isoformat(),
        "layer_index": layer_index,
        "num_prompts": len(prompts),
        "max_length": max_length,
        "max_capture_tokens": max_capture_tokens,
        "prompt_sha256": _sha256_bytes(prompt_blob),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "captured_arrays": sorted(arrays),
    }
    arrays["metadata_json"] = np.array(json.dumps(metadata, sort_keys=True))

    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **arrays)
    manifest = _write_manifest(output)
    return output, manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture real Qwen3-Next layer activations for calibration.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--model-path", type=Path, help="Optional local from_pretrained path for cached weights.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prompts", type=Path, help="Optional newline-delimited prompt file.")
    parser.add_argument("--layer-index", type=int, default=12)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--max-capture-tokens", type=int, default=32)
    parser.add_argument("--torch-dtype", choices=["auto", "float32", "float16", "bfloat16"], default="auto")
    parser.add_argument("--device-map", default="auto", help="Use 'none' to keep the model on the default device.")
    parser.add_argument(
        "--experts-implementation",
        choices=["eager", "grouped_mm", "batched_mm", "deepgemm", "sonicmoe"],
        help="Optional Transformers MoE experts implementation override.",
    )
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--revision")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--preflight-only", action="store_true", help="Validate capture setup without loading weights.")
    args = parser.parse_args(argv)

    output = args.output or _canonical_output_for(args.model)
    preflight = preflight_qwen_capture(
        model_id=args.model,
        model_path=args.model_path,
        output=output,
        torch_dtype=args.torch_dtype,
        experts_implementation=args.experts_implementation,
        trust_remote_code=args.trust_remote_code,
        revision=args.revision,
        local_files_only=args.local_files_only,
        token_env=args.token_env,
    )
    print(json.dumps({"preflight": preflight}, indent=2), flush=True)
    if args.preflight_only:
        return 0

    prompts = _read_prompts(args.prompts)
    capture, manifest = capture_qwen_activations(
        model_id=args.model,
        model_path=args.model_path,
        output=output,
        prompts=prompts,
        layer_index=args.layer_index,
        max_length=args.max_length,
        max_capture_tokens=args.max_capture_tokens,
        torch_dtype=args.torch_dtype,
        device_map=args.device_map,
        experts_implementation=args.experts_implementation,
        trust_remote_code=args.trust_remote_code,
        revision=args.revision,
        local_files_only=args.local_files_only,
        token_env=args.token_env,
    )
    print(json.dumps({"capture": capture.relative_to(ROOT).as_posix(), "manifest": manifest.relative_to(ROOT).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

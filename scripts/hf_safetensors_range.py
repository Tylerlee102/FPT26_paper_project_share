"""Extract selected public Hugging Face safetensors with HTTP range reads."""

from __future__ import annotations

import hashlib
import json
import struct
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np


DTYPE_SIZES = {"BF16": 2, "F16": 2, "F32": 4}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_json(url: str, *, timeout: int = 120) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "gdn-fpga-research/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_range(url: str, start: int, end: int, *, timeout: int = 300) -> tuple[bytes, int]:
    if start < 0 or end < start:
        raise ValueError("invalid byte range")
    request = urllib.request.Request(
        url,
        headers={
            "Range": f"bytes={start}-{end}",
            "User-Agent": "gdn-fpga-research/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
        content_range = response.headers.get("Content-Range", "")
        status = getattr(response, "status", None)
    if status != 206:
        raise RuntimeError(f"server did not honor range request: HTTP {status}")
    expected_prefix = f"bytes {start}-{end}/"
    if not content_range.startswith(expected_prefix):
        raise RuntimeError(f"unexpected Content-Range: {content_range!r}")
    if len(payload) != end - start + 1:
        raise RuntimeError("range response length does not match request")
    total_size = int(content_range.rsplit("/", 1)[1])
    return payload, total_size


def safetensors_header(url: str) -> tuple[dict[str, object], int, int]:
    prefix, file_size = fetch_range(url, 0, 7)
    header_size = struct.unpack("<Q", prefix)[0]
    if header_size <= 0 or header_size > 64 * 1024 * 1024:
        raise RuntimeError(f"implausible safetensors header size: {header_size}")
    raw_header, second_size = fetch_range(url, 8, 8 + header_size - 1)
    if second_size != file_size:
        raise RuntimeError("file size changed while reading safetensors header")
    header = json.loads(raw_header.decode("utf-8").rstrip())
    return header, 8 + header_size, file_size


def extract_selected_tensors(
    *,
    model_id: str,
    revision: str,
    shard: str,
    tensor_aliases: dict[str, str],
    output: Path,
) -> dict[str, object]:
    url = f"https://huggingface.co/{model_id}/resolve/{revision}/{shard}"
    header, data_start, file_size = safetensors_header(url)
    entries: dict[str, dict[str, object]] = {}
    for tensor_name in tensor_aliases:
        entry = header.get(tensor_name)
        if not isinstance(entry, dict):
            raise KeyError(f"tensor is absent from shard: {tensor_name}")
        dtype = str(entry["dtype"])
        if dtype not in DTYPE_SIZES:
            raise ValueError(f"unsupported safetensors dtype {dtype} for {tensor_name}")
        shape = [int(value) for value in entry["shape"]]
        offsets = [int(value) for value in entry["data_offsets"]]
        expected_bytes = int(np.prod(shape, dtype=np.int64)) * DTYPE_SIZES[dtype]
        if offsets[1] - offsets[0] != expected_bytes:
            raise RuntimeError(f"tensor byte count mismatch for {tensor_name}")
        entries[tensor_name] = {"dtype": dtype, "shape": shape, "data_offsets": offsets}

    first = min(int(entry["data_offsets"][0]) for entry in entries.values())
    last = max(int(entry["data_offsets"][1]) for entry in entries.values())
    span, second_size = fetch_range(url, data_start + first, data_start + last - 1)
    if second_size != file_size:
        raise RuntimeError("file size changed while extracting tensor data")

    arrays: dict[str, np.ndarray] = {}
    tensor_manifest: dict[str, object] = {}
    for tensor_name, entry in entries.items():
        start, end = (int(value) for value in entry["data_offsets"])
        raw = span[start - first : end - first]
        dtype = str(entry["dtype"])
        storage_dtype = {"BF16": "<u2", "F16": "<f2", "F32": "<f4"}[dtype]
        array = np.frombuffer(raw, dtype=storage_dtype).reshape(entry["shape"]).copy()
        alias = tensor_aliases[tensor_name]
        arrays[alias] = array
        tensor_manifest[alias] = {
            "source_name": tensor_name,
            **entry,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }

    metadata = {
        "schema": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_id": model_id,
        "revision": revision,
        "shard": shard,
        "source_url": url,
        "source_file_bytes": file_size,
        "header_bytes": data_start - 8,
        "range_start": data_start + first,
        "range_end": data_start + last - 1,
        "range_bytes": len(span),
        "tensors": tensor_manifest,
    }
    arrays["metadata_json"] = np.array(json.dumps(metadata, sort_keys=True))
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **arrays)
    digest = sha256_file(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.as_posix()}\n", encoding="utf-8"
    )
    metadata["output_sha256"] = digest
    return metadata


def current_model_revision(model_id: str) -> str:
    payload = fetch_json(f"https://huggingface.co/api/models/{model_id}")
    revision = payload.get("sha")
    if not isinstance(revision, str) or len(revision) != 40:
        raise RuntimeError("Hugging Face model API did not return a commit SHA")
    return revision


def bf16_storage_to_float32(array: np.ndarray) -> np.ndarray:
    raw = np.asarray(array)
    if raw.dtype != np.dtype("uint16"):
        raise TypeError(f"expected BF16 uint16 storage, got {raw.dtype}")
    widened = raw.astype(np.uint32) << np.uint32(16)
    return widened.view(np.float32)


def validate_aliases(aliases: Iterable[str]) -> None:
    values = list(aliases)
    if len(values) != len(set(values)):
        raise ValueError("tensor aliases must be unique")
    if any(not value or value == "metadata_json" for value in values):
        raise ValueError("invalid tensor alias")

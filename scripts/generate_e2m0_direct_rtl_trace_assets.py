"""Convert the frozen E2M0 64-token oracle trace into readmemh assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "data" / "vectors" / "e2m0_resident_trace64.bin"
TRACE_MANIFEST = TRACE.with_name("e2m0_resident_trace64_manifest.json")
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "cosim"
    / "corrected"
    / "e2m0_direct_rtl_trace64"
    / "assets"
)
HEADER = struct.Struct("<8s10I")
MAGIC = b"E2M0T01\0"
VERSION = 1
ENDIAN_MARKER = 0x01020304


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _take(payload: memoryview, offset: int, size: int) -> tuple[bytes, int]:
    stop = offset + size
    if stop > len(payload):
        raise ValueError(f"short E2M0 trace at byte {offset}; need {size} bytes")
    return bytes(payload[offset:stop]), stop


def _take_words(
    payload: memoryview,
    offset: int,
    count: int,
    code: str,
) -> tuple[list[int], int]:
    width = struct.calcsize(code)
    chunk, offset = _take(payload, offset, count * width)
    return list(struct.unpack(f"<{count}{code}", chunk)), offset


def _write_hex(path: Path, values: Iterable[int], digits: int) -> int:
    count = 0
    with path.open("w", encoding="ascii", newline="\n") as handle:
        pending: list[str] = []
        for value in values:
            pending.append(f"{value:0{digits}x}\n")
            count += 1
            if len(pending) == 65536:
                handle.write("".join(pending))
                pending.clear()
        if pending:
            handle.write("".join(pending))
    return count


def _read_snapshot(
    payload: memoryview,
    offset: int,
    dimensions: dict[str, int],
) -> tuple[dict[str, object], int]:
    snapshot: dict[str, object] = {}
    for name, count in (
        ("primary", dimensions["state_elements"]),
        ("primary_scales", dimensions["state_scales"]),
        ("residual", dimensions["state_elements"]),
        ("residual_scales", dimensions["state_scales"]),
        ("log_keys", dimensions["log_key_elements"]),
        ("log_key_scales", dimensions["log_key_scales"]),
        ("log_updates", dimensions["log_update_elements"]),
        ("log_update_scales", dimensions["log_update_scales"]),
    ):
        snapshot[name], offset = _take(payload, offset, count)
    snapshot["gamma"], offset = _take_words(
        payload, offset, dimensions["gamma_elements"], "H"
    )
    snapshot["lambda"], offset = _take_words(
        payload, offset, dimensions["lambda_elements"], "H"
    )
    return snapshot, offset


def parse_trace(trace_path: Path = TRACE) -> dict[str, object]:
    payload = memoryview(trace_path.read_bytes())
    if len(payload) < HEADER.size:
        raise ValueError("E2M0 trace is shorter than its header")
    (
        magic,
        version,
        endian,
        tokens,
        qk_heads,
        value_heads,
        key_dim,
        value_dim,
        block_size,
        stack_depth,
        log_capacity,
    ) = HEADER.unpack_from(payload, 0)
    expected = (64, 16, 32, 128, 128, 32, 2, 7)
    actual = (
        tokens,
        qk_heads,
        value_heads,
        key_dim,
        value_dim,
        block_size,
        stack_depth,
        log_capacity,
    )
    if (magic, version, endian) != (MAGIC, VERSION, ENDIAN_MARKER):
        raise ValueError("E2M0 trace identity header mismatch")
    if actual != expected:
        raise ValueError(f"E2M0 trace dimensions {actual} do not match {expected}")

    q_elements = stack_depth * qk_heads * key_dim
    q_scales = stack_depth * qk_heads * (key_dim // block_size)
    v_elements = stack_depth * value_heads * value_dim
    v_scales = stack_depth * value_heads * (value_dim // block_size)
    state_elements = value_heads * key_dim * value_dim
    state_scales = value_heads * key_dim * (value_dim // block_size)
    log_key_elements = log_capacity * stack_depth * qk_heads * key_dim
    log_key_scales = (
        log_capacity * stack_depth * qk_heads * (key_dim // block_size)
    )
    log_update_elements = log_capacity * stack_depth * value_heads * value_dim
    log_update_scales = (
        log_capacity * stack_depth * value_heads * (value_dim // block_size)
    )
    dimensions = {
        "tokens": tokens,
        "num_qk_heads": qk_heads,
        "num_value_heads": value_heads,
        "key_dim": key_dim,
        "value_dim": value_dim,
        "block_size": block_size,
        "stack_depth": stack_depth,
        "log_capacity": log_capacity,
        "counter_count": 8,
        "q_elements": q_elements,
        "q_scales": q_scales,
        "v_elements": v_elements,
        "v_scales": v_scales,
        "gate_elements": value_heads,
        "output_elements": value_heads * value_dim,
        "state_elements": state_elements,
        "state_scales": state_scales,
        "log_key_elements": log_key_elements,
        "log_key_scales": log_key_scales,
        "log_update_elements": log_update_elements,
        "log_update_scales": log_update_scales,
        "gamma_elements": value_heads,
        "lambda_elements": log_capacity * value_heads,
    }
    offset = HEADER.size
    initial, offset = _read_snapshot(payload, offset, dimensions)
    initial_live_raw, offset = _take(payload, offset, 1)
    initial["live"] = initial_live_raw[0]

    byte_stream_names = ("q", "q_scales", "k", "k_scales", "v", "v_scales")
    streams: dict[str, list[int]] = {name: [] for name in byte_stream_names}
    streams.update({"alpha": [], "beta": []})
    expected: dict[str, list[int]] = {
        "status": [],
        "generation": [],
        "live": [],
        "command_counters": [],
        "cumulative_counters": [],
        "output_mantissas": [],
        "output_exponents": [],
    }
    for _ in range(tokens):
        for name, count in (
            ("q", q_elements),
            ("q_scales", q_scales),
            ("k", q_elements),
            ("k_scales", q_scales),
            ("v", v_elements),
            ("v_scales", v_scales),
        ):
            chunk, offset = _take(payload, offset, count)
            streams[name].extend(chunk)
        for name in ("alpha", "beta"):
            words, offset = _take_words(payload, offset, value_heads, "H")
            streams[name].extend(words)
        chunk, offset = _take(payload, offset, 1)
        expected["status"].append(chunk[0])
        words, offset = _take_words(payload, offset, 1, "Q")
        expected["generation"].extend(words)
        chunk, offset = _take(payload, offset, 1)
        expected["live"].append(chunk[0])
        for name in ("command_counters", "cumulative_counters"):
            words, offset = _take_words(payload, offset, 8, "Q")
            expected[name].extend(words)
        words, offset = _take_words(
            payload, offset, dimensions["output_elements"], "I"
        )
        expected["output_mantissas"].extend(words)
        words, offset = _take_words(
            payload, offset, dimensions["output_elements"], "H"
        )
        expected["output_exponents"].extend(words)

    final, offset = _read_snapshot(payload, offset, dimensions)
    chunk, offset = _take(payload, offset, 1)
    final["live"] = chunk[0]
    chunk, offset = _take(payload, offset, 1)
    final["status"] = chunk[0]
    words, offset = _take_words(payload, offset, 1, "Q")
    final["generation"] = words[0]
    words, offset = _take_words(payload, offset, 8, "Q")
    final["cumulative_counters"] = words
    if offset != len(payload):
        raise ValueError(f"E2M0 trace has {len(payload) - offset} trailing bytes")
    return {
        "dimensions": dimensions,
        "initial": initial,
        "streams": streams,
        "expected": expected,
        "final": final,
    }


def generate_assets(
    trace_path: Path = TRACE,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, object]:
    source_manifest_path = trace_path.with_name(f"{trace_path.stem}_manifest.json")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("status") != "PASS":
        raise ValueError("source E2M0 oracle manifest is not PASS")
    if str(source_manifest.get("trace_sha256", "")).upper() != _sha256(trace_path):
        raise ValueError("source E2M0 trace hash does not match its manifest")
    parsed = parse_trace(trace_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    initial = parsed["initial"]
    streams = parsed["streams"]
    expected = parsed["expected"]
    final = parsed["final"]
    assets: dict[str, tuple[Iterable[int], int]] = {}
    for name, values in initial.items():
        assets[f"initial_{name}"] = ([values] if isinstance(values, int) else values, 4 if name in {"gamma", "lambda"} else 2)
    for name, values in streams.items():
        assets[name] = (values, 4 if name in {"alpha", "beta"} else 2)
    for name, values in expected.items():
        digits = 16 if name in {"generation", "command_counters", "cumulative_counters"} else 8 if name == "output_mantissas" else 4 if name == "output_exponents" else 2
        assets[name] = (values, digits)
    for name, values in final.items():
        digits = 16 if name in {"generation", "cumulative_counters"} else 4 if name in {"gamma", "lambda"} else 2
        assets[f"final_{name}"] = ([values] if isinstance(values, int) else values, digits)

    files: dict[str, dict[str, object]] = {}
    for name, (values, digits) in assets.items():
        path = output_dir / f"{name}.hex"
        count = _write_hex(path, values, digits)
        files[path.name] = {
            "elements": count,
            "digits": digits,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
    manifest: dict[str, object] = {
        "schema": 1,
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_trace": {
            "path": trace_path.resolve().relative_to(ROOT.resolve()).as_posix(),
            "bytes": trace_path.stat().st_size,
            "sha256": _sha256(trace_path),
            "manifest": source_manifest_path.resolve().relative_to(ROOT.resolve()).as_posix(),
            "manifest_sha256": _sha256(source_manifest_path),
        },
        "dimensions": parsed["dimensions"],
        "initial": {"live": initial["live"]},
        "readback": {
            "live": final["live"],
            "status": final["status"],
            "generation": final["generation"],
        },
        "files": files,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=TRACE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    trace = args.trace if args.trace.is_absolute() else ROOT / args.trace
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    manifest = generate_assets(trace, output)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "tokens": manifest["dimensions"]["tokens"],
                "files": len(manifest["files"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

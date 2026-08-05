"""Convert the verified 64-token HLS oracle trace into XSIM readmemh assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .generate_hls_command_trace import COUNTER_FIELDS, ENDIAN_MARKER, MAGIC, VERSION
from .verify_hls_command_trace import TRACE, verify_trace


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "cosim" / "corrected" / "direct_rtl_trace64" / "assets"
HEADER = struct.Struct("<8s8I")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _take(payload: memoryview, offset: int, size: int) -> tuple[bytes, int]:
    stop = offset + size
    if stop > len(payload):
        raise ValueError(f"short trace at byte {offset}; need {size} bytes")
    return bytes(payload[offset:stop]), stop


def parse_trace(trace_path: Path = TRACE) -> dict[str, object]:
    payload = memoryview(trace_path.read_bytes())
    if len(payload) < HEADER.size:
        raise ValueError("trace is shorter than its header")
    header = HEADER.unpack_from(payload, 0)
    (
        magic,
        version,
        endian_marker,
        tokens,
        num_qk_heads,
        num_value_heads,
        key_dim,
        value_dim,
        block_size,
    ) = header
    if (magic, version, endian_marker) != (MAGIC, VERSION, ENDIAN_MARKER):
        raise ValueError("trace identity header mismatch")
    if (tokens, num_qk_heads, num_value_heads, key_dim, value_dim, block_size) != (
        64,
        16,
        32,
        128,
        128,
        32,
    ):
        raise ValueError("trace dimensions do not match the synthesized kernel")

    q_bytes = num_qk_heads * key_dim
    q_scale_bytes = num_qk_heads * (key_dim // block_size)
    v_bytes = num_value_heads * value_dim
    v_scale_bytes = num_value_heads * (value_dim // block_size)
    gate_bytes = num_value_heads * 2
    output_elements = num_value_heads * value_dim
    counter_count = len(COUNTER_FIELDS)
    streams: dict[str, bytearray] = {
        name: bytearray()
        for name in (
            "q",
            "q_scales",
            "k",
            "k_scales",
            "v",
            "v_scales",
            "alpha",
            "beta",
        )
    }
    status: list[int] = []
    generation: list[int] = []
    command_counters: list[int] = []
    cumulative_counters: list[int] = []
    output_mantissas: list[int] = []
    output_exponents: list[int] = []
    offset = HEADER.size

    for _ in range(tokens):
        for name, size in (
            ("q", q_bytes),
            ("q_scales", q_scale_bytes),
            ("k", q_bytes),
            ("k_scales", q_scale_bytes),
            ("v", v_bytes),
            ("v_scales", v_scale_bytes),
            ("alpha", gate_bytes),
            ("beta", gate_bytes),
        ):
            chunk, offset = _take(payload, offset, size)
            streams[name].extend(chunk)
        chunk, offset = _take(payload, offset, 1)
        status.append(chunk[0])
        chunk, offset = _take(payload, offset, 8)
        generation.append(struct.unpack("<Q", chunk)[0])
        chunk, offset = _take(payload, offset, counter_count * 8)
        command_counters.extend(struct.unpack(f"<{counter_count}Q", chunk))
        chunk, offset = _take(payload, offset, counter_count * 8)
        cumulative_counters.extend(struct.unpack(f"<{counter_count}Q", chunk))
        chunk, offset = _take(payload, offset, output_elements * 4)
        output_mantissas.extend(struct.unpack(f"<{output_elements}I", chunk))
        chunk, offset = _take(payload, offset, output_elements * 2)
        output_exponents.extend(struct.unpack(f"<{output_elements}H", chunk))

    final_state, offset = _take(payload, offset, num_value_heads * key_dim * value_dim)
    final_scales, offset = _take(
        payload,
        offset,
        num_value_heads * key_dim * (value_dim // block_size),
    )
    chunk, offset = _take(payload, offset, 1)
    readback_status = chunk[0]
    chunk, offset = _take(payload, offset, 8)
    readback_generation = struct.unpack("<Q", chunk)[0]
    chunk, offset = _take(payload, offset, counter_count * 8)
    readback_counters = list(struct.unpack(f"<{counter_count}Q", chunk))
    if offset != len(payload):
        raise ValueError(f"trace has {len(payload) - offset} trailing bytes")

    return {
        "dimensions": {
            "tokens": tokens,
            "num_qk_heads": num_qk_heads,
            "num_value_heads": num_value_heads,
            "key_dim": key_dim,
            "value_dim": value_dim,
            "block_size": block_size,
            "counter_count": counter_count,
            "output_elements": output_elements,
        },
        "streams": {name: bytes(values) for name, values in streams.items()},
        "status": status,
        "generation": generation,
        "command_counters": command_counters,
        "cumulative_counters": cumulative_counters,
        "output_mantissas": output_mantissas,
        "output_exponents": output_exponents,
        "final_state": final_state,
        "final_scales": final_scales,
        "readback_status": readback_status,
        "readback_generation": readback_generation,
        "readback_counters": readback_counters,
    }


def _write_hex(path: Path, values: Iterable[int], digits: int) -> int:
    count = 0
    with path.open("w", encoding="ascii", newline="\n") as handle:
        chunk: list[str] = []
        for value in values:
            chunk.append(f"{value:0{digits}x}\n")
            count += 1
            if len(chunk) == 65536:
                handle.write("".join(chunk))
                chunk.clear()
        if chunk:
            handle.write("".join(chunk))
    return count


def generate_assets(
    trace_path: Path = TRACE,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, object]:
    if trace_path.resolve() == TRACE.resolve():
        verification = verify_trace(trace_path=trace_path)
        if verification["status"] != "PASS":
            raise ValueError("source oracle trace verification did not pass")
    parsed = parse_trace(trace_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    assets: dict[str, tuple[Iterable[int], int]] = {
        **{name: (values, 2) for name, values in parsed["streams"].items()},
        "status": (parsed["status"], 2),
        "generation": (parsed["generation"], 16),
        "command_counters": (parsed["command_counters"], 16),
        "cumulative_counters": (parsed["cumulative_counters"], 16),
        "output_mantissas": (parsed["output_mantissas"], 8),
        "output_exponents": (parsed["output_exponents"], 4),
        "final_state": (parsed["final_state"], 2),
        "final_scales": (parsed["final_scales"], 2),
        "readback_counters": (parsed["readback_counters"], 16),
    }
    file_manifest: dict[str, dict[str, object]] = {}
    for name, (values, digits) in assets.items():
        path = output_dir / f"{name}.hex"
        count = _write_hex(path, values, digits)
        file_manifest[path.name] = {
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
        },
        "dimensions": parsed["dimensions"],
        "readback": {
            "status": parsed["readback_status"],
            "generation": parsed["readback_generation"],
        },
        "files": file_manifest,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
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

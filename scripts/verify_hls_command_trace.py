from __future__ import annotations

import csv
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

from .generate_hls_command_trace import COUNTER_FIELDS, ENDIAN_MARKER, MAGIC, VERSION


ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "data" / "vectors" / "corrected_gdn_command_trace.bin"
SUMMARY = ROOT / "reports" / "golden" / "corrected_hls_command_trace.csv"
MANIFEST = (
    ROOT / "reports" / "golden" / "corrected_hls_command_trace_manifest.json"
)
OUTPUT = (
    ROOT
    / "reports"
    / "golden"
    / "corrected_hls_command_trace_verification.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _take(payload: memoryview, offset: int, size: int) -> tuple[memoryview, int]:
    stop = offset + size
    if stop > len(payload):
        raise ValueError(f"short trace at byte {offset}; need {size} bytes")
    return payload[offset:stop], stop


def verify_trace(
    trace_path: Path = TRACE,
    summary_path: Path = SUMMARY,
    manifest_path: Path = MANIFEST,
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = memoryview(trace_path.read_bytes())
    header_size = struct.calcsize("<8s8I")
    if len(payload) < header_size:
        raise ValueError("trace is shorter than its header")
    header = struct.unpack_from("<8s8I", payload, 0)
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
    expected_header = (MAGIC, VERSION, ENDIAN_MARKER, 64, 16, 32, 128, 128, 32)
    if header != expected_header:
        raise ValueError(f"trace header mismatch: {header!r}")

    q_elements_bytes = num_qk_heads * key_dim
    q_scales_bytes = num_qk_heads * (key_dim // block_size)
    v_elements_bytes = num_value_heads * value_dim
    v_scales_bytes = num_value_heads * (value_dim // block_size)
    gate_bytes = num_value_heads * 2
    output_mantissa_bytes = num_value_heads * value_dim * 4
    output_exponent_bytes = num_value_heads * value_dim * 2
    counters_bytes = len(COUNTER_FIELDS) * 8
    input_sizes = (
        q_elements_bytes,
        q_scales_bytes,
        q_elements_bytes,
        q_scales_bytes,
        v_elements_bytes,
        v_scales_bytes,
        gate_bytes,
        gate_bytes,
    )

    with summary_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != tokens:
        raise ValueError(f"summary row count is {len(rows)}, expected {tokens}")

    input_digest = hashlib.sha256()
    offset = header_size
    final_generation = 0
    final_counters: tuple[int, ...] = ()
    for token_index in range(tokens):
        for size in input_sizes:
            chunk, offset = _take(payload, offset, size)
            input_digest.update(chunk)
        status_chunk, offset = _take(payload, offset, 1)
        status = int(status_chunk[0])
        generation_chunk, offset = _take(payload, offset, 8)
        generation = struct.unpack_from("<Q", generation_chunk, 0)[0]
        command_chunk, offset = _take(payload, offset, counters_bytes)
        command_counters = struct.unpack_from("<8Q", command_chunk, 0)
        cumulative_chunk, offset = _take(payload, offset, counters_bytes)
        cumulative_counters = struct.unpack_from("<8Q", cumulative_chunk, 0)
        _, offset = _take(payload, offset, output_mantissa_bytes)
        _, offset = _take(payload, offset, output_exponent_bytes)

        row = rows[token_index]
        if int(row["token_index"]) != token_index + 1:
            raise ValueError(f"summary token index mismatch at row {token_index + 1}")
        if status != int(row["status"]) or status != 0:
            raise ValueError(f"status mismatch at token {token_index + 1}")
        if generation != int(row["generation"]) or generation != token_index + 1:
            raise ValueError(f"generation mismatch at token {token_index + 1}")
        for index, field in enumerate(COUNTER_FIELDS):
            if command_counters[index] != int(row[f"command_{field}"]):
                raise ValueError(
                    f"command counter {field} mismatch at token {token_index + 1}"
                )
            if cumulative_counters[index] != int(row[f"cumulative_{field}"]):
                raise ValueError(
                    f"cumulative counter {field} mismatch at token {token_index + 1}"
                )
        final_generation = generation
        final_counters = cumulative_counters

    state_bytes = num_value_heads * key_dim * value_dim
    state_scale_bytes = num_value_heads * key_dim * (value_dim // block_size)
    _, offset = _take(payload, offset, state_bytes)
    _, offset = _take(payload, offset, state_scale_bytes)
    readback_status_chunk, offset = _take(payload, offset, 1)
    readback_generation_chunk, offset = _take(payload, offset, 8)
    readback_counters_chunk, offset = _take(payload, offset, counters_bytes)
    if offset != len(payload):
        raise ValueError(f"trace has {len(payload) - offset} trailing bytes")
    readback_status = int(readback_status_chunk[0])
    readback_generation = struct.unpack_from("<Q", readback_generation_chunk, 0)[0]
    readback_counters = struct.unpack_from("<8Q", readback_counters_chunk, 0)
    if readback_status != 0 or readback_generation != final_generation:
        raise ValueError("final readback metadata does not match the token trace")
    if readback_counters != final_counters:
        raise ValueError("final readback counters do not match the last token")

    trace_hash = _sha256(trace_path)
    summary_hash = _sha256(summary_path)
    if trace_hash != manifest["binary"]["sha256"]:
        raise ValueError("trace SHA256 does not match manifest")
    if len(payload) != manifest["binary"]["bytes"]:
        raise ValueError("trace byte length does not match manifest")
    if summary_hash != manifest["summary_csv"]["sha256"]:
        raise ValueError("summary SHA256 does not match manifest")
    if input_digest.hexdigest().upper() != manifest["input_stream_sha256"]:
        raise ValueError("input-stream SHA256 does not match manifest")
    if manifest["final_generation"] != final_generation:
        raise ValueError("manifest final generation does not match trace")
    expected_final = tuple(
        manifest["final_cumulative_counters"][field] for field in COUNTER_FIELDS
    )
    if expected_final != final_counters:
        raise ValueError("manifest final counters do not match trace")
    for relative_path, expected_hash in manifest["source_sha256"].items():
        if _sha256(ROOT / relative_path) != expected_hash:
            raise ValueError(f"source hash mismatch: {relative_path}")

    return {
        "status": "PASS",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "trace_sha256": trace_hash,
        "summary_sha256": summary_hash,
        "manifest_sha256": _sha256(manifest_path),
        "input_stream_sha256": input_digest.hexdigest().upper(),
        "bytes": len(payload),
        "tokens": tokens,
        "final_generation": final_generation,
        "final_cumulative_counters": {
            field: final_counters[index]
            for index, field in enumerate(COUNTER_FIELDS)
        },
        "source_hashes_verified": len(manifest["source_sha256"]),
    }


def main() -> int:
    result = verify_trace()
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

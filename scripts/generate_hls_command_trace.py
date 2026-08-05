from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import normalize_qk
from golden.gdn_mxfp4_encoded import EncodedToken, encode_token
from golden.gdn_resident_state import ResidentStateOracle, ResidentStatus


ROOT = Path(__file__).resolve().parents[1]
MAGIC = b"GDNTRC01"
VERSION = 1
ENDIAN_MARKER = 0x01020304
DEFAULT_SEED = 0xFB72
COUNTER_FIELDS = (
    "element_saturations",
    "accumulator_saturations",
    "scale_clamps",
    "alignment_underflows",
    "state_scale_changes",
    "invalid_encodings",
    "rejected_commands",
    "committed_state_generations",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _source_sha256(relative_path: str) -> str:
    return _sha256(ROOT / relative_path)


def _git_revision() -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "rev-parse",
            "HEAD",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _token_rng(seed: int, token_index: int) -> np.random.Generator:
    family_offset = sum(
        (index + 1) * ord(char) for index, char in enumerate("nominal")
    )
    return np.random.default_rng(
        seed + 0x9E3779B97F4A7C15 * (token_index + 2) + family_offset
    )


def _encoded_token(seed: int, token_index: int) -> EncodedToken:
    generator = _token_rng(seed, token_index)
    q = generator.normal(0.0, 1.0, size=(16, 128)).astype(np.float32)
    k = generator.normal(0.0, 1.0, size=(16, 128)).astype(np.float32)
    v = generator.normal(0.0, 0.25, size=(32, 128)).astype(np.float32)
    alpha = generator.uniform(0.95, 1.0, size=32).astype(np.float32)
    beta = generator.uniform(0.0, 1.0, size=32).astype(np.float32)
    q_scaled, k_normalized = normalize_qk(q, k)
    return encode_token(
        q_scaled,
        k_normalized,
        v,
        alpha,
        beta,
        block_size=32,
    )


def _write_array(handle: object, array: object, dtype: str) -> bytes:
    payload = np.asarray(array, dtype=np.dtype(dtype).newbyteorder("<")).tobytes(
        order="C"
    )
    handle.write(payload)
    return payload


def _counter_values(counters: object) -> np.ndarray:
    values = counters.as_dict()
    return np.asarray([values[field] for field in COUNTER_FIELDS], dtype="<u8")


def generate_trace(
    *,
    output: Path,
    summary_csv: Path,
    manifest_path: Path,
    tokens: int,
    seed: int,
) -> dict[str, object]:
    if tokens <= 0:
        raise ValueError("tokens must be positive")
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc)
    started_perf = time.perf_counter()
    oracle = ResidentStateOracle()
    reset = oracle.reset(0, 0)
    if reset.status is not ResidentStatus.OK:
        raise RuntimeError("resident-state reset failed")

    input_digest = hashlib.sha256()
    rows: list[dict[str, int]] = []
    header = struct.pack(
        "<8s8I",
        MAGIC,
        VERSION,
        ENDIAN_MARKER,
        tokens,
        16,
        32,
        128,
        128,
        32,
    )
    with output.open("wb") as handle:
        handle.write(header)
        for token_index in range(tokens):
            token = _encoded_token(seed, token_index)
            inputs = (
                (token.q_elements, "u1"),
                (token.q_scales, "u1"),
                (token.k_elements, "u1"),
                (token.k_scales, "u1"),
                (token.v_elements, "u1"),
                (token.v_scales, "u1"),
                (token.alpha_codes, "u2"),
                (token.beta_codes, "u2"),
            )
            for array, dtype in inputs:
                input_digest.update(_write_array(handle, array, dtype))

            result = oracle.step(0, 0, token)
            if result.status is not ResidentStatus.OK:
                raise RuntimeError(
                    f"encoded oracle failed at token {token_index + 1}: "
                    f"{result.status.name}"
                )
            _write_array(handle, [int(result.status)], "u1")
            _write_array(handle, [result.generation], "u8")
            _write_array(handle, _counter_values(result.command_counters), "u8")
            _write_array(handle, _counter_values(result.cumulative_counters), "u8")
            _write_array(handle, result.output_mantissas, "i4")
            _write_array(handle, result.output_exponents, "i2")

            command_values = result.command_counters.as_dict()
            cumulative_values = result.cumulative_counters.as_dict()
            row = {
                "token_index": token_index + 1,
                "status": int(result.status),
                "generation": result.generation,
            }
            row.update(
                {
                    f"command_{field}": command_values[field]
                    for field in COUNTER_FIELDS
                }
            )
            row.update(
                {
                    f"cumulative_{field}": cumulative_values[field]
                    for field in COUNTER_FIELDS
                }
            )
            rows.append(row)

        readback = oracle.readback(0, 0)
        if readback.status is not ResidentStatus.OK or readback.state is None:
            raise RuntimeError("final resident-state readback failed")
        _write_array(handle, readback.state.elements, "u1")
        _write_array(handle, readback.state.scales, "u1")
        _write_array(handle, [int(readback.status)], "u1")
        _write_array(handle, [readback.generation], "u8")
        _write_array(handle, _counter_values(readback.cumulative_counters), "u8")

    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    finished = datetime.now(timezone.utc)
    source_paths = (
        "scripts/generate_hls_command_trace.py",
        "golden/gdn_mxfp4_encoded.py",
        "golden/gdn_resident_state.py",
        "golden/mx_format.py",
        "golden/gdn_fp32.py",
    )
    manifest: dict[str, object] = {
        "status": "PASS",
        "format": "GDNTRC01",
        "format_version": VERSION,
        "git_revision": _git_revision(),
        "seed": seed,
        "tokens": tokens,
        "split": "development",
        "trace_family": "nominal",
        "configuration": {
            "num_sequences": 1,
            "num_layers": 36,
            "num_qk_heads": 16,
            "num_value_heads": 32,
            "key_dim": 128,
            "value_dim": 128,
            "block_size": 32,
            "sequence_id": 0,
            "layer_id": 0,
        },
        "counter_order": list(COUNTER_FIELDS),
        "input_stream_sha256": input_digest.hexdigest().upper(),
        "binary": {
            "path": output.relative_to(ROOT).as_posix(),
            "sha256": _sha256(output),
            "bytes": output.stat().st_size,
        },
        "summary_csv": {
            "path": summary_csv.relative_to(ROOT).as_posix(),
            "sha256": _sha256(summary_csv),
            "rows": len(rows),
        },
        "final_generation": readback.generation,
        "final_cumulative_counters": readback.cumulative_counters.as_dict(),
        "source_sha256": {
            path: _source_sha256(path) for path in source_paths
        },
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "elapsed_seconds": time.perf_counter() - started_perf,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a bit-exact encoded command trace for HLS parity."
    )
    parser.add_argument(
        "--output",
        default="data/vectors/corrected_gdn_command_trace.bin",
    )
    parser.add_argument(
        "--summary-csv",
        default="reports/golden/corrected_hls_command_trace.csv",
    )
    parser.add_argument(
        "--manifest",
        default="reports/golden/corrected_hls_command_trace_manifest.json",
    )
    parser.add_argument("--tokens", type=int, default=64)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    manifest = generate_trace(
        output=_resolve(args.output),
        summary_csv=_resolve(args.summary_csv),
        manifest_path=_resolve(args.manifest),
        tokens=args.tokens,
        seed=args.seed,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

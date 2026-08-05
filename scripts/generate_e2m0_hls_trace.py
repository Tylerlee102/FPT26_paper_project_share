from __future__ import annotations

import argparse
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_e2m0_encoded import (
    E2M0ArithmeticCounters,
    encode_e2m0_state,
    encode_e2m0_token,
)
from golden.gdn_e2m0_encoded_vectorized import EncodedE2M0WriteLogGDNVectorized
from golden.gdn_fp32 import normalize_qk
from scripts.evidence_source_snapshot import describe_source_files
from scripts.long_sequence_stability import TraceConfiguration
from scripts.write_log_stability import _trace_initial_state, _trace_inputs


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "vectors" / "e2m0_resident_trace8.bin"
DEFAULT_MANIFEST = ROOT / "data" / "vectors" / "e2m0_resident_trace8_manifest.json"
MAGIC = b"E2M0T01\0"
VERSION = 1
ENDIAN_MARKER = 0x01020304
CAPACITY = 7
STACK_DEPTH = 2
SEED = 0xFB72


def _write_array(handle, values: object, dtype: str) -> None:
    array = np.ascontiguousarray(np.asarray(values, dtype=np.dtype(dtype)))
    handle.write(array.tobytes(order="C"))


def _write_snapshot(handle, engine: EncodedE2M0WriteLogGDNVectorized) -> None:
    _write_array(handle, engine.base.primary_elements, "u1")
    _write_array(handle, engine.base.primary_scales, "u1")
    _write_array(handle, engine.base.residual_elements, "u1")
    _write_array(handle, engine.base.residual_scales, "u1")
    _write_array(handle, engine.key_elements, "u1")
    _write_array(handle, engine.key_scales, "u1")
    _write_array(handle, engine.update_elements, "u1")
    _write_array(handle, engine.update_scales, "u1")
    _write_array(handle, engine.gamma_codes, "<u2")
    _write_array(handle, engine.lambda_codes, "<u2")
    handle.write(struct.pack("<B", engine.live_entries))


def generate(output: Path, manifest: Path, tokens: int) -> None:
    config = TraceConfiguration(
        tokens=tokens,
        checkpoints=(tokens,),
        seed=SEED,
        split="hls_parity",
        trace_family="high_retention",
        num_value_heads=32,
        num_qk_heads=16,
        key_dim=128,
        value_dim=128,
        activation_block_size=32,
        state_block_size=32,
    )
    initial = _trace_initial_state(config, "random")
    engine = EncodedE2M0WriteLogGDNVectorized(
        encode_e2m0_state(initial, block_size=32),
        num_qk_heads=config.num_qk_heads,
        capacity=CAPACITY,
    )
    cumulative = np.zeros(8, dtype=np.uint64)
    cumulative[7] = 1  # The HLS LOAD command commits generation one.
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(initial).tobytes())

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        handle.write(MAGIC)
        handle.write(
            struct.pack(
                "<10I",
                VERSION,
                ENDIAN_MARKER,
                tokens,
                config.num_qk_heads,
                config.num_value_heads,
                config.key_dim,
                config.value_dim,
                config.activation_block_size,
                STACK_DEPTH,
                CAPACITY,
            )
        )
        _write_snapshot(handle, engine)

        for token_zero_based in range(tokens):
            q, k, v, alpha, beta = _trace_inputs(config, token_zero_based)
            for values in (q, k, v, alpha, beta):
                digest.update(np.ascontiguousarray(values).tobytes())
            q_scaled, k_normalized = normalize_qk(q, k)
            encoded = encode_e2m0_token(
                q_scaled,
                k_normalized,
                v,
                alpha,
                beta,
                block_size=32,
            )
            _write_array(handle, encoded.q.elements, "u1")
            _write_array(handle, encoded.q.scales, "u1")
            _write_array(handle, encoded.k.elements, "u1")
            _write_array(handle, encoded.k.scales, "u1")
            _write_array(handle, encoded.v.elements, "u1")
            _write_array(handle, encoded.v.scales, "u1")
            _write_array(handle, encoded.alpha_codes, "<u2")
            _write_array(handle, encoded.beta_codes, "<u2")

            result = engine.step(encoded)
            counters = result.counters.as_dict()
            command = np.asarray(
                [
                    counters["element_saturations"],
                    counters["accumulator_saturations"],
                    counters["scale_clamps"],
                    counters["alignment_underflows"],
                    counters["state_scale_changes"],
                    counters["e2m0_residual_clips"],
                    int(result.folded),
                    1,
                ],
                dtype=np.uint64,
            )
            cumulative += command
            handle.write(
                struct.pack(
                    "<BQB",
                    0,
                    token_zero_based + 2,
                    result.live_entries,
                )
            )
            _write_array(handle, command, "<u8")
            _write_array(handle, cumulative, "<u8")
            _write_array(handle, result.output_mantissas, "<i4")
            _write_array(handle, result.output_exponents, "<i2")

        _write_snapshot(handle, engine)
        handle.write(struct.pack("<BQ", 0, tokens + 1))
        _write_array(handle, cumulative, "<u8")

    sources = [
        ROOT / "golden" / "gdn_e2m0_encoded.py",
        ROOT / "golden" / "gdn_e2m0_encoded_vectorized.py",
        ROOT / "golden" / "gdn_mxfp4_encoded.py",
        ROOT / "golden" / "gdn_mxfp4_encoded_vectorized.py",
        Path(__file__).resolve(),
    ]
    identity = describe_source_files(sources)
    payload = {
        "schema": 1,
        "status": "PASS",
        "scope": "encoded_e2m0_hls_csim_trace",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": config.__dict__,
        "capacity": CAPACITY,
        "stack_depth": STACK_DEPTH,
        "input_stream_sha256": digest.hexdigest().upper(),
        "trace": output.relative_to(ROOT).as_posix(),
        "trace_sha256": hashlib.sha256(output.read_bytes()).hexdigest().upper(),
        "source_identity": identity,
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest().upper()
            for path in sources
        },
        "independent_reference": "frozen scalar oracle, via its exhaustively cross-checked vectorized executor",
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {tokens} encoded HLS trace tokens to {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an encoded E2M0 HLS parity trace.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--tokens", type=int, default=8)
    args = parser.parse_args()
    if args.tokens < CAPACITY:
        parser.error(f"--tokens must be at least {CAPACITY} to exercise a fold")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    generate(output, manifest, args.tokens)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

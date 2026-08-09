"""Generate bit-exact encoded RS2/R3 traces for HLS C/RTL parity."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import normalize_qk
from golden.gdn_rs2_encoded import encode_rs2_state, encode_rs2_token
from golden.gdn_rs2_encoded_vectorized import EncodedRS2WriteLogGDNVectorized
from scripts.evidence_source_snapshot import describe_source_files
from scripts.long_sequence_stability import TraceConfiguration
from scripts.write_log_stability import _trace_initial_state, _trace_inputs


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "vectors" / "rs2_resident_trace8.bin"
DEFAULT_MANIFEST = ROOT / "data" / "vectors" / "rs2_resident_trace8_manifest.json"
MAGIC = b"RS2T001\0"
VERSION = 1
ENDIAN_MARKER = 0x01020304
CAPACITY = 3
STACK_DEPTH = 2
COUNTER_COUNT = 7
SEED = 0xFB72


def _write_array(handle, values: object, dtype: str) -> None:
    array = np.ascontiguousarray(np.asarray(values, dtype=np.dtype(dtype)))
    handle.write(array.tobytes(order="C"))


def _write_snapshot(handle, engine: EncodedRS2WriteLogGDNVectorized) -> None:
    _write_array(handle, engine.base.elements[0], "u1")
    _write_array(handle, engine.base.scales[0], "u1")
    _write_array(handle, engine.base.elements[1], "u1")
    _write_array(handle, engine.base.scales[1], "u1")
    _write_array(handle, engine.key_elements, "u1")
    _write_array(handle, engine.key_scales, "u1")
    _write_array(handle, engine.update_elements, "u1")
    _write_array(handle, engine.update_scales, "u1")
    _write_array(handle, engine.gamma_codes, "<u2")
    _write_array(handle, engine.lambda_codes, "<u2")
    handle.write(struct.pack("<B", engine.live_entries))


def generate(
    output: Path,
    manifest: Path,
    tokens: int,
    *,
    initial_state_mode: str = "random",
    initial_command: str = "load",
) -> None:
    if initial_state_mode not in {"random", "zero"}:
        raise ValueError(f"unsupported initial state mode: {initial_state_mode}")
    if initial_command not in {"load", "reset"}:
        raise ValueError(f"unsupported initial command: {initial_command}")
    if initial_command == "reset" and initial_state_mode != "zero":
        raise ValueError("RESET traces require a zero initial state")
    trace_version = 2 if initial_command == "reset" else VERSION
    config = TraceConfiguration(
        tokens=tokens,
        checkpoints=(tokens,),
        seed=SEED,
        split="hls_parity_reset" if initial_command == "reset" else "hls_parity",
        trace_family="high_retention",
        num_value_heads=32,
        num_qk_heads=16,
        key_dim=128,
        value_dim=128,
        activation_block_size=32,
        state_block_size=32,
    )
    initial = _trace_initial_state(config, initial_state_mode)
    engine = EncodedRS2WriteLogGDNVectorized(
        encode_rs2_state(initial, block_size=32),
        num_qk_heads=config.num_qk_heads,
        capacity=CAPACITY,
    )
    cumulative = np.zeros(COUNTER_COUNT, dtype=np.uint64)
    if initial_command == "load":
        cumulative[6] = 1  # The HLS LOAD command commits generation one.
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(initial).tobytes())

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        handle.write(MAGIC)
        handle.write(
            struct.pack(
                "<10I",
                trace_version,
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
            encoded = encode_rs2_token(
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
                    int(result.folded),
                    1,
                ],
                dtype=np.uint64,
            )
            cumulative += command
            initial_generation = 1 if initial_command == "load" else 0
            handle.write(
                struct.pack(
                    "<BQB",
                    0,
                    token_zero_based + initial_generation + 1,
                    result.live_entries,
                )
            )
            _write_array(handle, command, "<u8")
            _write_array(handle, cumulative, "<u8")
            _write_array(handle, result.output_mantissas, "<i4")
            _write_array(handle, result.output_exponents, "<i2")

        _write_snapshot(handle, engine)
        final_generation = tokens + (1 if initial_command == "load" else 0)
        handle.write(struct.pack("<BQ", 0, final_generation))
        _write_array(handle, cumulative, "<u8")

    sources = [
        ROOT / "golden" / "gdn_rs2_encoded.py",
        ROOT / "golden" / "gdn_rs2_encoded_vectorized.py",
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
        "scope": "encoded_rs2_hls_csim_trace",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": config.__dict__,
        "capacity": CAPACITY,
        "stack_depth": STACK_DEPTH,
        "counter_count": COUNTER_COUNT,
        "trace_version": trace_version,
        "initial_state_mode": initial_state_mode,
        "initial_command": initial_command,
        "input_stream_sha256": digest.hexdigest().upper(),
        "trace": output.relative_to(ROOT).as_posix(),
        "trace_sha256": hashlib.sha256(output.read_bytes()).hexdigest().upper(),
        "source_identity": identity,
        "source_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest().upper()
            for path in sources
        },
        "independent_reference": (
            "frozen scalar RS2 oracle, via its bit-exact cross-checked vectorized executor"
        ),
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {tokens} encoded RS2 HLS trace tokens to {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--tokens", type=int, default=8)
    parser.add_argument(
        "--initial-state", choices=("random", "zero"), default="random"
    )
    parser.add_argument(
        "--initial-command", choices=("load", "reset"), default="load"
    )
    args = parser.parse_args()
    if args.tokens < CAPACITY:
        parser.error(f"--tokens must be at least {CAPACITY} to exercise a fold")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    generate(
        output,
        manifest,
        args.tokens,
        initial_state_mode=args.initial_state,
        initial_command=args.initial_command,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

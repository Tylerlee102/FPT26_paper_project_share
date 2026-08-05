"""Cross-check the vectorized encoded oracle against the frozen 64-token trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import struct
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_mxfp4_encoded import E8M0_BIAS, EncodedState, EncodedToken
from golden.gdn_mxfp4_encoded_vectorized import (
    recurrence_core_step_encoded_vectorized,
)
from scripts.evidence_source_snapshot import describe_source_files
from scripts.generate_hls_command_trace import (
    COUNTER_FIELDS,
    ENDIAN_MARKER,
    MAGIC,
    VERSION,
)
from scripts.verify_hls_command_trace import TRACE, verify_trace


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "reports" / "golden" / "vectorized_encoded_oracle_verification.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _take_array(
    payload: memoryview,
    offset: int,
    dtype: str,
    shape: tuple[int, ...],
) -> tuple[np.ndarray, int]:
    item_dtype = np.dtype(dtype)
    count = int(np.prod(shape, dtype=np.int64))
    size = count * item_dtype.itemsize
    stop = offset + size
    if stop > len(payload):
        raise ValueError(f"short trace at byte {offset}; need {size} bytes")
    array = np.frombuffer(payload[offset:stop], dtype=item_dtype, count=count)
    return array.copy().reshape(shape), stop


def _require_equal(name: str, actual: np.ndarray, expected: np.ndarray) -> None:
    if actual.shape != expected.shape or not np.array_equal(actual, expected):
        mismatch = np.argwhere(actual != expected)
        location = tuple(int(value) for value in mismatch[0]) if mismatch.size else ()
        raise ValueError(f"{name} mismatch at {location}")


def verify_vectorized_trace(trace_path: Path = TRACE) -> dict[str, object]:
    frozen_verification = verify_trace(trace_path=trace_path)
    payload = memoryview(trace_path.read_bytes())
    header_size = struct.calcsize("<8s8I")
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
    ) = struct.unpack_from("<8s8I", payload, 0)
    if (magic, version, endian_marker) != (MAGIC, VERSION, ENDIAN_MARKER):
        raise ValueError("frozen trace header identity mismatch")
    if (tokens, num_qk_heads, num_value_heads, key_dim, value_dim, block_size) != (
        64,
        16,
        32,
        128,
        128,
        32,
    ):
        raise ValueError("frozen trace dimensions mismatch")

    blocks = value_dim // block_size
    state = EncodedState(
        elements=np.zeros(
            (num_value_heads, key_dim, value_dim), dtype=np.uint8
        ),
        scales=np.full(
            (num_value_heads, key_dim, blocks), E8M0_BIAS, dtype=np.uint8
        ),
        block_size=block_size,
    )
    cumulative = np.zeros(len(COUNTER_FIELDS), dtype=np.uint64)
    offset = header_size
    started = time.perf_counter()

    for token_zero_based in range(tokens):
        q_elements, offset = _take_array(
            payload, offset, "<u1", (num_qk_heads, key_dim)
        )
        q_scales, offset = _take_array(
            payload, offset, "<u1", (num_qk_heads, key_dim // block_size)
        )
        k_elements, offset = _take_array(
            payload, offset, "<u1", (num_qk_heads, key_dim)
        )
        k_scales, offset = _take_array(
            payload, offset, "<u1", (num_qk_heads, key_dim // block_size)
        )
        v_elements, offset = _take_array(
            payload, offset, "<u1", (num_value_heads, value_dim)
        )
        v_scales, offset = _take_array(
            payload, offset, "<u1", (num_value_heads, value_dim // block_size)
        )
        alpha_codes, offset = _take_array(
            payload, offset, "<u2", (num_value_heads,)
        )
        beta_codes, offset = _take_array(
            payload, offset, "<u2", (num_value_heads,)
        )
        expected_status, offset = _take_array(payload, offset, "<u1", (1,))
        expected_generation, offset = _take_array(payload, offset, "<u8", (1,))
        expected_command, offset = _take_array(
            payload, offset, "<u8", (len(COUNTER_FIELDS),)
        )
        expected_cumulative, offset = _take_array(
            payload, offset, "<u8", (len(COUNTER_FIELDS),)
        )
        expected_output_mantissas, offset = _take_array(
            payload, offset, "<i4", (num_value_heads, value_dim)
        )
        expected_output_exponents, offset = _take_array(
            payload, offset, "<i2", (num_value_heads, value_dim)
        )

        token = EncodedToken(
            q_elements=q_elements,
            q_scales=q_scales,
            k_elements=k_elements,
            k_scales=k_scales,
            v_elements=v_elements,
            v_scales=v_scales,
            alpha_codes=alpha_codes,
            beta_codes=beta_codes,
            block_size=block_size,
        )
        result = recurrence_core_step_encoded_vectorized(token, state)
        if int(expected_status[0]) != 0:
            raise ValueError(f"nonzero frozen status at token {token_zero_based + 1}")
        if int(expected_generation[0]) != token_zero_based + 1:
            raise ValueError(
                f"frozen generation mismatch at token {token_zero_based + 1}"
            )
        command = np.asarray(
            [
                result.counters.element_saturations,
                result.counters.accumulator_saturations,
                result.counters.scale_clamps,
                result.counters.alignment_underflows,
                result.counters.state_scale_changes,
                0,
                0,
                1,
            ],
            dtype=np.uint64,
        )
        cumulative += command
        _require_equal(
            f"command counters token {token_zero_based + 1}",
            command,
            expected_command,
        )
        _require_equal(
            f"cumulative counters token {token_zero_based + 1}",
            cumulative,
            expected_cumulative,
        )
        _require_equal(
            f"output mantissas token {token_zero_based + 1}",
            result.output_mantissas.astype(np.int32),
            expected_output_mantissas,
        )
        _require_equal(
            f"output exponents token {token_zero_based + 1}",
            result.output_exponents.astype(np.int16),
            expected_output_exponents,
        )
        state = result.state

    expected_state, offset = _take_array(
        payload, offset, "<u1", (num_value_heads, key_dim, value_dim)
    )
    expected_scales, offset = _take_array(
        payload, offset, "<u1", (num_value_heads, key_dim, blocks)
    )
    expected_status, offset = _take_array(payload, offset, "<u1", (1,))
    expected_generation, offset = _take_array(payload, offset, "<u8", (1,))
    expected_cumulative, offset = _take_array(
        payload, offset, "<u8", (len(COUNTER_FIELDS),)
    )
    if offset != len(payload):
        raise ValueError(f"trace has {len(payload) - offset} trailing bytes")
    if int(expected_status[0]) != 0 or int(expected_generation[0]) != tokens:
        raise ValueError("frozen final readback metadata mismatch")
    _require_equal("final cumulative counters", cumulative, expected_cumulative)
    _require_equal("final state elements", state.elements, expected_state)
    _require_equal("final state scales", state.scales, expected_scales)
    elapsed = time.perf_counter() - started

    source_paths = [
        ROOT / "golden" / "gdn_mxfp4_encoded.py",
        ROOT / "golden" / "gdn_mxfp4_encoded_vectorized.py",
        ROOT / "scripts" / "verify_vectorized_encoded_oracle.py",
    ]
    return {
        "schema": 1,
        "status": "PASS",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Exact 64-token full-dimension cross-check of the vectorized encoded "
            "oracle against the frozen scalar-oracle HLS trace."
        ),
        "configuration": {
            "tokens": tokens,
            "num_qk_heads": num_qk_heads,
            "num_value_heads": num_value_heads,
            "key_dim": key_dim,
            "value_dim": value_dim,
            "block_size": block_size,
            "orientation": "KxV",
        },
        "comparisons": {
            "output_mantissas": tokens * num_value_heads * value_dim,
            "output_exponents": tokens * num_value_heads * value_dim,
            "command_counters": tokens * len(COUNTER_FIELDS),
            "cumulative_counters": tokens * len(COUNTER_FIELDS),
            "final_state_elements": num_value_heads * key_dim * value_dim,
            "final_state_scales": num_value_heads * key_dim * blocks,
        },
        "final_cumulative_counters": {
            field: int(cumulative[index])
            for index, field in enumerate(COUNTER_FIELDS)
        },
        "elapsed_seconds": elapsed,
        "frozen_trace": {
            "path": trace_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(trace_path),
            "verification": frozen_verification,
        },
        "source_identity": describe_source_files(source_paths),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "command": "python -m scripts.verify_vectorized_encoded_oracle",
        "exit_code": 0,
        "independent_verification": (
            "The vectorized implementation is structurally separate from the "
            "scalar oracle and is compared against every frozen per-token output "
            "and counter plus the complete final encoded state."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=TRACE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    trace_path = args.trace if args.trace.is_absolute() else ROOT / args.trace
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    result = verify_vectorized_trace(trace_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "tokens": result["configuration"]["tokens"],
                "elapsed_seconds": result["elapsed_seconds"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

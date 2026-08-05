from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from golden.gdn_e2m0_encoded import (
    E2M0ArithmeticCounters,
    _aligned_sum_guarded,
    _e2m0_sse,
    _exceeds_e2m0_max,
    _quantize_exact_e2m0,
    _select_e2m0_scale_power,
)
from golden.gdn_mxfp4_encoded import _quantize_exact_e2m1, _select_scale_power


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "vectors" / "e2m0_arithmetic_v1.txt"
BLOCK_SIZE = 32
SEED = 0xFB72


def _fixed_cases() -> list[tuple[np.ndarray, np.ndarray]]:
    cases: list[tuple[np.ndarray, np.ndarray]] = []
    cases.append((np.zeros(BLOCK_SIZE, dtype=np.int64), np.zeros(BLOCK_SIZE, dtype=np.int64)))

    for mantissa, exponent in (
        (1, 0),
        (-1, 0),
        (3, -7),
        (-12, 19),
        ((1 << 30) - 1, -80),
        (-(1 << 30), 80),
        (1, 126),
        (-1, -128),
    ):
        mantissas = np.zeros(BLOCK_SIZE, dtype=np.int64)
        exponents = np.zeros(BLOCK_SIZE, dtype=np.int64)
        mantissas[0] = mantissa
        exponents[0] = exponent
        cases.append((mantissas, exponents))

    tie_magnitudes = np.asarray(
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, -1, -3, -5, -7],
        dtype=np.int64,
    )
    mantissas = np.resize(tie_magnitudes, BLOCK_SIZE)
    exponents = np.full(BLOCK_SIZE, -5, dtype=np.int64)
    cases.append((mantissas, exponents))

    mantissas = np.asarray(
        [1, 1, -1, -1, 3, -3, 7, -7] * 4, dtype=np.int64
    )
    exponents = np.asarray(
        [40, 34, 28, 22, 16, 10, 4, -2] * 4, dtype=np.int64
    )
    cases.append((mantissas, exponents))
    return cases


def _random_cases(count: int) -> list[tuple[np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(SEED)
    cases: list[tuple[np.ndarray, np.ndarray]] = []
    for index in range(count):
        mantissas = rng.integers(-(1 << 30), 1 << 30, size=BLOCK_SIZE, dtype=np.int64)
        zero_mask = rng.random(BLOCK_SIZE) < 0.12
        mantissas[zero_mask] = 0
        bit_lengths = np.asarray(
            [max(1, abs(int(value)).bit_length()) for value in mantissas],
            dtype=np.int64,
        )
        physical_top = int(rng.integers(-118, 119))
        jitter = rng.integers(-18, 4, size=BLOCK_SIZE, dtype=np.int64)
        exponents = physical_top - bit_lengths + 1 + jitter
        exponents = np.clip(exponents, -250, 250).astype(np.int64)
        if index % 17 == 0:
            lane = int(rng.integers(0, BLOCK_SIZE))
            mantissas[lane] = int(rng.choice(np.asarray((-1, 1), dtype=np.int64)))
            exponents[lane] = int(rng.integers(-220, 221))
        cases.append((mantissas, exponents))
    return cases


def _evaluate(mantissas: np.ndarray, exponents: np.ndarray) -> dict[str, object]:
    counters = E2M0ArithmeticCounters()
    aligned_m, aligned_e = _aligned_sum_guarded(mantissas, exponents, counters)

    e2m1_power = _select_scale_power(mantissas, exponents, counters)
    e2m1_codes = [
        _quantize_exact_e2m1(int(m), int(e), e2m1_power, counters)
        for m, e in zip(mantissas, exponents)
    ]

    upper = _select_e2m0_scale_power(mantissas, exponents, counters)
    lower = max(-127, upper - 1)
    upper_codes = np.asarray(
        [_quantize_exact_e2m0(int(m), int(e), upper) for m, e in zip(mantissas, exponents)],
        dtype=np.uint8,
    )
    lower_codes = np.asarray(
        [_quantize_exact_e2m0(int(m), int(e), lower) for m, e in zip(mantissas, exponents)],
        dtype=np.uint8,
    )
    choose_lower = _e2m0_sse(mantissas, exponents, lower, lower_codes) < _e2m0_sse(
        mantissas, exponents, upper, upper_codes
    )
    selected_power = lower if choose_lower else upper
    selected_codes = lower_codes if choose_lower else upper_codes
    counters.e2m0_residual_clips += sum(
        _exceeds_e2m0_max(int(m), int(e), selected_power)
        for m, e in zip(mantissas, exponents)
    )
    if not np.any(selected_codes):
        selected_power = 0

    return {
        "aligned_m": aligned_m,
        "aligned_e": aligned_e,
        "e2m1_power": e2m1_power,
        "e2m1_codes": e2m1_codes,
        "upper": upper,
        "selected_power": selected_power,
        "choose_lower": int(choose_lower),
        "e2m0_codes": selected_codes.astype(int).tolist(),
        "counters": [
            counters.element_saturations,
            counters.accumulator_saturations,
            counters.scale_clamps,
            counters.alignment_underflows,
            counters.state_scale_changes,
            counters.e2m0_residual_clips,
            0,
            0,
        ],
    }


def generate(output: Path, random_cases: int) -> None:
    cases = [*_fixed_cases(), *_random_cases(random_cases)]
    lines = [f"E2M0_ARITHMETIC_V1 {len(cases)}"]
    for case_id, (mantissas, exponents) in enumerate(cases):
        expected = _evaluate(mantissas, exponents)
        lines.append(f"CASE {case_id}")
        lines.extend(f"{int(m)} {int(e)}" for m, e in zip(mantissas, exponents))
        lines.append(f"ALIGNED {expected['aligned_m']} {expected['aligned_e']}")
        lines.append(
            "E2M1 "
            + str(expected["e2m1_power"])
            + " "
            + " ".join(str(value) for value in expected["e2m1_codes"])
        )
        lines.append(
            f"E2M0 {expected['upper']} {expected['selected_power']} "
            f"{expected['choose_lower']} "
            + " ".join(str(value) for value in expected["e2m0_codes"])
        )
        lines.append("COUNTERS " + " ".join(str(value) for value in expected["counters"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"wrote {len(cases)} oracle cases to {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate frozen-oracle E2M0 HLS arithmetic vectors.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--random-cases", type=int, default=256)
    args = parser.parse_args()
    if args.random_cases < 0:
        parser.error("--random-cases must be nonnegative")
    generate(args.output, args.random_cases)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

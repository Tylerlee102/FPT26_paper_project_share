from __future__ import annotations

import csv
from collections import defaultdict

from scripts.long_sequence_stability import DEFAULT_TOKEN_CSV
from scripts.verify_synthetic_stability import threshold_decision


def _rows(cosines: list[float], final_state: float) -> list[dict[str, str]]:
    rows = []
    for index, token in enumerate((64, 256, 1024, 4096, 8192)):
        rows.append(
            {
                "token_index": str(token),
                "output_cosine_fp32": str(cosines[index]),
                "state_rel_l2": str(final_state if token == 8192 else 0.01),
            }
        )
    return rows


def test_threshold_pass_requires_both_metrics() -> None:
    result = threshold_decision(_rows([0.995] * 5, 0.08))
    assert result["status"] == "PASS"


def test_threshold_fails_cosine_or_state() -> None:
    assert threshold_decision(_rows([0.995, 0.98, 0.995, 0.995, 0.995], 0.08))[
        "status"
    ] == "FAIL"
    assert threshold_decision(_rows([0.995] * 5, 0.11))["status"] == "FAIL"


def test_canonical_floating_trace_diagnostic_crossings() -> None:
    with DEFAULT_TOKEN_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    variants: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        variants[row["variant"]].append(row)
    for variant_rows in variants.values():
        variant_rows.sort(key=lambda row: int(row["token_index"]))

    def first_crossing(variant: str, metric: str, threshold: float) -> int | None:
        for row in variants[variant]:
            value = float(row[metric])
            crossed = (
                value < threshold
                if metric == "output_cosine_fp32"
                else value > threshold
            )
            if crossed:
                return int(row["token_index"])
        return None

    assert first_crossing(
        "bf16_qdq_fp32_accum_state_bf16", "output_cosine_fp32", 0.99
    ) is None
    assert first_crossing(
        "bf16_qdq_fp32_accum_state_bf16", "state_rel_l2", 0.10
    ) is None
    assert first_crossing(
        "mxfp4_qdq_act_b32_state_b32", "output_cosine_fp32", 0.99
    ) == 1
    assert first_crossing(
        "mxfp4_qdq_act_b32_state_b32", "state_rel_l2", 0.10
    ) == 1
    assert first_crossing(
        "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32",
        "output_cosine_fp32",
        0.99,
    ) == 4
    assert first_crossing(
        "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32", "state_rel_l2", 0.10
    ) == 5

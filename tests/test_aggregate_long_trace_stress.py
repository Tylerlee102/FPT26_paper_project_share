import csv
import json
from pathlib import Path

import pytest

from scripts.aggregate_long_trace_stress import DEFAULT_INPUTS, VARIANTS, aggregate


ROOT = Path(__file__).resolve().parents[1]


def _run(tmp_path: Path) -> tuple[list[dict[str, str]], dict[str, object]]:
    csv_path = tmp_path / "summary.csv"
    report_path = tmp_path / "summary.md"
    manifest_path = tmp_path / "manifest.json"
    aggregate(
        inputs=DEFAULT_INPUTS,
        csv_path=csv_path,
        report_path=report_path,
        manifest_path=manifest_path,
        execution_command="pytest aggregate_long_trace_stress",
    )
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return rows, manifest


def test_full_shape_stress_artifacts_validate_and_preserve_method_ranking(tmp_path: Path) -> None:
    rows, manifest = _run(tmp_path)
    assert manifest["status"] == "PASS"
    assert manifest["evidence_scope"] == "supplemental_synthetic_floating_qdq_stress"
    assert manifest["row_count"] == 2 * len(VARIANTS)
    assert len(rows) == 2 * len(VARIANTS)

    indexed = {(row["trace_family"], row["variant"]): row for row in rows}
    for family in ("dynamic_range", "cancellation"):
        assert indexed[(family, "fp32")]["full_trace_threshold_status"] == "PASS"
        assert indexed[(family, "bf16_qdq_fp32_accum_state_bf16")][
            "full_trace_threshold_status"
        ] == "PASS"
        mxfp4 = indexed[(family, "mxfp4_qdq_act_b32_state_b32")]
        mxfp8 = indexed[
            (family, "mxfp4_qdq_act_b32_mxfp8_e4m3_state_b32")
        ]
        assert float(mxfp8["final_output_cosine_fp32"]) > float(
            mxfp4["final_output_cosine_fp32"]
        )
        assert float(mxfp8["final_state_rel_l2"]) < float(
            mxfp4["final_state_rel_l2"]
        )
        assert mxfp8["full_trace_threshold_status"] == "FAIL"


def test_stress_aggregate_hashes_every_input_and_output(tmp_path: Path) -> None:
    rows, manifest = _run(tmp_path)
    assert rows
    assert len(manifest["input_sha256"]) == 6
    assert len(manifest["outputs"]) == 2
    assert all(len(value) == 64 for value in manifest["input_sha256"].values())
    assert all(len(value) == 64 for value in manifest["outputs"].values())
    assert "not fitted to model-derived activation distributions" in manifest["limitations"]


def test_stress_aggregate_rejects_wrong_geometry(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_INPUTS["dynamic_range"].read_text(encoding="utf-8"))
    payload["configuration"]["key_dim"] = 64
    tampered = tmp_path / "dynamic_range_manifest.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="configuration key_dim"):
        aggregate(
            inputs={
                "dynamic_range": tampered,
                "cancellation": DEFAULT_INPUTS["cancellation"],
            },
            csv_path=tmp_path / "summary.csv",
            report_path=tmp_path / "summary.md",
            manifest_path=tmp_path / "summary.json",
            execution_command="pytest tampered",
        )

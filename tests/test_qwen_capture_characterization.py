from __future__ import annotations

import json

import numpy as np

from scripts.qwen_capture_characterization import characterize, write_outputs


def test_characterization_reports_range_without_claiming_recurrence(tmp_path) -> None:
    capture = tmp_path / "capture.npz"
    metadata = {
        "source": "huggingface_qwen3_next",
        "model_id": "Qwen/Qwen3-Next-test",
        "layer_index": 12,
        "captured_arrays": ["layer_input", "layer_output"],
    }
    np.savez(
        capture,
        layer_input=np.asarray([[-4.0, 0.0, 1.0, 8.0]], dtype=np.float32),
        layer_output=np.asarray([[0.5, -0.5]], dtype=np.float32),
        metadata_json=np.asarray(json.dumps(metadata)),
    )

    report = characterize(capture)

    assert report["status"] == "PASS"
    assert report["floating_tensors"]["layer_input"]["abs_max"] == 8.0
    coverage = report["recurrence_coverage"]
    assert coverage["complete"] is False
    assert coverage["closed_loop_quality_supported"] is False
    assert coverage["missing_tensors"] == ["alpha", "beta", "k", "q", "v"]

    json_path = tmp_path / "report.json"
    csv_path = tmp_path / "report.csv"
    write_outputs(report, json_path, csv_path)
    assert json.loads(json_path.read_text())["status"] == "PASS"
    assert csv_path.read_text().splitlines()[1].startswith("layer_input,")

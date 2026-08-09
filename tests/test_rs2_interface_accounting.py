from __future__ import annotations

import json
from pathlib import Path

from scripts.rs2_interface_accounting import generate


def test_selected_rs2_interface_accounting(tmp_path: Path) -> None:
    output = tmp_path / "accounting.json"
    report = generate(output)

    assert report["status"] == "PASS"
    assert report["commands"]["LOAD"]["bf16_input_bytes"] == 1048576
    assert report["commands"]["LOAD"]["rs2_input_bytes"] == 576912
    assert report["commands"]["STEP"]["bf16_input_bytes"] == 16512
    assert report["commands"]["STEP"]["rs2_input_bytes"] == 8832
    assert report["commands"]["STEP"]["bf16_output_bytes"] == 8192
    assert report["commands"]["STEP"]["rs2_output_bytes"] == 24576
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "PASS"

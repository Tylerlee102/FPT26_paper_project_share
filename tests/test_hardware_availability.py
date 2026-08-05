from __future__ import annotations

from pathlib import Path

from scripts import hardware_availability as module


def test_collect_distinguishes_tools_from_missing_board(monkeypatch) -> None:
    monkeypatch.setattr(module, "find_vitis_hls", lambda: Path("C:/tools/vitis_hls.exe"))
    monkeypatch.setattr(module, "find_vivado_batch", lambda: Path("C:/tools/vivado.bat"))
    payload = module.collect(
        which=lambda _name: None,
        platform_finder=lambda: [],
        device_probe=lambda: {"returncode": 0, "stdout": "", "stderr": ""},
        gpu_probe=lambda _command: {
            "returncode": 0,
            "stdout": "NVIDIA GeForce RTX 3070, 8192 MiB, 8.6, 610.88",
            "stderr": "",
        },
    )

    assert payload["toolchain"]["status"] == "AVAILABLE"
    assert payload["u55c_board_experiment"]["status"] == (
        "BLOCKED_EXTERNAL_NO_U55C_DEVICE_OR_XRT"
    )
    assert payload["native_fp4_gpu_experiment"]["status"] == (
        "BLOCKED_EXTERNAL_NO_NATIVE_FP4_GPU"
    )


def test_collect_marks_complete_board_stack_available(monkeypatch) -> None:
    monkeypatch.setattr(module, "find_vitis_hls", lambda: Path("vitis_hls.exe"))
    monkeypatch.setattr(module, "find_vivado_batch", lambda: Path("vivado.bat"))
    payload = module.collect(
        which=lambda name: f"C:/XRT/{name}.exe",
        platform_finder=lambda: ["C:/platforms/u55c/base.xpfm"],
        device_probe=lambda: {
            "returncode": 0,
            "stdout": '{"FriendlyName":"Alveo U55C"}',
            "stderr": "",
        },
        gpu_probe=lambda _command: {
            "returncode": 0,
            "stdout": "NVIDIA B200, 183359 MiB, 10.0, 610.88",
            "stderr": "",
        },
    )

    assert payload["u55c_board_experiment"]["status"] == "AVAILABLE"
    assert payload["native_fp4_gpu_experiment"]["status"] == "AVAILABLE"


def test_markdown_names_external_measurement_boundary(monkeypatch) -> None:
    monkeypatch.setattr(module, "find_vitis_hls", lambda: Path("vitis_hls.exe"))
    monkeypatch.setattr(module, "find_vivado_batch", lambda: Path("vivado.bat"))
    payload = module.collect(
        which=lambda _name: None,
        platform_finder=lambda: [],
        device_probe=lambda: {"returncode": 0, "stdout": "", "stderr": ""},
        gpu_probe=lambda _command: {"returncode": 1, "stdout": "", "stderr": "missing"},
    )
    markdown = module._markdown(payload)

    assert "U55C board parity and telemetry" in markdown
    assert "Native-FP4 GPU baseline" in markdown
    assert "not represented by estimates" in markdown

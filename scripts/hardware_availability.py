"""Record whether local hardware can support board and native-FP4 experiments."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from scripts.xilinx_tools import find_vitis_hls, find_vivado_batch


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "reports" / "environment" / "hardware_availability.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "environment" / "hardware_availability.md"
XRT_COMMANDS = ("xbutil", "xrt-smi", "xclbinutil")
VITIS_COMMANDS = ("v++", "platforminfo", "xsim")
PLATFORM_ROOTS = (
    Path("C:/AMDDesignTools"),
    Path("C:/Xilinx"),
    Path("C:/Xilinx/platforms"),
    Path("C:/Users/Public/xilinx"),
)


def _which(name: str) -> str | None:
    hit = shutil.which(name) or shutil.which(f"{name}.exe")
    if hit:
        return str(Path(hit).resolve())
    known = {
        "v++": (
            Path("C:/AMDDesignTools/2025.2/Vitis/bin/v++.bat"),
            Path("C:/AMDDesignTools/2025.1/Vitis/bin/v++.bat"),
            Path("C:/AMDDesignTools/2024.2/Vitis/bin/v++.bat"),
        ),
        "platforminfo": (
            Path("C:/AMDDesignTools/2025.2/Vitis/bin/platforminfo.bat"),
            Path("C:/AMDDesignTools/2025.1/Vitis/bin/platforminfo.bat"),
            Path("C:/AMDDesignTools/2024.2/Vitis/bin/platforminfo.bat"),
        ),
        "xsim": (
            Path("C:/AMDDesignTools/2025.2/Vivado/bin/xsim.bat"),
            Path("C:/AMDDesignTools/2025.1/Vivado/bin/xsim.bat"),
            Path("C:/AMDDesignTools/2024.2/Vivado/bin/xsim.bat"),
        ),
        "xclbinutil": (
            Path("C:/AMDDesignTools/2025.2/Vitis/bin/unwrapped/win64.o/xclbinutil.exe"),
            Path("C:/AMDDesignTools/2025.1/Vitis/bin/unwrapped/win64.o/xclbinutil.exe"),
            Path("C:/AMDDesignTools/2024.2/Vitis/bin/unwrapped/win64.o/xclbinutil.exe"),
        ),
        "xbutil": (
            Path("C:/Xilinx/XRT/bin/xbutil.exe"),
            Path("C:/Program Files/Xilinx/XRT/bin/xbutil.exe"),
        ),
        "xrt-smi": (
            Path("C:/Xilinx/XRT/bin/xrt-smi.exe"),
            Path("C:/Program Files/Xilinx/XRT/bin/xrt-smi.exe"),
        ),
    }
    for candidate in known.get(name, ()):
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def _run(command: list[str]) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"returncode": None, "stdout": "", "stderr": str(exc)}
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _find_u55c_platforms(roots: tuple[Path, ...] = PLATFORM_ROOTS) -> list[str]:
    hits: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for candidate in root.rglob("*.xpfm"):
            if "u55c" in candidate.as_posix().lower():
                hits.add(str(candidate.resolve()))
    return sorted(hits)


def _windows_xilinx_devices() -> dict[str, object]:
    if os.name != "nt":
        return {"returncode": None, "stdout": "", "stderr": "not Windows"}
    script = (
        "Get-PnpDevice -PresentOnly | "
        "Where-Object { $_.FriendlyName -match 'Alveo|Xilinx|U55C' "
        "-or $_.InstanceId -match '^PCI\\\\VEN_10EE' } | "
        "Select-Object Status,Class,FriendlyName,InstanceId | ConvertTo-Json -Compress"
    )
    return _run(["powershell", "-NoProfile", "-Command", script])


def _parse_gpu(query: dict[str, object]) -> dict[str, object]:
    if query.get("returncode") != 0 or not str(query.get("stdout", "")).strip():
        return {
            "detected": False,
            "devices": [],
            "native_fp4_baseline_available": False,
            "status": "BLOCKED_EXTERNAL_NO_NATIVE_FP4_GPU",
        }
    devices: list[dict[str, str]] = []
    for line in str(query["stdout"]).splitlines():
        cells = [cell.strip() for cell in line.split(",")]
        if len(cells) >= 4:
            devices.append(
                {
                    "name": cells[0],
                    "memory_total": cells[1],
                    "compute_capability": cells[2],
                    "driver_version": cells[3],
                }
            )
    native = any(
        "B100" in row["name"]
        or "B200" in row["name"]
        or "GB200" in row["name"]
        or "RTX 50" in row["name"]
        for row in devices
    )
    return {
        "detected": bool(devices),
        "devices": devices,
        "native_fp4_baseline_available": native,
        "status": "AVAILABLE" if native else "BLOCKED_EXTERNAL_NO_NATIVE_FP4_GPU",
    }


def collect(
    *,
    which: Callable[[str], str | None] = _which,
    platform_finder: Callable[[], list[str]] = _find_u55c_platforms,
    device_probe: Callable[[], dict[str, object]] = _windows_xilinx_devices,
    gpu_probe: Callable[[list[str]], dict[str, object]] = _run,
) -> dict[str, object]:
    xrt_commands = {name: which(name) for name in XRT_COMMANDS}
    vitis_commands = {name: which(name) for name in VITIS_COMMANDS}
    platforms = platform_finder()
    pcie = device_probe()
    pcie_present = pcie.get("returncode") == 0 and bool(str(pcie.get("stdout", "")).strip())
    board_ready = bool(platforms) and bool(xrt_commands["xbutil"] or xrt_commands["xrt-smi"]) and pcie_present
    gpu_query = gpu_probe(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,compute_cap,driver_version",
            "--format=csv,noheader",
        ]
    )
    return {
        "schema": "hardware-availability-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "toolchain": {
            "vitis_hls": str(find_vitis_hls()) if find_vitis_hls() else None,
            "vivado": str(find_vivado_batch()) if find_vivado_batch() else None,
            "vitis_compiler": vitis_commands["v++"],
            "platforminfo": vitis_commands["platforminfo"],
            "xsim": vitis_commands["xsim"],
            "status": "AVAILABLE"
            if find_vitis_hls() is not None and find_vivado_batch() is not None
            else "INCOMPLETE",
            "acceleration_tools_status": "AVAILABLE"
            if all(vitis_commands.values())
            else "INCOMPLETE",
        },
        "u55c_board_experiment": {
            "xrt_commands": xrt_commands,
            "u55c_platform_files": platforms,
            "pcie_probe": pcie,
            "pcie_device_present": pcie_present,
            "ready": board_ready,
            "status": "AVAILABLE"
            if board_ready
            else "BLOCKED_EXTERNAL_NO_U55C_DEVICE_OR_XRT",
            "required_to_unblock": [
                "an attached Alveo U55C visible as PCI vendor 0x10ee",
                "an installed U55C XRT platform and xbutil or xrt-smi",
                "a generated xclbin and board telemetry access",
            ],
        },
        "native_fp4_gpu_experiment": {
            **_parse_gpu(gpu_query),
            "query": gpu_query,
            "required_to_unblock": [
                "a GPU with native FP4 tensor-core support",
                "a matching software stack and synchronized benchmark harness",
            ],
        },
    }


def _markdown(payload: dict[str, object]) -> str:
    tools = payload["toolchain"]
    board = payload["u55c_board_experiment"]
    gpu = payload["native_fp4_gpu_experiment"]
    devices = gpu["devices"]
    gpu_text = "; ".join(
        f"{row['name']} (CC {row['compute_capability']}, {row['memory_total']})"
        for row in devices
    ) or "none detected"
    xrt = board["xrt_commands"]
    return "\n".join(
        [
            "# Local Hardware Availability",
            "",
            f"Generated: `{payload['generated_at']}` on `{payload['host']}`.",
            "",
            "| Experiment prerequisite | Status | Observation |",
            "|---|---|---|",
            f"| Vitis HLS and Vivado | {tools['status']} | HLS: `{tools['vitis_hls']}`; Vivado: `{tools['vivado']}` |",
            f"| Vitis compiler, platform inventory, and XSim | {tools['acceleration_tools_status']} | v++: `{tools['vitis_compiler']}`; platforminfo: `{tools['platforminfo']}`; XSim: `{tools['xsim']}` |",
            f"| U55C board parity and telemetry | {board['status']} | PCI device: `{board['pcie_device_present']}`; U55C platforms: `{len(board['u55c_platform_files'])}`; xbutil: `{xrt['xbutil']}`; xrt-smi: `{xrt['xrt-smi']}` |",
            f"| Native-FP4 GPU baseline | {gpu['status']} | {gpu_text} |",
            "",
            "The installed synthesis and acceleration tools support HLS, Vivado, v++, "
            "platform inventory, and XSim experiments. They do not substitute for an attached U55C, "
            "a U55C XPFM, XRT management tools, or board telemetry. "
            "Likewise, a detected pre-native-FP4 GPU cannot provide the requested matched "
            "native-FP4 GPU baseline. These two measurements remain externally blocked and "
            "are not represented by estimates.",
            "",
        ]
    )


def write_reports(json_path: Path, markdown_path: Path) -> dict[str, object]:
    payload = collect()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    payload = write_reports(args.json, args.markdown)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

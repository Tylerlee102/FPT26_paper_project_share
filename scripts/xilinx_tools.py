from __future__ import annotations

import os
import shutil
from pathlib import Path


TOOL_VERSIONS = ("2025.2", "2025.1", "2024.2")


def _amd_roots() -> list[Path]:
    roots: list[Path] = []
    for base in (Path("C:/AMDDesignTools"), Path("C:/Xilinx")):
        for version in TOOL_VERSIONS:
            version_root = base / version
            roots.extend([version_root, version_root / "Vitis", version_root / "Vivado"])
    return roots


def _candidate_paths() -> list[Path]:
    roots: list[Path] = []
    for env_name in ("VITIS_HLS", "XILINX_HLS", "XILINX_VITIS", "XILINX_VIVADO"):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value))

    roots.extend(
        [
            Path("C:/Xilinx/Vitis_HLS"),
            Path("C:/Xilinx/Vitis"),
            Path("C:/Xilinx/Vivado"),
        ]
    )
    roots.extend(_amd_roots())

    exe_candidates: list[Path] = []
    script_candidates: list[Path] = []
    for root in roots:
        exe_candidates.extend(
            [
                root / "bin" / "vitis_hls.exe",
                root / "bin" / "unwrapped" / "win64.o" / "vitis_hls.exe",
                root / "2024.2" / "bin" / "vitis_hls.exe",
                root / "2024.2" / "bin" / "unwrapped" / "win64.o" / "vitis_hls.exe",
                root / "2024.2" / "xsct-trim" / "bin" / "unwrapped" / "win64.o" / "vitis_hls.exe",
                root / "2025.2" / "bin" / "vitis_hls.exe",
                root / "2025.2" / "bin" / "unwrapped" / "win64.o" / "vitis_hls.exe",
                root / "2025.2" / "xsct-trim" / "bin" / "unwrapped" / "win64.o" / "vitis_hls.exe",
            ]
        )
        script_candidates.extend(
            [
                root / "bin" / "vitis_hls.bat",
                root / "bin" / "vitis_hls",
                root / "2024.2" / "bin" / "vitis_hls.bat",
                root / "2024.2" / "bin" / "vitis_hls",
                root / "2025.2" / "bin" / "vitis_hls.bat",
                root / "2025.2" / "bin" / "vitis_hls",
            ]
        )
    return exe_candidates + script_candidates


def _roots() -> list[Path]:
    roots: list[Path] = []
    for env_name in ("VITIS_HLS", "XILINX_HLS", "XILINX_VITIS", "XILINX_VIVADO"):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value))
    roots.extend(
        [
            Path("C:/Xilinx/Vitis_HLS/2024.2"),
            Path("C:/Xilinx/Vitis/2024.2"),
            Path("C:/Xilinx/Vivado/2024.2"),
        ]
    )
    roots.extend(_amd_roots())
    return roots


def find_vitis_hls() -> Path | None:
    path_hit = shutil.which("vitis_hls") or shutil.which("vitis_hls.bat") or shutil.which("vitis_hls.exe")
    if path_hit:
        return Path(path_hit)

    for candidate in _candidate_paths():
        if candidate.exists():
            return candidate
    return None


def find_vitis_hls_batch() -> Path | None:
    for root in _roots():
        for candidate in (root / "bin" / "vitis_hls.bat", root / "bin" / "vitis_hls"):
            if candidate.exists():
                return candidate
    return None


def find_settings64() -> Path | None:
    for root in _roots():
        candidate = root / "settings64.bat"
        if candidate.exists():
            return candidate
    return None


def find_gnuwin_bin() -> Path | None:
    for root in _roots():
        candidate = root / "gnuwin" / "bin"
        if candidate.exists():
            return candidate
    return None


def find_mingw_runtime_bin() -> Path | None:
    for root in _roots():
        install_root = root.parent if root.name in {"Vitis", "Vivado"} else root
        for version in ("10.0.0", "6.2.0"):
            candidate = install_root / "tps" / "mingw" / version / "win64.o" / "nt" / "bin"
            if (
                candidate.is_dir()
                and (candidate / "libstdc++-6.dll").is_file()
                and (candidate / "libgcc_s_seh-1.dll").is_file()
            ):
                return candidate
    return None


def find_vivado_batch() -> Path | None:
    path_hit = shutil.which("vivado.bat") or shutil.which("vivado")
    if path_hit:
        return Path(path_hit)

    for root in _roots():
        for candidate in (root / "bin" / "vivado.bat", root / "bin" / "vivado"):
            if candidate.exists():
                return candidate
    return None

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "golden" / "qwen_capture_status.md"
CAPTURE_CANDIDATES = (
    ROOT / "data" / "calibration" / "qwen3_next_80b_a3b_layer12.npz",
    ROOT / "data" / "calibration" / "qwen3_next_1p5b_a3b_layer12.npz",
)


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture_metadata(path: Path) -> dict[str, object] | None:
    try:
        with np.load(path, allow_pickle=False) as data:
            if "metadata_json" not in data.files:
                return None
            metadata = json.loads(str(data["metadata_json"].item()))
            required = {"source", "model_id", "layer_index", "captured_arrays"}
            if not required <= set(metadata):
                return None
            if metadata["source"] != "huggingface_qwen3_next":
                return None
            if not str(metadata["model_id"]).startswith("Qwen/Qwen3-Next-"):
                return None
            if "layer_input" not in data.files or "layer_output" not in data.files:
                return None
            return metadata
    except Exception:
        return None


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    available = [(path, _capture_metadata(path)) for path in CAPTURE_CANDIDATES if path.exists()]
    valid = [(path, metadata) for path, metadata in available if metadata is not None]
    missing_deps = [name for name in ("torch", "transformers", "datasets") if not _has_module(name)]

    lines = [
        "# Qwen Capture Status",
        "",
        "Generated: deterministic local capture/dependency check",
        "",
    ]
    if valid:
        path, metadata = valid[0]
        lines.extend(
            [
                "Status: available",
                "",
                f"- Capture file: `{path.relative_to(ROOT).as_posix()}`",
                f"- Model: `{metadata['model_id']}`",
                f"- Layer index: {metadata['layer_index']}",
                f"- SHA256: `{_sha256(path)}`",
                f"- Size: {path.stat().st_size} bytes",
            ]
        )
    elif available:
        path, _metadata = available[0]
        lines.extend(
            [
                "Status: invalid_capture",
                "",
                f"- Found `{path.relative_to(ROOT).as_posix()}`, but it does not match the required Qwen3-Next capture schema.",
                "- Re-run `python -m scripts.qwen_capture` with a canonical `Qwen/Qwen3-Next-*` HuggingFace model.",
            ]
        )
    elif missing_deps:
        lines.extend(
            [
                "Status: dependency_blocked",
                "",
                "- No Qwen3-Next activation capture exists under `data/calibration/`.",
                "- Expected one of:",
                *[f"  - `{path.relative_to(ROOT).as_posix()}`" for path in CAPTURE_CANDIDATES],
            ]
        )
    else:
        lines.extend(
            [
                "Status: capture_missing",
                "",
                "- Qwen capture dependencies are installed, but no Qwen3-Next activation capture exists under `data/calibration/`.",
                "- Expected one of:",
                *[f"  - `{path.relative_to(ROOT).as_posix()}`" for path in CAPTURE_CANDIDATES],
                "- Capture data is intentionally not synthesized or substituted by the benchmark pipeline.",
            ]
        )
    lines.extend(
        [
            "",
            "Dependency check:",
            "",
            f"- torch: {'available' if _has_module('torch') else 'missing'}",
            f"- transformers: {'available' if _has_module('transformers') else 'missing'}",
            f"- datasets: {'available' if _has_module('datasets') else 'missing'}",
            "",
        ]
    )
    if missing_deps:
        lines.extend(
            [
                "Resolution:",
                "",
                "- Install the `full` optional dependency set before collecting Qwen activations.",
                "- Capture data is intentionally not synthesized or substituted by the benchmark pipeline.",
                "",
            ]
        )
    elif not available:
        lines.extend(
            [
                "Resolution:",
                "",
                "- Collect the real HuggingFace Qwen3-Next layer-12 activation capture before claiming realistic PPL/accuracy.",
                "- The dependency blocker is resolved; this status now means only that the capture artifact itself is absent.",
                "",
            ]
        )
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(REPORT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

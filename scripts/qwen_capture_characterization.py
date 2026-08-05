"""Characterize a pinned Qwen capture without overstating recurrence coverage."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPTURE = (
    ROOT / "data" / "calibration" / "qwen3_next_80b_a3b_layer12.npz"
)
DEFAULT_JSON = ROOT / "reports" / "golden" / "qwen_capture_characterization.json"
DEFAULT_CSV = ROOT / "reports" / "golden" / "qwen_capture_characterization.csv"
RECURRENT_TENSORS = {"q", "k", "v", "alpha", "beta"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _git_revision() -> str:
    return subprocess.check_output(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "rev-parse",
            "HEAD",
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _stats(values: np.ndarray) -> dict[str, int | float]:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    if flat.size == 0 or not np.isfinite(flat).all():
        raise ValueError("captured tensor must be nonempty and finite")
    absolute = np.abs(flat)
    return {
        "elements": int(flat.size),
        "minimum": float(np.min(flat)),
        "maximum": float(np.max(flat)),
        "mean": float(np.mean(flat)),
        "standard_deviation": float(np.std(flat)),
        "zero_fraction": float(np.count_nonzero(flat == 0.0) / flat.size),
        "abs_p50": float(np.percentile(absolute, 50.0)),
        "abs_p90": float(np.percentile(absolute, 90.0)),
        "abs_p99": float(np.percentile(absolute, 99.0)),
        "abs_p999": float(np.percentile(absolute, 99.9)),
        "abs_max": float(np.max(absolute)),
    }


def characterize(capture: Path) -> dict[str, object]:
    with np.load(capture, allow_pickle=False) as data:
        if "metadata_json" not in data.files:
            raise ValueError("capture metadata_json is absent")
        metadata = json.loads(str(data["metadata_json"].item()))
        if metadata.get("source") != "huggingface_qwen3_next":
            raise ValueError("capture is not labeled as HuggingFace Qwen3-Next")
        arrays = {
            name: _stats(data[name])
            for name in data.files
            if name != "metadata_json"
            and np.issubdtype(data[name].dtype, np.floating)
        }
        present = set(data.files)

    missing_recurrent = sorted(RECURRENT_TENSORS - present)
    return {
        "schema": 1,
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": _git_revision(),
        "capture": {
            "path": _display_path(capture),
            "sha256": _sha256(capture),
            "bytes": capture.stat().st_size,
            "metadata": metadata,
        },
        "floating_tensors": arrays,
        "recurrence_coverage": {
            "required_tensors": sorted(RECURRENT_TENSORS),
            "missing_tensors": missing_recurrent,
            "complete": not missing_recurrent,
            "closed_loop_quality_supported": False,
        },
        "interpretation": (
            "Real Qwen activation-range evidence only; this capture cannot measure "
            "GDN recurrent-state error or end-to-end model quality."
        ),
    }


def write_outputs(report: dict[str, object], json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fieldnames = [
        "tensor",
        "elements",
        "minimum",
        "maximum",
        "mean",
        "standard_deviation",
        "zero_fraction",
        "abs_p50",
        "abs_p90",
        "abs_p99",
        "abs_p999",
        "abs_max",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for name, values in report["floating_tensors"].items():
            writer.writerow({"tensor": name, **values})


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args(argv)
    report = characterize(_resolve(args.capture))
    write_outputs(report, _resolve(args.json), _resolve(args.csv))
    print(
        json.dumps(
            {
                "status": report["status"],
                "recurrence_complete": report["recurrence_coverage"]["complete"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

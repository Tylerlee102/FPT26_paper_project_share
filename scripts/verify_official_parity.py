"""Independently verify the pinned official recurrence-parity artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


EXPECTED_TRANSFORMERS_COMMIT = "8ac2b916b042b1f78b75c9eb941c0f5d2cdd8e10"
EXPECTED_FLA_COMMIT = "a670dff4c2537fc1a82486584dd9569e18fba833"
EXPECTED_COMPARISONS = {
    "numpy_fp32_vs_transformers_recurrent_fp32": (
        "numpy_output",
        "transformers_recurrent_fp32",
        "numpy_state",
        "transformers_recurrent_state_fp32",
        "fp32",
    ),
    "transformers_chunk_fp32_vs_recurrent_fp32": (
        "transformers_recurrent_fp32",
        "transformers_chunk_fp32",
        "transformers_recurrent_state_fp32",
        "transformers_chunk_state_fp32",
        "fp32",
    ),
    "transformers_cache_fp32_vs_recurrent_fp32": (
        "transformers_recurrent_fp32",
        "transformers_cache_fp32",
        "transformers_recurrent_state_fp32",
        "transformers_cache_state_fp32",
        "fp32",
    ),
    "fla_recurrent_bf16_vs_transformers_recurrent_bf16": (
        "transformers_recurrent_bf16",
        "fla_recurrent_bf16",
        "transformers_recurrent_state_bf16",
        "fla_recurrent_state_bf16",
        "bf16",
    ),
    "fla_chunk_bf16_vs_transformers_recurrent_bf16": (
        "transformers_recurrent_bf16",
        "fla_chunk_bf16",
        "transformers_recurrent_state_bf16",
        "fla_chunk_state_bf16",
        "bf16",
    ),
    "fla_cache_bf16_vs_transformers_recurrent_bf16": (
        "transformers_recurrent_bf16",
        "fla_cache_bf16",
        "transformers_recurrent_state_bf16",
        "fla_cache_state_bf16",
        "bf16",
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _git_commit(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()


def _metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    ref = np.array(reference, dtype=np.float64, copy=True).ravel()
    got = np.array(candidate, dtype=np.float64, copy=True).ravel()
    if ref.shape != got.shape or not np.isfinite(ref).all() or not np.isfinite(got).all():
        raise ValueError("invalid arrays in parity output archive")
    delta = got - ref
    ref_norm = float(np.sqrt(np.sum(ref * ref, dtype=np.float64)))
    got_norm = float(np.sqrt(np.sum(got * got, dtype=np.float64)))
    product = ref_norm * got_norm
    if product <= 1e-24:
        cosine = 1.0 if ref_norm <= 1e-12 and got_norm <= 1e-12 else 0.0
    else:
        cosine = float(np.sum(ref * got, dtype=np.float64) / product)
    return {
        "cosine": max(-1.0, min(1.0, cosine)),
        "rel_l2": float(np.sqrt(np.sum(delta * delta, dtype=np.float64)) / max(ref_norm, 1e-12)),
        "max_abs": float(np.max(np.abs(delta))) if delta.size else 0.0,
    }


def _assert_close(label: str, observed: float, expected: float) -> None:
    if not np.isclose(observed, expected, rtol=1e-12, atol=1e-15):
        raise AssertionError(f"{label}: CSV={observed!r}, recomputed={expected!r}")


def verify(
    evidence_dir: Path,
    *,
    transformers_source: Path,
    fla_source: Path,
) -> dict[str, object]:
    manifest_path = evidence_dir / "official_parity_manifest.json"
    metrics_path = evidence_dir / "official_parity_metrics.csv"
    arrays_path = evidence_dir / "official_parity_outputs.npz"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with metrics_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if manifest.get("status") != "PASS":
        raise AssertionError("manifest status is not PASS")
    if len(rows) != len(EXPECTED_COMPARISONS):
        raise AssertionError("unexpected comparison count")
    if {row["comparison"] for row in rows} != set(EXPECTED_COMPARISONS):
        raise AssertionError("comparison names differ from the frozen set")
    if any(row["status"] != "PASS" for row in rows):
        raise AssertionError("one or more metric rows are not PASS")

    for artifact_name, expected_hash in manifest["artifact_hashes"].items():
        actual_hash = _sha256(evidence_dir / artifact_name)
        if actual_hash != expected_hash:
            raise AssertionError(f"artifact hash mismatch: {artifact_name}")

    expected_sources = {
        "transformers_modeling": transformers_source
        / "src/transformers/models/qwen3_next/modeling_qwen3_next.py",
        "fla_recurrent": fla_source / "fla/ops/gated_delta_rule/fused_recurrent.py",
        "fla_chunk": fla_source / "fla/ops/gated_delta_rule/chunk.py",
        "fla_wy": fla_source / "fla/ops/gated_delta_rule/wy_fast.py",
        "local_fp32": Path(__file__).resolve().parents[1] / "golden/gdn_fp32.py",
        "parity_harness": Path(__file__).resolve().parent / "official_parity.py",
    }
    for source_name, source_path in expected_sources.items():
        if _sha256(source_path) != manifest["source_hashes"][source_name]:
            raise AssertionError(f"source hash mismatch: {source_name}")
    if _git_commit(transformers_source) != EXPECTED_TRANSFORMERS_COMMIT:
        raise AssertionError("Transformers commit mismatch")
    if _git_commit(fla_source) != EXPECTED_FLA_COMMIT:
        raise AssertionError("FLA commit mismatch")

    recomputed: dict[str, dict[str, float]] = {}
    with np.load(arrays_path, allow_pickle=False) as arrays:
        for row in rows:
            output_ref, output_got, state_ref, state_got, precision = EXPECTED_COMPARISONS[
                row["comparison"]
            ]
            if row["precision"] != precision:
                raise AssertionError(f"precision mismatch: {row['comparison']}")
            output = _metrics(arrays[output_ref], arrays[output_got])
            state = _metrics(arrays[state_ref], arrays[state_got])
            for prefix, values in (("output", output), ("state", state)):
                for metric_name, expected in values.items():
                    _assert_close(
                        f"{row['comparison']}:{prefix}_{metric_name}",
                        float(row[f"{prefix}_{metric_name}"]),
                        expected,
                    )
            recomputed[row["comparison"]] = {
                "output_rel_l2": output["rel_l2"],
                "state_rel_l2": state["rel_l2"],
            }

    manifest_rows = {row["comparison"]: row for row in manifest["comparisons"]}
    for row in rows:
        manifest_row = manifest_rows.get(row["comparison"])
        if manifest_row is None or manifest_row.get("status") != "PASS":
            raise AssertionError(f"manifest comparison mismatch: {row['comparison']}")

    return {
        "schema": 1,
        "status": "PASS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, *sys.argv],
        "verified_manifest_sha256": _sha256(manifest_path),
        "verified_metric_rows": len(rows),
        "verified_artifact_hashes": len(manifest["artifact_hashes"]),
        "verified_source_hashes": len(manifest["source_hashes"]),
        "recomputed": recomputed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_dir", type=Path)
    parser.add_argument(
        "--transformers-source",
        type=Path,
        default=Path("/opt/gdn-parity/src/transformers"),
    )
    parser.add_argument(
        "--fla-source",
        type=Path,
        default=Path("/opt/gdn-parity/src/flash-linear-attention"),
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify(
        args.evidence_dir,
        transformers_source=args.transformers_source,
        fla_source=args.fla_source,
    )
    report_path = args.report or args.evidence_dir / "official_parity_verification.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"PASS: recomputed {report['verified_metric_rows']} comparisons; "
        f"verified {report['verified_artifact_hashes']} artifacts and "
        f"{report['verified_source_hashes']} sources"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

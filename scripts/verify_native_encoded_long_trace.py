"""Independently verify the native encoded MXFP4 long-trace artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from golden.gdn_mxfp4_encoded import EncodedState, decode_state
from scripts.evidence_source_snapshot import describe_source_files
from scripts.native_encoded_long_trace import (
    COUNTER_FIELDS,
    DEFAULT_CHECKPOINT_CSV,
    DEFAULT_MANIFEST,
    DEFAULT_TOKEN_CSV,
    FLOATING_MANIFEST,
    VARIANT,
    VECTOR_REPORT,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "native_encoded_long_trace_verification.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    reference64 = np.asarray(reference, dtype=np.float64)
    candidate64 = np.asarray(candidate, dtype=np.float64)
    difference = candidate64 - reference64
    reference_norm = float(np.linalg.norm(reference64.reshape(-1)))
    candidate_norm = float(np.linalg.norm(candidate64.reshape(-1)))
    denominator = max(reference_norm, 1e-12)
    if reference_norm == 0.0 and candidate_norm == 0.0:
        cosine = 1.0
    elif reference_norm == 0.0 or candidate_norm == 0.0:
        cosine = 0.0
    else:
        cosine = float(
            np.dot(reference64.reshape(-1), candidate64.reshape(-1))
            / (reference_norm * candidate_norm)
        )
    return {
        "cosine": cosine,
        "rel_l2": float(np.linalg.norm(difference.reshape(-1)) / denominator),
        "max_abs": float(np.max(np.abs(difference))) if difference.size else 0.0,
    }


def _close(actual: str, expected: float, name: str) -> None:
    if not np.isclose(float(actual), expected, rtol=1e-12, atol=1e-12):
        raise ValueError(f"checkpoint metric mismatch: {name}")


def verify_native_encoded_long_trace(
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS":
        raise ValueError("native encoded long-trace generation is not PASS")
    config = manifest["configuration"]
    tokens = int(config["tokens"])
    checkpoints = [int(value) for value in config["checkpoints"]]
    if tokens != 8192 or checkpoints != [64, 256, 1024, 4096, 8192]:
        raise ValueError("native encoded long trace is not the required run")
    if manifest.get("variant") != VARIANT:
        raise ValueError("native encoded variant identity mismatch")

    output_meta = manifest["outputs"]
    for relative_path, metadata in output_meta.items():
        path = ROOT / relative_path
        if _sha256(path) != metadata["sha256"] or path.stat().st_size != metadata["bytes"]:
            raise ValueError(f"output hash or size mismatch: {relative_path}")
    if _sha256(VECTOR_REPORT) != manifest["vectorized_oracle_crosscheck"]["sha256"]:
        raise ValueError("vectorized-oracle cross-check hash mismatch")
    vector_report = json.loads(VECTOR_REPORT.read_text(encoding="utf-8"))
    if vector_report.get("status") != "PASS" or vector_report["configuration"]["tokens"] != 64:
        raise ValueError("vectorized-oracle cross-check is not a 64-token PASS")
    if _sha256(FLOATING_MANIFEST) != manifest["shared_floating_trace"]["sha256"]:
        raise ValueError("shared floating-trace manifest hash mismatch")
    floating = json.loads(FLOATING_MANIFEST.read_text(encoding="utf-8"))
    if manifest["input_stream_sha256"] != floating["input_sha256"].upper():
        raise ValueError("input-stream identity mismatch")
    if manifest["initial_state_sha256"] != floating["initial_state_sha256"].upper():
        raise ValueError("initial-state identity mismatch")

    with DEFAULT_TOKEN_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with DEFAULT_CHECKPOINT_CSV.open(newline="", encoding="utf-8") as handle:
        checkpoint_rows = list(csv.DictReader(handle))
    if len(rows) != tokens or [int(row["token_index"]) for row in rows] != list(
        range(1, tokens + 1)
    ):
        raise ValueError("token CSV does not contain one ordered row per token")
    if any(row["variant"] != VARIANT for row in rows):
        raise ValueError("token CSV contains an unexpected variant")
    projected = [row for row in rows if int(row["token_index"]) in checkpoints]
    if checkpoint_rows != projected:
        raise ValueError("checkpoint CSV is not an exact token-CSV projection")

    cumulative = {field: 0 for field in COUNTER_FIELDS}
    for row in rows:
        numeric_metrics = (
            "output_cosine_fp32",
            "output_rel_l2",
            "output_max_abs",
            "state_rel_l2",
            "state_max_abs",
        )
        if not all(np.isfinite(float(row[field])) for field in numeric_metrics):
            raise ValueError("token CSV contains a non-finite metric")
        if not -1.0 <= float(row["output_cosine_fp32"]) <= 1.0:
            raise ValueError("token CSV contains an invalid cosine")
        for field in COUNTER_FIELDS:
            command = int(row[f"command_{field}"])
            if command < 0:
                raise ValueError("token CSV contains a negative event counter")
            cumulative[field] += command
            if int(row[f"cumulative_{field}"]) != cumulative[field]:
                raise ValueError(f"cumulative counter mismatch: {field}")
        if row["event_metrics_status"] != "PASS":
            raise ValueError("native encoded event metrics are not PASS")

    snapshots = manifest["snapshots"]
    expected_snapshot_tokens = [0, *checkpoints]
    if sorted(int(meta["token_index"]) for meta in snapshots.values()) != expected_snapshot_tokens:
        raise ValueError("required full-state snapshots are absent")
    checkpoint_by_token = {
        int(row["token_index"]): row for row in checkpoint_rows
    }
    for relative_path, metadata in snapshots.items():
        path = ROOT / relative_path
        if _sha256(path) != metadata["sha256"] or path.stat().st_size != metadata["bytes"]:
            raise ValueError(f"snapshot hash or size mismatch: {relative_path}")
        with np.load(path, allow_pickle=False) as snapshot:
            token_index = int(snapshot["token_index"][0])
            if token_index != int(metadata["token_index"]):
                raise ValueError("snapshot token metadata mismatch")
            reference_state = snapshot["reference_state"]
            encoded_state = EncodedState(
                snapshot["encoded_state_elements"],
                snapshot["encoded_state_scales"],
                int(snapshot["block_size"][0]),
            )
            if reference_state.shape != (32, 128, 128):
                raise ValueError("snapshot reference-state shape mismatch")
            if encoded_state.elements.shape != reference_state.shape:
                raise ValueError("snapshot encoded-state shape mismatch")
            if token_index == 0:
                continue
            row = checkpoint_by_token[token_index]
            state_metrics = _metrics(reference_state, decode_state(encoded_state))
            output_metrics = _metrics(
                snapshot["reference_output"], snapshot["encoded_output"]
            )
            _close(row["state_rel_l2"], state_metrics["rel_l2"], "state rel L2")
            _close(row["state_max_abs"], state_metrics["max_abs"], "state max abs")
            _close(row["output_cosine_fp32"], output_metrics["cosine"], "output cosine")
            _close(row["output_rel_l2"], output_metrics["rel_l2"], "output rel L2")
            _close(row["output_max_abs"], output_metrics["max_abs"], "output max abs")

    final = checkpoint_rows[-1]
    cosine_pass = all(float(row["output_cosine_fp32"]) >= 0.99 for row in checkpoint_rows)
    state_pass = float(final["state_rel_l2"]) <= 0.10
    saturation_pass = all(
        int(final[f"cumulative_{field}"]) == 0
        for field in (
            "element_saturations",
            "accumulator_saturations",
            "scale_clamps",
        )
    )
    expected_gate = "PASS" if cosine_pass and state_pass and saturation_pass else "FAIL"
    if manifest["engineering_gate"]["status"] != expected_gate:
        raise ValueError("engineering-gate status is not reproducible")

    source_identity = describe_source_files(
        [
            Path(__file__).resolve(),
            ROOT / "scripts" / "native_encoded_long_trace.py",
            ROOT / "golden" / "gdn_mxfp4_encoded_vectorized.py",
        ]
    )
    return {
        "schema": 1,
        "status": "PASS",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": _sha256(manifest_path),
        "token_csv_sha256": _sha256(DEFAULT_TOKEN_CSV),
        "checkpoint_csv_sha256": _sha256(DEFAULT_CHECKPOINT_CSV),
        "rows_verified": len(rows),
        "checkpoint_rows_verified": len(checkpoint_rows),
        "snapshots_verified": len(snapshots),
        "input_stream_match": "PASS",
        "initial_state_match": "PASS",
        "counter_recurrence": "PASS",
        "checkpoint_metric_recomputation": "PASS",
        "engineering_gate": expected_gate,
        "source_revision": source_identity["git_revision"],
        "source_identity": source_identity,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "command": "python -m scripts.verify_native_encoded_long_trace",
        "exit_code": 0,
        "limitations": manifest["limitations"],
    }


def main() -> int:
    result = verify_native_encoded_long_trace()
    DEFAULT_OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "engineering_gate": result["engineering_gate"],
                "rows": result["rows_verified"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

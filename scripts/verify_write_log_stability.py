"""Independently verify a write-log stability manifest and its CSV outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPACITY_PATTERN = re.compile(r"_r([0-9]+)$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _blocked_bytes(length: int, block_size: int, bytes_per_block: int) -> int:
    return ((length + block_size - 1) // block_size) * bytes_per_block


def _expected_storage_bytes(
    config: dict[str, object],
    *,
    capacity: int,
    log_precision: str,
    base_stack_depth: int,
    base_residual_block_fraction: float,
) -> int:
    value_heads = int(config["num_value_heads"])
    qk_heads = int(config["num_qk_heads"])
    key_dim = int(config["key_dim"])
    value_dim = int(config["value_dim"])
    block_size = int(config["state_block_size"])
    base_row = _blocked_bytes(value_dim, block_size, block_size // 2 + 1)
    rows = value_heads * key_dim
    base = rows * base_row
    if base_stack_depth > 1:
        blocks_per_row = (value_dim + block_size - 1) // block_size
        selected_blocks = min(
            blocks_per_row,
            math.ceil(blocks_per_row * base_residual_block_fraction),
        )
        bitmap_bytes = (
            0
            if base_residual_block_fraction >= 1.0
            else math.ceil(blocks_per_row / 8)
        )
        residual_layer = rows * (
            selected_blocks * (block_size // 2 + 1) + bitmap_bytes
        )
        base += (base_stack_depth - 1) * residual_layer
    if log_precision == "mxfp8_e4m3":
        key_row = _blocked_bytes(key_dim, block_size, block_size + 1)
        update_row = _blocked_bytes(value_dim, block_size, block_size + 1)
        vectors = capacity * (qk_heads * key_row + value_heads * update_row)
    elif log_precision in {"bf16", "fp16"}:
        vectors = capacity * 2 * (qk_heads * key_dim + value_heads * value_dim)
    elif log_precision == "fp32":
        vectors = capacity * 4 * (qk_heads * key_dim + value_heads * value_dim)
    else:
        raise ValueError(f"unknown log precision: {log_precision}")
    coefficients = 4 * (value_heads + capacity * value_heads)
    return base + vectors + coefficients + 16


def verify(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    outputs = dict(manifest.get("outputs", {}))
    if len(outputs) != 2:
        failures.append("manifest must name exactly two CSV outputs")
    output_paths: dict[str, Path] = {}
    for relative, expected_hash in outputs.items():
        path = ROOT / relative
        output_paths[relative] = path
        if not path.is_file():
            failures.append(f"missing output: {relative}")
        elif _sha256(path) != expected_hash:
            failures.append(f"output hash mismatch: {relative}")

    for relative, expected_hash in dict(manifest.get("source_hashes", {})).items():
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing source: {relative}")
        elif _sha256(path) != expected_hash:
            failures.append(f"source hash mismatch: {relative}")

    token_path = next((path for name, path in output_paths.items() if "tokens" in name), None)
    checkpoint_path = next(
        (path for name, path in output_paths.items() if "checkpoints" in name), None
    )
    token_rows = _load_rows(token_path) if token_path and token_path.is_file() else []
    checkpoint_rows = (
        _load_rows(checkpoint_path) if checkpoint_path and checkpoint_path.is_file() else []
    )
    config = dict(manifest["configuration"])
    tokens = int(config["tokens"])
    checkpoints = {int(value) for value in config["checkpoints"]}
    capacities = tuple(int(value) for value in manifest["capacities"])
    fold_policy = str(manifest.get("fold_policy", "fixed"))
    adaptive_min_entries = int(manifest.get("adaptive_min_entries", 1))
    variants_per_token = len(capacities) + 1
    if len(token_rows) != tokens * variants_per_token:
        failures.append("token row count mismatch")
    if len(checkpoint_rows) != len(checkpoints) * variants_per_token:
        failures.append("checkpoint row count mismatch")

    token_keys: dict[tuple[int, str], dict[str, str]] = {}
    for row in token_rows:
        key = (int(row["token_index"]), row["variant"])
        if key in token_keys:
            failures.append(f"duplicate token row: {key}")
        token_keys[key] = row
        if key[0] < 1 or key[0] > tokens:
            failures.append(f"token index out of range: {key[0]}")
        for field in (
            "output_cosine_fp32",
            "output_rel_l2",
            "output_max_abs",
            "state_rel_l2",
            "state_max_abs",
        ):
            if not math.isfinite(float(row[field])):
                failures.append(f"nonfinite {field} at {key}")
        cosine = float(row["output_cosine_fp32"])
        if cosine < -1.0000001 or cosine > 1.0000001:
            failures.append(f"cosine out of range at {key}")

        if row["variant"] == "fp32":
            if cosine != 1.0 or float(row["state_rel_l2"]) != 0.0:
                failures.append(f"FP32 self-reference mismatch at token {key[0]}")
            continue
        match = CAPACITY_PATTERN.search(row["variant"])
        if match is None:
            failures.append(f"candidate capacity missing from variant: {row['variant']}")
            continue
        capacity = int(match.group(1))
        if capacity not in capacities:
            failures.append(f"unexpected capacity {capacity}")
        folds = int(row["folds"])
        live_entries = int(row["live_entries"])
        if fold_policy == "fixed":
            expected_folds = key[0] // capacity
            expected_live = key[0] % capacity
            if folds != expected_folds:
                failures.append(f"fold count mismatch at {key}")
            if live_entries != expected_live:
                failures.append(f"live-entry count mismatch at {key}")
        else:
            if not 0 <= live_entries < capacity:
                failures.append(f"adaptive live-entry bound failed at {key}")
            if folds < key[0] // capacity:
                failures.append(f"adaptive fold count too small at {key}")
            if folds * adaptive_min_entries > key[0]:
                failures.append(f"adaptive fold count exceeds minimum interval at {key}")
        if int(row["dropped_entries"]) != 0:
            failures.append(f"dropped write at {key}")
        expected_bytes = _expected_storage_bytes(
            config,
            capacity=capacity,
            log_precision=str(manifest["log_precision"]),
            base_stack_depth=int(manifest["base_stack_depth"]),
            base_residual_block_fraction=float(
                manifest.get("base_residual_block_fraction", 1.0)
            ),
        )
        if int(row["logical_state_bytes"]) != expected_bytes:
            failures.append(f"logical storage mismatch at {key}")

    if {key[0] for key in token_keys} != set(range(1, tokens + 1)):
        failures.append("token coverage mismatch")
    checkpoint_keys: set[tuple[int, str]] = set()
    for row in checkpoint_rows:
        key = (int(row["token_index"]), row["variant"])
        if key in checkpoint_keys:
            failures.append(f"duplicate checkpoint row: {key}")
        checkpoint_keys.add(key)
        if key[0] not in checkpoints:
            failures.append(f"unexpected checkpoint token: {key[0]}")
        if token_keys.get(key) != row:
            failures.append(f"checkpoint row does not equal token row: {key}")

    final_candidates = [
        row
        for row in checkpoint_rows
        if int(row["token_index"]) == tokens and row["variant"] != "fp32"
    ]
    gate_pass = bool(final_candidates)
    gate_pass = gate_pass and all(
        float(row["output_cosine_fp32"]) >= 0.99
        for row in checkpoint_rows
        if row["variant"] != "fp32"
    )
    gate_pass = gate_pass and all(
        float(row["state_rel_l2"]) <= 0.10 for row in final_candidates
    )
    if not gate_pass:
        failures.append("preregistered synthetic checkpoint gate failed")

    status = "PASS" if not failures else "FAIL"
    return {
        "schema": 1,
        "status": status,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "manifest_sha256": _sha256(manifest_path),
        "token_rows": len(token_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "gate_pass": gate_pass,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest",
        type=Path,
        nargs="?",
        default=Path(
            "reports/benchmark/corrected/write_log_development_manifest.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "reports/benchmark/corrected/write_log_development_verification.json"
        ),
    )
    args = parser.parse_args(argv)
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    output = args.output if args.output.is_absolute() else ROOT / args.output
    result = verify(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

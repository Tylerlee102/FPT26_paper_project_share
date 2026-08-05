"""Independently verify E2M0 fold-residual stability artifacts."""

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


def _expected_bytes(manifest: dict[str, object]) -> int:
    config = dict(manifest["configuration"])
    value_heads = int(config["num_value_heads"])
    qk_heads = int(config["num_qk_heads"])
    key_dim = int(config["key_dim"])
    value_dim = int(config["value_dim"])
    block_size = int(config["state_block_size"])
    capacity = int(manifest["capacity"])
    base_depth = int(manifest["base_stack_depth"])
    rows = value_heads * key_dim
    base_row = _blocked_bytes(value_dim, block_size, block_size // 2 + 1)
    residual_block = math.ceil(block_size * 3 / 8) + 1
    residual_row = _blocked_bytes(value_dim, block_size, residual_block)
    base = rows * (base_row + max(0, base_depth - 1) * residual_row)
    log_mode = str(manifest["log_mode"])
    if log_mode == "mxfp4_rs2":
        log_block = 2 * (block_size // 2 + 1)
    elif log_mode == "mxfp8_e4m3":
        log_block = block_size + 1
    else:
        raise ValueError(f"unknown log mode: {log_mode}")
    key_row = _blocked_bytes(key_dim, block_size, log_block)
    update_row = _blocked_bytes(value_dim, block_size, log_block)
    log = capacity * (qk_heads * key_row + value_heads * update_row)
    coefficients = 4 * (value_heads + capacity * value_heads)
    return base + log + coefficients + 16


def verify(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if manifest.get("base_residual_element_bits") != 3:
        failures.append("residual element width is not 3 bits")
    if manifest.get("base_residual_values") != [0.0, 0.5, 1.0, 2.0]:
        failures.append("residual value table mismatch")
    if manifest.get("base_residual_scale_policy") != "min_sse_adjacent_e8m0":
        failures.append("residual scale policy mismatch")
    if manifest.get("log_mode") not in {"mxfp4_rs2", "mxfp8_e4m3"}:
        failures.append("log mode mismatch")
    expected_log_depth = 2 if manifest.get("log_mode") == "mxfp4_rs2" else 1
    if manifest.get("log_stack_depth") != expected_log_depth:
        failures.append("log stack depth mismatch")

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
    capacity = int(manifest["capacity"])
    variant = str(manifest["variant"])
    match = CAPACITY_PATTERN.search(variant)
    if match is None or int(match.group(1)) != capacity:
        failures.append("variant capacity mismatch")
    if len(token_rows) != tokens * 2:
        failures.append("token row count mismatch")
    if len(checkpoint_rows) != len(checkpoints) * 2:
        failures.append("checkpoint row count mismatch")

    expected_bytes = _expected_bytes(manifest)
    if int(manifest.get("logical_state_bytes", -1)) != expected_bytes:
        failures.append("manifest logical storage mismatch")
    token_keys: dict[tuple[int, str], dict[str, str]] = {}
    for row in token_rows:
        key = (int(row["token_index"]), row["variant"])
        if key in token_keys:
            failures.append(f"duplicate token row: {key}")
        token_keys[key] = row
        for field in (
            "output_cosine_fp32",
            "output_rel_l2",
            "output_max_abs",
            "state_rel_l2",
            "state_max_abs",
        ):
            if not math.isfinite(float(row[field])):
                failures.append(f"nonfinite {field} at {key}")
        if row["variant"] == "fp32":
            if float(row["output_cosine_fp32"]) != 1.0:
                failures.append(f"FP32 cosine mismatch at {key}")
            if float(row["state_rel_l2"]) != 0.0:
                failures.append(f"FP32 state mismatch at {key}")
        else:
            if row["variant"] != variant:
                failures.append(f"unexpected candidate variant at {key}")
            if int(row["folds"]) != key[0] // capacity:
                failures.append(f"fold count mismatch at {key}")
            if int(row["live_entries"]) != key[0] % capacity:
                failures.append(f"live-entry count mismatch at {key}")
            if int(row["dropped_entries"]) != 0:
                failures.append(f"dropped write at {key}")
            if int(row["logical_state_bytes"]) != expected_bytes:
                failures.append(f"logical storage mismatch at {key}")

    if {key[0] for key in token_keys} != set(range(1, tokens + 1)):
        failures.append("token coverage mismatch")
    checkpoint_keys: set[tuple[int, str]] = set()
    for row in checkpoint_rows:
        key = (int(row["token_index"]), row["variant"])
        checkpoint_keys.add(key)
        if key[0] not in checkpoints:
            failures.append(f"unexpected checkpoint token: {key[0]}")
        if token_keys.get(key) != row:
            failures.append(f"checkpoint row does not equal token row: {key}")

    candidate_checkpoints = [
        row for row in checkpoint_rows if row["variant"] == variant
    ]
    final = [row for row in candidate_checkpoints if int(row["token_index"]) == tokens]
    gate_pass = bool(final)
    gate_pass = gate_pass and all(
        float(row["output_cosine_fp32"]) >= 0.99 for row in candidate_checkpoints
    )
    gate_pass = gate_pass and all(float(row["state_rel_l2"]) <= 0.10 for row in final)
    if not gate_pass:
        failures.append("preregistered synthetic checkpoint gate failed")

    return {
        "schema": 1,
        "status": "PASS" if not failures else "FAIL",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "manifest_sha256": _sha256(manifest_path),
        "token_rows": len(token_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "expected_logical_state_bytes": expected_bytes,
        "gate_pass": gate_pass,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    result = verify(manifest)
    output = args.output
    if output is None:
        output = manifest.with_name(manifest.stem.replace("_manifest", "_verification") + ".json")
    elif not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "gate_pass": result["gate_pass"]}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate RS2 fold-write/banking RTL with localized snapshot writes."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.rs2_fold_write_partial_banks_experiment import (
    SOURCE,
    generate as generate_parent,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "build"
    / "experiments"
    / "rs2_snapshot_write_partial_banks"
    / "gdn_rs2_top.cpp"
)
DEFAULT_MANIFEST = DEFAULT_OUTPUT.parent / "manifest.json"

HELPER = """void commit_snapshot_block(
    int head,
    int row,
    int block,
    state_primary_word_t primary_word,
    state_residual_word_t residual_word,
    resident_primary_slot_t primary,
    resident_residual_slot_t residual) {
#pragma HLS INLINE off
  primary[head][row][block] = primary_word;
  residual[head][row][block] = residual_word;
}

"""

OLD_WRITES = """        primary[head][row][block] = primary_word;
        residual[head][row][block] = residual_word;
"""

NEW_WRITES = """        commit_snapshot_block(
            head,
            row,
            block,
            primary_word,
            residual_word,
            primary,
            residual);
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def generate(output: Path, manifest_path: Path) -> dict[str, object]:
    parent_manifest_path = output.parent / ".parent_manifest.json"
    parent = generate_parent(output, parent_manifest_path)
    parent_sha256 = _sha256(output)
    transformed = output.read_text(encoding="utf-8")
    marker = "void load_snapshot(\n"
    if transformed.count(marker) != 1:
        raise RuntimeError("expected one load_snapshot insertion marker")
    before, after = transformed.split(marker, maxsplit=1)
    if after.count(OLD_WRITES) != 1:
        raise RuntimeError("expected one load_snapshot resident-write block")
    transformed = before + HELPER + marker + after.replace(OLD_WRITES, NEW_WRITES)

    output.write_text(transformed, encoding="utf-8", newline="\n")
    parent_manifest_path.unlink(missing_ok=True)
    manifest = {
        "schema": 1,
        "status": "PASS",
        "experiment": "RS2 localized snapshot/fold writes with six-way layer banks",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": _sha256(SOURCE),
        "parent_output_sha256": parent_sha256,
        "parent_transform": {
            "fold_write_transform": parent["fold_write_transform"],
            "partition_factor": parent["partition_factor"],
            "layers_per_bank": parent["layers_per_bank"],
        },
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": _sha256(output),
        "snapshot_write_transform": {
            "helpers": transformed.count("void commit_snapshot_block("),
            "replacements": transformed.count("        commit_snapshot_block(\n"),
        },
        "behavioral_contract": (
            "same arithmetic, state layout and capacity, commands, fold cadence, "
            "and layer banking; only LOAD resident-write hierarchy changes"
        ),
        "selected_source_modified": False,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    try:
        result = generate(output, manifest)
    except RuntimeError as exc:
        print(exc)
        return 1
    print(json.dumps({"status": result["status"], "output": result["output"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate an isolated RS2 variant with split primary/residual fold commits."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.rs2_fold_write_experiment import SOURCE, generate as generate_parent


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "build" / "experiments" / "rs2_split_fold_write" / "gdn_rs2_top.cpp"
)
DEFAULT_MANIFEST = DEFAULT_OUTPUT.parent / "manifest.json"

OLD_HELPER = """void commit_fold_block(
    int head,
    int row,
    int block,
    state_primary_word_t primary_word,
    state_residual_word_t residual_word,
    scale_t primary_scale,
    scale_t residual_scale,
    resident_primary_slot_t primary,
    resident_scale_slot_t primary_scales,
    resident_residual_slot_t residual,
    resident_scale_slot_t residual_scales) {
#pragma HLS INLINE off
  primary[head][row][block] = primary_word;
  residual[head][row][block] = residual_word;
  pack_scale(primary_scales[head][row], block, primary_scale);
  pack_scale(residual_scales[head][row], block, residual_scale);
}

"""

NEW_HELPERS = """void commit_primary_fold_block(
    int head,
    int row,
    int block,
    state_primary_word_t primary_word,
    scale_t primary_scale,
    resident_primary_slot_t primary,
    resident_scale_slot_t primary_scales) {
#pragma HLS INLINE off
  primary[head][row][block] = primary_word;
  pack_scale(primary_scales[head][row], block, primary_scale);
}

void commit_residual_fold_block(
    int head,
    int row,
    int block,
    state_residual_word_t residual_word,
    scale_t residual_scale,
    resident_residual_slot_t residual,
    resident_scale_slot_t residual_scales) {
#pragma HLS INLINE off
  residual[head][row][block] = residual_word;
  pack_scale(residual_scales[head][row], block, residual_scale);
}

"""

OLD_CALL = """  commit_fold_block(
      head,
      row,
      block,
      primary_word,
      residual_word,
      new_primary_scale,
      new_residual_scale,
      primary,
      primary_scales,
      residual,
      residual_scales);
"""

NEW_CALLS = """  commit_primary_fold_block(
      head,
      row,
      block,
      primary_word,
      new_primary_scale,
      primary,
      primary_scales);
  commit_residual_fold_block(
      head,
      row,
      block,
      residual_word,
      new_residual_scale,
      residual,
      residual_scales);
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def generate(output: Path, manifest_path: Path) -> dict[str, object]:
    parent_manifest_path = output.parent / ".parent_manifest.json"
    parent = generate_parent(output, parent_manifest_path)
    parent_sha256 = _sha256(output)
    transformed = output.read_text(encoding="utf-8")
    if transformed.count(OLD_HELPER) != 1:
        raise RuntimeError("expected one combined fold-write helper")
    if transformed.count(OLD_CALL) != 1:
        raise RuntimeError("expected one combined fold-write call")
    transformed = transformed.replace(OLD_HELPER, NEW_HELPERS)
    transformed = transformed.replace(OLD_CALL, NEW_CALLS)

    output.write_text(transformed, encoding="utf-8", newline="\n")
    parent_manifest_path.unlink(missing_ok=True)
    manifest = {
        "schema": 1,
        "status": "PASS",
        "experiment": "RS2 split primary/residual fold-write commits",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": _sha256(SOURCE),
        "parent_output_sha256": parent_sha256,
        "parent_transform": parent["transform"],
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": _sha256(output),
        "split_write_transform": {
            "combined_helpers_remaining": transformed.count(
                "void commit_fold_block("
            ),
            "primary_helpers": transformed.count(
                "void commit_primary_fold_block("
            ),
            "residual_helpers": transformed.count(
                "void commit_residual_fold_block("
            ),
            "primary_calls": transformed.count("  commit_primary_fold_block(\n"),
            "residual_calls": transformed.count("  commit_residual_fold_block(\n"),
        },
        "behavioral_contract": (
            "same arithmetic, state layout and capacity, commands, fold cadence, "
            "and write values; only primary/residual fold-write hierarchy changes"
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

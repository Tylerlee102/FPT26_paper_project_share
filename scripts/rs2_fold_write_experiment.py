"""Generate an isolated RS2 variant with localized fold control and writes."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.rs2_fold_control_experiment import HELPER as FOLD_CONTROL_HELPER
from scripts.rs2_fold_control_experiment import NEW_COMMIT, OLD_COMMIT, SOURCE


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "build" / "experiments" / "rs2_fold_write" / "gdn_rs2_top.cpp"
)
DEFAULT_MANIFEST = (
    ROOT / "build" / "experiments" / "rs2_fold_write" / "manifest.json"
)

WRITE_HELPER = """void commit_fold_block(
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

OLD_WRITES = """  primary[head][row][block] = primary_word;
  residual[head][row][block] = residual_word;
  pack_scale(primary_scales[head][row], block, new_primary_scale);
  pack_scale(residual_scales[head][row], block, new_residual_scale);
"""

NEW_WRITES = """  commit_fold_block(
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def generate(output: Path, manifest_path: Path) -> dict[str, object]:
    source = SOURCE.read_text(encoding="utf-8")
    reset_marker = "void reset_slot(\n"
    quantize_marker = "void quantize_fold_block(\n"
    required = {
        reset_marker: "reset insertion marker",
        quantize_marker: "quantize insertion marker",
        OLD_COMMIT: "fold-control block",
        OLD_WRITES: "fold-write block",
    }
    for marker, label in required.items():
        if source.count(marker) != 1:
            raise RuntimeError(f"expected one {label}")

    transformed = source.replace(
        quantize_marker, WRITE_HELPER + quantize_marker
    )
    transformed = transformed.replace(reset_marker, FOLD_CONTROL_HELPER + reset_marker)
    transformed = transformed.replace(OLD_WRITES, NEW_WRITES)
    transformed = transformed.replace(OLD_COMMIT, NEW_COMMIT)
    if transformed == source:
        raise RuntimeError("fold-write transform made no change")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(transformed, encoding="utf-8", newline="\n")
    manifest = {
        "schema": 1,
        "status": "PASS",
        "experiment": "RS2 localized fold control and write commit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": _sha256(SOURCE),
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": _sha256(output),
        "transform": {
            "fold_control_helpers": transformed.count("void fold_log_if_full("),
            "fold_control_replacements": transformed.count(
                "const int live_after_step = old_live + 1;"
            ),
            "fold_write_helpers": transformed.count("void commit_fold_block("),
            "fold_write_replacements": transformed.count("  commit_fold_block(\n"),
        },
        "behavioral_contract": (
            "same fold cadence, write order, counters, and command-visible state; "
            "only fold-control and resident-write hierarchy are changed"
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

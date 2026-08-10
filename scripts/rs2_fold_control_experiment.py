"""Generate an isolated RS2 variant with a local fold-control state machine."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hls" / "rs2" / "src" / "gdn_rs2_top.cpp"
DEFAULT_OUTPUT = (
    ROOT / "build" / "experiments" / "rs2_fold_control" / "gdn_rs2_top.cpp"
)
DEFAULT_MANIFEST = (
    ROOT / "build" / "experiments" / "rs2_fold_control" / "manifest.json"
)

HELPER = """void fold_log_if_full(
    int live_after_step,
    resident_primary_slot_t primary,
    resident_scale_slot_t primary_scales,
    resident_residual_slot_t residual,
    resident_scale_slot_t residual_scales,
    resident_key_log_t keys,
    resident_key_scale_log_t key_scales,
    resident_update_log_t updates,
    resident_update_scale_log_t update_scales,
    coefficient_heads_t gamma,
    lambda_t lambda,
    counters_t counters) {
#pragma HLS INLINE off
  if (live_after_step != LOG_CAPACITY) {
    return;
  }
  fold_log(
      primary,
      primary_scales,
      residual,
      residual_scales,
      keys,
      key_scales,
      updates,
      update_scales,
      gamma,
      lambda,
      counters);
}

"""

OLD_COMMIT = """  resident_live[sequence_id][layer_id] = old_live + 1;
  if (old_live + 1 == LOG_CAPACITY) {
    fold_log(
        primary,
        primary_scales,
        residual,
        residual_scales,
        keys,
        key_scales,
        updates,
        update_scales,
        gamma,
        lambda,
        command_counters);
    resident_live[sequence_id][layer_id] = 0;
  }
"""

NEW_COMMIT = """  const int live_after_step = old_live + 1;
  fold_log_if_full(
      live_after_step,
      primary,
      primary_scales,
      residual,
      residual_scales,
      keys,
      key_scales,
      updates,
      update_scales,
      gamma,
      lambda,
      command_counters);
  resident_live[sequence_id][layer_id] =
      live_after_step == LOG_CAPACITY ? 0 : live_after_step;
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def generate(output: Path, manifest_path: Path) -> dict[str, object]:
    source = SOURCE.read_text(encoding="utf-8")
    insertion_marker = "void reset_slot(\n"
    if source.count(insertion_marker) != 1:
        raise RuntimeError("expected one reset_slot insertion marker")
    if source.count(OLD_COMMIT) != 1:
        raise RuntimeError("expected one original fold commit block")

    transformed = source.replace(insertion_marker, HELPER + insertion_marker)
    transformed = transformed.replace(OLD_COMMIT, NEW_COMMIT)
    if transformed == source:
        raise RuntimeError("fold-control transform made no change")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(transformed, encoding="utf-8")
    manifest = {
        "schema": 1,
        "status": "PASS",
        "experiment": "RS2 localized fold control",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": _sha256(SOURCE),
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": _sha256(output),
        "transform": {
            "helper_insertions": transformed.count("void fold_log_if_full("),
            "commit_replacements": transformed.count(
                "const int live_after_step = old_live + 1;"
            ),
        },
        "behavioral_contract": (
            "same fold cadence and command-visible state; only fold-control "
            "hierarchy is changed"
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
    manifest = (
        args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    )
    try:
        result = generate(output, manifest)
    except RuntimeError as exc:
        print(exc)
        return 1
    print(json.dumps({"status": result["status"], "output": result["output"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

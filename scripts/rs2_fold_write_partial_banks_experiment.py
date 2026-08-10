"""Generate isolated RS2 fold-write plus six-way layer-bank RTL source."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.rs2_fold_write_experiment import SOURCE, generate as generate_fold_write
from scripts.rs2_partial_layer_banks_experiment import PARTITION_FACTOR, STATE_VARIABLES


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "build"
    / "experiments"
    / "rs2_fold_write_partial_banks"
    / "gdn_rs2_top.cpp"
)
DEFAULT_MANIFEST = (
    ROOT
    / "build"
    / "experiments"
    / "rs2_fold_write_partial_banks"
    / "manifest.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def generate(output: Path, manifest_path: Path) -> dict[str, object]:
    intermediate_manifest = output.parent / ".fold_write_manifest.json"
    fold_result = generate_fold_write(output, intermediate_manifest)
    fold_write_sha256 = _sha256(output)
    transformed = output.read_text(encoding="utf-8")
    insertions: list[str] = []
    for variable in STATE_VARIABLES:
        binding = (
            f"#pragma HLS BIND_STORAGE variable={variable} "
            "type=ram_t2p impl=uram"
        )
        partition = (
            f"#pragma HLS ARRAY_PARTITION variable={variable} "
            f"cyclic factor={PARTITION_FACTOR} dim=2"
        )
        if transformed.count(binding) != 1:
            raise RuntimeError(f"expected one URAM binding for {variable}")
        if partition in transformed:
            raise RuntimeError(f"cyclic layer partition already present for {variable}")
        transformed = transformed.replace(binding, binding + "\n" + partition)
        insertions.append(partition)

    output.write_text(transformed, encoding="utf-8", newline="\n")
    intermediate_manifest.unlink(missing_ok=True)
    manifest = {
        "schema": 1,
        "status": "PASS",
        "experiment": "RS2 localized fold writes with six-way cyclic layer banks",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": _sha256(SOURCE),
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": _sha256(output),
        "fold_write_intermediate_sha256": fold_write_sha256,
        "fold_write_transform": fold_result["transform"],
        "partition_factor": PARTITION_FACTOR,
        "layers_per_bank": 36 // PARTITION_FACTOR,
        "partition_insertions": insertions,
        "behavioral_contract": (
            "same arithmetic, state layout, capacity, commands, and fold cadence; "
            "only fold-write hierarchy and primary/residual physical layer banking change"
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

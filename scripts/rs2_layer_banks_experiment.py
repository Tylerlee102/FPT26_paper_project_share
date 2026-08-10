"""Generate an isolated RS2 variant with layer-local state URAM banks."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hls" / "rs2" / "src" / "gdn_rs2_top.cpp"
DEFAULT_OUTPUT = (
    ROOT / "build" / "experiments" / "rs2_layer_banks" / "gdn_rs2_top.cpp"
)
DEFAULT_MANIFEST = (
    ROOT / "build" / "experiments" / "rs2_layer_banks" / "manifest.json"
)
STATE_VARIABLES = ("resident_primary", "resident_residual")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def generate(output: Path, manifest_path: Path) -> dict[str, object]:
    source = SOURCE.read_text(encoding="utf-8")
    transformed = source
    insertions: list[str] = []
    for variable in STATE_VARIABLES:
        binding = (
            f"#pragma HLS BIND_STORAGE variable={variable} "
            "type=ram_t2p impl=uram"
        )
        partition = (
            f"#pragma HLS ARRAY_PARTITION variable={variable} complete dim=2"
        )
        if transformed.count(binding) != 1:
            raise RuntimeError(f"expected one URAM binding for {variable}")
        if partition in transformed:
            raise RuntimeError(f"layer partition already present for {variable}")
        transformed = transformed.replace(binding, binding + "\n" + partition)
        insertions.append(partition)

    if transformed == source:
        raise RuntimeError("layer-bank transform made no change")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(transformed, encoding="utf-8", newline="\n")
    manifest = {
        "schema": 1,
        "status": "PASS",
        "experiment": "RS2 layer-local primary/residual URAM banks",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": _sha256(SOURCE),
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": _sha256(output),
        "insertions": insertions,
        "behavioral_contract": (
            "same arithmetic, state layout, capacity, command behavior, and fold cadence; "
            "only the physical layer dimension of primary/residual state is partitioned"
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

"""Generate an isolated RS2 source variant with registered URAM access."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hls" / "rs2" / "src" / "gdn_rs2_top.cpp"
DEFAULT_OUTPUT = (
    ROOT / "build" / "experiments" / "rs2_uram_latency2" / "gdn_rs2_top.cpp"
)
DEFAULT_MANIFEST = (
    ROOT / "build" / "experiments" / "rs2_uram_latency2" / "manifest.json"
)
URAM_VARIABLES = (
    "resident_primary",
    "resident_residual",
    "resident_keys",
    "resident_updates",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def generate(output: Path, manifest_path: Path) -> dict[str, object]:
    source = SOURCE.read_text(encoding="utf-8")
    transformed = source
    replacements: list[dict[str, str]] = []
    for variable in URAM_VARIABLES:
        old = (
            f"#pragma HLS BIND_STORAGE variable={variable} "
            "type=ram_t2p impl=uram"
        )
        new = old + " latency=2"
        if transformed.count(old) != 1:
            raise RuntimeError(
                f"expected one unregistered URAM binding for {variable}"
            )
        transformed = transformed.replace(old, new)
        replacements.append({"from": old, "to": new})
    if transformed == source:
        raise RuntimeError("URAM-latency transform made no change")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(transformed, encoding="utf-8")
    manifest = {
        "schema": 1,
        "status": "PASS",
        "experiment": "RS2 two-cycle URAM binding",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": _sha256(SOURCE),
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": _sha256(output),
        "replacements": replacements,
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
        print(str(exc))
        return 1
    print(json.dumps({"status": result["status"], "output": result["output"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

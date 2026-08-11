"""Generate fold-write RTL with bounded registered-address fanout."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "gdn_rs2_fold_write_hls/u55c_250mhz/syn/verilog"
TARGET_NAME = "gdn_rs2_top_p_anonymous_namespace_commit_fold_block.v"
DEFAULT_OUTPUT = ROOT / "build/experiments/rs2_fold_write_address_fanout16/rtl"
DEFAULT_MANIFEST = DEFAULT_OUTPUT.parent / "manifest.json"
TRANSFORMS = {
    "reg   [19:0] lshr_ln_reg_364;": (
        '(* max_fanout = 16 *) reg   [19:0] lshr_ln_reg_364;'
    ),
    "reg   [19:0] lshr_ln9_reg_369;": (
        '(* max_fanout = 16 *) reg   [19:0] lshr_ln9_reg_369;'
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def generate(output: Path, manifest_path: Path) -> dict[str, object]:
    source = SOURCE_ROOT / TARGET_NAME
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SOURCE_ROOT, output)
    target = output / TARGET_NAME
    text = target.read_text(encoding="utf-8")
    for old, new in TRANSFORMS.items():
        if text.count(old) != 1:
            raise RuntimeError(f"expected one address-register declaration: {old}")
        text = text.replace(old, new)
    target.write_text(text, encoding="utf-8", newline="\n")

    copied_files = sorted(path.relative_to(output).as_posix() for path in output.iterdir())
    manifest = {
        "schema": 1,
        "status": "PASS",
        "experiment": "RS2 fold-write registered-address max-fanout 16",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "synthesis attributes only; HLS C++ and behavioral RTL unchanged",
        "source_root": SOURCE_ROOT.relative_to(ROOT).as_posix(),
        "source_file_count": len(copied_files),
        "source_target_sha256": _sha256(source),
        "output_root": output.relative_to(ROOT).as_posix(),
        "output_target_sha256": _sha256(target),
        "transform": {
            "attribute": "max_fanout",
            "value": 16,
            "registers": sorted(new.split()[-1].rstrip(";") for new in TRANSFORMS.values()),
            "declaration_replacements": len(TRANSFORMS),
        },
        "behavioral_contract": (
            "same fold-write generated RTL behavior; only synthesis fanout hints on "
            "the registered primary and residual state addresses"
        ),
        "hls_cpp_modified": False,
        "generated_rtl_modified": True,
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
    except (FileNotFoundError, RuntimeError) as exc:
        print(exc)
        return 1
    print(json.dumps({"status": result["status"], "output": result["output_root"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

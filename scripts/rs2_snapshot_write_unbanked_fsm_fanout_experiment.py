"""Generate an RS2 RTL experiment with bounded top-FSM fanout."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (
    ROOT / "gdn_rs2_snapshot_write_unbanked_hls/u55c_250mhz/syn/verilog"
)
TARGET_NAME = "gdn_rs2_top_gdn_rs2_top_impl.v"
DEFAULT_OUTPUT = (
    ROOT / "build/experiments/rs2_snapshot_write_unbanked_fsm_fanout16/rtl"
)
DEFAULT_MANIFEST = DEFAULT_OUTPUT.parent / "manifest.json"
OLD_DECLARATION = '(* fsm_encoding = "none" *) reg   [326:0] ap_CS_fsm;'
NEW_DECLARATION = (
    '(* fsm_encoding = "none", max_fanout = 16 *) reg   [326:0] ap_CS_fsm;'
)


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
    if text.count(OLD_DECLARATION) != 1:
        raise RuntimeError("expected one unencoded top-FSM declaration")
    target.write_text(
        text.replace(OLD_DECLARATION, NEW_DECLARATION),
        encoding="utf-8",
        newline="\n",
    )
    copied_files = sorted(path.relative_to(output).as_posix() for path in output.iterdir())
    manifest = {
        "schema": 1,
        "status": "PASS",
        "experiment": "RS2 unbanked snapshot-write top-FSM max-fanout 16",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "synthesis attribute only; RTL logic and selected HLS source unchanged",
        "source_root": SOURCE_ROOT.relative_to(ROOT).as_posix(),
        "source_file_count": len(copied_files),
        "source_impl_sha256": _sha256(source),
        "output_root": output.relative_to(ROOT).as_posix(),
        "output_impl_sha256": _sha256(target),
        "transform": {
            "attribute": "max_fanout",
            "value": 16,
            "declaration_replacements": 1,
        },
        "behavioral_contract": (
            "Verilog behavior is unchanged; max_fanout is a synthesis-only replication hint"
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

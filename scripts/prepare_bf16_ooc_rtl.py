"""Generate a BF16 OOC top whose kernel clock is buffered before RTL synthesis."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT / "gdn_bf16_hls" / "u55c_250mhz" / "syn" / "verilog" / "gdn_bf16_top.v"
)
DEFAULT_OUTPUT = ROOT / "build" / "vivado" / "bf16_ooc_rtl" / "gdn_bf16_top.v"
INPUT_DECLARATION = "input   ap_clk;\n"
INSERTION_MARKER = "\ninitial begin\n"
CLOCK_BUFFER = """
wire ooc_ap_clk_global;
BUFGCE ooc_ap_clk_bufg (
    .I(ap_clk),
    .CE(1'b1),
    .O(ooc_ap_clk_global)
);
"""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def transform_top(source: str) -> str:
    if source.count(INPUT_DECLARATION) != 1:
        raise ValueError("expected one top-level ap_clk input declaration")
    if source.count(INSERTION_MARKER) != 1:
        raise ValueError("expected one top-level initial block marker")
    if "module gdn_bf16_top (" not in source:
        raise ValueError("expected gdn_bf16_top module")

    prefix, body = source.split(INPUT_DECLARATION, maxsplit=1)
    body = re.sub(r"(?<!\.)\bap_clk\b", "ooc_ap_clk_global", body)
    body = body.replace(INSERTION_MARKER, f"\n{CLOCK_BUFFER}{INSERTION_MARKER}", 1)
    transformed = prefix + INPUT_DECLARATION + body

    if transformed.count("BUFGCE ooc_ap_clk_bufg") != 1:
        raise ValueError("clock buffer insertion failed")
    if ".ap_clk(ooc_ap_clk_global)" not in transformed:
        raise ValueError("internal kernel clock connections were not rewritten")
    return transformed


def generate(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT) -> dict[str, object]:
    source_text = source.read_text(encoding="utf-8")
    transformed = transform_top(source_text)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(transformed, encoding="utf-8", newline="\n")

    manifest = {
        "status": "PASS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transformation": "insert_top_level_bufgce_and_rewire_internal_ap_clk",
        "source": _display_path(source),
        "source_sha256": _sha256_bytes(source.read_bytes()),
        "output": _display_path(output),
        "output_sha256": _sha256_bytes(output.read_bytes()),
    }
    manifest_path = output.with_name("manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.output if args.output.is_absolute() else ROOT / args.output
    generate(source, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "csynth" / "native_mac_evidence.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _contains_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def write_report(path: Path) -> None:
    mac_source = ROOT / "hls" / "src" / "mac_e2m1.cpp"
    mac_testbench = ROOT / "hls" / "tb" / "tb_mac_e2m1.cpp"
    source_text = _read(mac_source)
    tb_text = _read(mac_testbench)

    evidence = [
        ("Product lookup table present", "yes" if "product_mag_q3[8][8]" in source_text else "no"),
        ("Lookup table fully partitioned", "yes" if "ARRAY_PARTITION variable=product_mag_q3 complete" in source_text else "no"),
        ("Floating-point keywords in MAC source", "yes" if any(_contains_word(source_text, item) for item in ("float", "double")) else "no"),
        ("DSP pragma in MAC source", "yes" if re.search(r"\bDSP\b", source_text, flags=re.IGNORECASE) else "no"),
        ("Exhaustive 16x16 testbench", "yes" if "for (unsigned a = 0; a < 16" in tb_text and "for (unsigned b = 0; b < 16" in tb_text else "no"),
        ("Pseudo-random regression cases", "100000" if "100000" in tb_text else "unknown"),
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Native E2M1 MAC Evidence",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Source: `{mac_source.relative_to(ROOT).as_posix()}`",
        f"Testbench: `{mac_testbench.relative_to(ROOT).as_posix()}`",
        "",
        "This report is source-level evidence for the native LUT-style E2M1 multiply primitive. Full design resource percentages are reported separately from HLS/Vivado synthesis reports because the top-level kernel also contains non-MAC fixed-point arithmetic and memory logic.",
        "",
        "| Check | Result |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {result} |" for name, result in evidence)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate source-level native E2M1 MAC evidence.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    write_report(args.report)
    print(args.report.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOG = (
    ROOT
    / "gdn_mxfp4_hls"
    / "u55c_250mhz"
    / "csim"
    / "report"
    / "gdn_top_csim.log"
)
TRACE = ROOT / "data" / "vectors" / "corrected_gdn_command_trace.bin"
TRACE_MANIFEST = (
    ROOT / "reports" / "golden" / "corrected_hls_command_trace_manifest.json"
)
OUT_DIR = ROOT / "reports" / "csim" / "corrected"
OUT_PATH = OUT_DIR / "results.md"
RAW_LOG = OUT_DIR / "gdn_top_csim.log"
RUN_MANIFEST = OUT_DIR / "csim_manifest.json"
SOURCE_GLOBS = (
    "hls/include/*.hpp",
    "hls/src/*.cpp",
    "hls/tb/tb_gdn_top.cpp",
    "hls/tcl/run_csim.tcl",
    "scripts/generate_hls_command_trace.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _parse_csim_log(text: str) -> tuple[int, int, bool]:
    match = re.search(
        r"tb_gdn_top PASS hand_commands=(\d+) oracle_steps=(\d+)", text
    )
    if match is None:
        raise ValueError("corrected C-sim PASS marker is absent")
    done = "CSim done with 0 errors" in text
    return int(match.group(1)), int(match.group(2)), done


def _source_freshness() -> tuple[bool, str]:
    sources: list[Path] = []
    for pattern in SOURCE_GLOBS:
        sources.extend(ROOT.glob(pattern))
    sources.extend([TRACE, TRACE_MANIFEST])
    latest = max(sources, key=lambda path: path.stat().st_mtime)
    stale = latest.stat().st_mtime > SOURCE_LOG.stat().st_mtime + 1.0
    detail = (
        f"latest input `{latest.relative_to(ROOT).as_posix()}` modified "
        f"{datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc).isoformat()}; "
        f"log modified "
        f"{datetime.fromtimestamp(SOURCE_LOG.stat().st_mtime, timezone.utc).isoformat()}"
    )
    return stale, detail


def main() -> int:
    if not SOURCE_LOG.exists():
        print(f"Missing corrected C-sim log: {SOURCE_LOG}")
        return 2
    text = SOURCE_LOG.read_text(encoding="utf-8", errors="replace")
    hand_commands, oracle_steps, done = _parse_csim_log(text)
    stale, freshness = _source_freshness()
    if not done:
        raise RuntimeError("C-sim log did not report zero errors")
    if stale:
        raise RuntimeError(f"C-sim evidence is stale: {freshness}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_LOG, RAW_LOG)
    trace_manifest = json.loads(TRACE_MANIFEST.read_text(encoding="utf-8"))
    generated = datetime.now(timezone.utc).isoformat()
    source_hashes: dict[str, str] = {}
    for pattern in SOURCE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            source_hashes[path.relative_to(ROOT).as_posix()] = _sha256(path)
    run_manifest = {
        "status": "PASS",
        "generated_at": generated,
        "tool": "Vitis HLS 2025.2 build 6295257",
        "target": "xcu55c-fsvh2892-2L-e",
        "clock_ns": 4.0,
        "hand_commands": hand_commands,
        "oracle_steps": oracle_steps,
        "trace_sha256": _sha256(TRACE),
        "trace_manifest_sha256": _sha256(TRACE_MANIFEST),
        "raw_log_sha256": _sha256(RAW_LOG),
        "source_sha256": source_hashes,
        "freshness": freshness,
    }
    RUN_MANIFEST.write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    OUT_PATH.write_text(
        "\n".join(
            [
                "# Corrected HLS C-Simulation Results",
                "",
                f"Generated: `{generated}`",
                "",
                "- Status: `PASS`",
                f"- Target: `{run_manifest['target']}` at 4.0 ns",
                f"- Hand-derived command checks: `{hand_commands}`",
                f"- Full-dimension encoded-oracle steps: `{oracle_steps}`",
                f"- Trace SHA256: `{run_manifest['trace_sha256']}`",
                f"- Raw C-sim log SHA256: `{run_manifest['raw_log_sha256']}`",
                f"- Freshness: {freshness}",
                "",
                "The testbench compares status, generation, all eight per-command and",
                "cumulative counters, every output mantissa/exponent tuple, and the",
                "complete final recurrent-state element/scale readback. It does not",
                "establish RTL or board parity.",
                "",
                f"Trace input-stream SHA256: `{trace_manifest['input_stream_sha256']}`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

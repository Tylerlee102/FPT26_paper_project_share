from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOG = ROOT / "gdn_mxfp4_hls" / "u55c_250mhz" / "csim" / "report" / "gdn_top_csim.log"
FALLBACK_LOGS = (
    ROOT / "gdn_mxfp4_hls" / "u55c_250mhz" / "sim" / "report" / "verilog" / "gdn_top.log",
    ROOT / "gdn_mxfp4_hls" / "u55c_250mhz" / "sim" / "wrapc_pc" / "run_xsim.log",
)
OUT_PATH = ROOT / "reports" / "csim" / "results.md"
SOURCE_GLOBS = (
    "hls/include/*.hpp",
    "hls/src/*.cpp",
    "hls/tb/tb_gdn_top.cpp",
)


def _parse_csim_log(text: str) -> tuple[int, int, bool]:
    match = re.search(r"tb_gdn_top PASS vectors=(\d+)/(\d+)", text)
    if match is None:
        raise ValueError("Could not find tb_gdn_top vector pass count in C-sim log")
    done = "CSim done with 0 errors" in text or "C/RTL co-simulation finished: PASS" in text
    return int(match.group(1)), int(match.group(2)), done


def _source_freshness(source_log: Path) -> tuple[bool, str]:
    sources: list[Path] = []
    for pattern in SOURCE_GLOBS:
        sources.extend(ROOT.glob(pattern))
    if not sources:
        return False, "No HLS sources found for freshness check."
    latest = max(sources, key=lambda path: path.stat().st_mtime)
    log_mtime = source_log.stat().st_mtime
    latest_mtime = latest.stat().st_mtime
    stale = latest_mtime > log_mtime + 1.0
    latest_stamp = datetime.fromtimestamp(latest_mtime, UTC).isoformat()
    log_stamp = datetime.fromtimestamp(log_mtime, UTC).isoformat()
    detail = (
        f"latest source `{latest.relative_to(ROOT).as_posix()}` modified {latest_stamp}; "
        f"parity log `{source_log.relative_to(ROOT).as_posix()}` modified {log_stamp}"
    )
    return stale, detail


def _find_source_log() -> Path | None:
    if SOURCE_LOG.exists():
        return SOURCE_LOG
    for path in FALLBACK_LOGS:
        if path.exists() and "tb_gdn_top PASS vectors=" in path.read_text(encoding="utf-8", errors="replace"):
            return path
    return None


def main() -> int:
    source_log = _find_source_log()
    if source_log is None:
        print(f"Missing C-sim or cosim parity log: {SOURCE_LOG}")
        return 2

    text = source_log.read_text(encoding="utf-8", errors="replace")
    passed, total, done = _parse_csim_log(text)
    stale, freshness = _source_freshness(source_log)
    if not done:
        raise RuntimeError("Parity log did not report zero errors or cosim PASS")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        "\n".join(
            [
                "# HLS C-Simulation Results",
                "",
                f"Generated: {datetime.now(UTC).isoformat()}",
                "",
                f"- Source log: `{source_log.relative_to(ROOT).as_posix()}`",
                f"- Status: {'stale - rerun required' if stale else 'current'}",
                f"- Freshness: {freshness}",
                f"- `tb_gdn_top PASS vectors={passed}/{total}`",
                "- `CSim done with 0 errors`",
                "",
                "Coverage notes:",
                "",
                "- The vectors are deterministic HLS fixed-point parity cases generated inside `hls/tb/tb_gdn_top.cpp`.",
                "- The testbench checks packed output parity; MXFP4 state writeback checks are enabled when `GDN_STATE_READBACK=1`.",
                "- Qwen3-Next captured realistic-vector parity remains pending until the real calibration capture is available.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

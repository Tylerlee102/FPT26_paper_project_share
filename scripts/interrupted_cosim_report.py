"""Report bounded RTL co-simulation attempts stopped for host-memory safety."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_GLOBS = (
    "hls/include/*.hpp",
    "hls/src/*.cpp",
    "hls/tb/*.cpp",
    "hls/tcl/run_cosim.tcl",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _source_hashes() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): _sha256(path)
        for pattern in SOURCE_GLOBS
        for path in sorted(ROOT.glob(pattern))
    }


def _parse_progress(log: str) -> tuple[int, int, int]:
    matches = re.findall(
        r'RTL Simulation\s*:\s*(\d+)\s*/\s*(\d+).*?@\s*"(\d+)"',
        log,
    )
    if not matches:
        raise ValueError("XSIM log has no inter-transaction progress")
    completed, total, simulation_time = matches[-1]
    return int(completed), int(total), int(simulation_time)


def _parse_xsim_start(journal: str) -> str:
    match = re.search(r"^# Start of session at:\s*(.+)$", journal, re.MULTILINE)
    if match is None:
        raise ValueError("XSIM journal has no session start")
    return match.group(1).strip()


def _normalize_relpath(value: str) -> str:
    return value.replace("\\", "/")


def _verify_archive(smoke: Path) -> dict[str, dict[str, object]]:
    archive_path = smoke / "archived_files.json"
    entries = json.loads(archive_path.read_text(encoding="utf-8-sig"))
    verified: dict[str, dict[str, object]] = {}
    for entry in entries:
        relpath = _normalize_relpath(entry["path"])
        path = ROOT / relpath
        actual_hash = _sha256(path)
        actual_bytes = path.stat().st_size
        if actual_hash != entry["sha256"] or actual_bytes != entry["bytes"]:
            raise ValueError(f"archive hash or size mismatch: {relpath}")
        verified[relpath] = {"sha256": actual_hash, "bytes": actual_bytes}
    return verified


def generate_report(smoke: Path) -> dict[str, object]:
    raw = smoke / "raw"
    observation_path = smoke / "operator_observation.json"
    trace_path = smoke / "trace.bin"
    trace_manifest_path = smoke / "trace_manifest.json"
    xsim_path = raw / "xsim.log"
    xelab_path = raw / "xelab.log"
    journal_path = raw / "xsim.jou"
    required = (
        observation_path,
        trace_path,
        trace_manifest_path,
        xsim_path,
        xelab_path,
        journal_path,
        smoke / "archived_files.json",
    )
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)

    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    if observation.get("status") != "FAIL":
        raise ValueError("interrupted attempts must be recorded as FAIL")
    if observation.get("termination", {}).get("kind") != "operator_memory_safety":
        raise ValueError("termination kind must be operator_memory_safety")

    trace_manifest = json.loads(trace_manifest_path.read_text(encoding="utf-8"))
    xsim_log = xsim_path.read_text(encoding="utf-8", errors="replace")
    xelab_log = xelab_path.read_text(encoding="utf-8", errors="replace")
    journal = journal_path.read_text(encoding="utf-8", errors="replace")
    completed, total, simulation_time = _parse_progress(xsim_log)
    first_valid_step_index = 4
    source_hashes = _source_hashes()
    archived = _verify_archive(smoke)

    run_script = raw / "run_xsim.bat"
    run_command = (
        run_script.read_text(encoding="utf-8", errors="replace")
        if run_script.exists()
        else ""
    )
    manifest: dict[str, object] = {
        "schema": 1,
        "status": "FAIL",
        "scope": observation["scope"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_revision": "bdd90bae3fdbeb6cb11e3a6538dc9bef72e26bfe",
        "source_sha256": source_hashes,
        "trace": {
            "path": trace_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(trace_path),
            "tokens": trace_manifest["tokens"],
            "status": trace_manifest["status"],
        },
        "simulator": {
            "tool": "XSIM",
            "version": "2025.2",
            "rtl_language": observation["rtl_language"],
            "session_start": _parse_xsim_start(journal),
            "multithreading_disabled": "Turned off multi-threading." in xelab_log,
            "ignore_coverage": "--ignore_coverage" in run_command,
            "ignore_assertions": "--ignore_assertions" in run_command,
        },
        "rtl_simulation": {
            "status": "FAIL",
            "failure": "operator termination for host-memory safety",
            "completed_transactions": completed,
            "total_transactions": total,
            "last_simulation_time": simulation_time,
            "first_valid_step_index": first_valid_step_index,
            "first_valid_step_completed": completed >= first_valid_step_index,
            "termination": observation["termination"],
        },
        "archived_artifacts": archived,
        "required_64_token_rtl_parity": "NOT_RUN",
        "required_64_token_transaction_count": 141,
        "decision": {
            "status": "FAIL",
            "text": (
                "This host/configuration cannot complete one valid recurrent STEP "
                "without unbounded simulator-memory growth; it is not valid RTL "
                "parity evidence."
            ),
        },
        "limitations": [
            "The simulator was terminated by the operator and did not emit a normal result.",
            "No valid recurrent STEP reached the RTL post-check.",
            "Memory values are explicit operator observations, not XSIM peak statistics.",
            "The required 64-token RTL parity run remains NOT_RUN.",
            "The selected residual-stack/write-log candidate is not implemented in this RTL.",
        ],
    }

    json_path = smoke / "cosim_interrupted_summary.json"
    md_path = smoke / "cosim_interrupted_summary.md"
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rtl = manifest["rtl_simulation"]
    termination = rtl["termination"]
    md_path.write_text(
        "\n".join(
            [
                "# Interrupted RTL Co-simulation Smoke",
                "",
                f"Generated: `{manifest['timestamp']}`",
                "",
                "- Status: `FAIL`",
                f"- Scope: {manifest['scope']}",
                f"- RTL language: `{manifest['simulator']['rtl_language']}`",
                f"- Progress: `{rtl['completed_transactions']} / {rtl['total_transactions']}` transactions",
                "- First valid recurrent STEP completed: `no`",
                f"- Observed private memory at termination: `{termination['xsimk_private_memory_gib']}` GiB",
                f"- Minimum observed free physical memory: `{termination['minimum_observed_free_physical_memory_gib']}` GiB",
                "- Required 64-token RTL parity: `NOT_RUN`",
                "",
                termination["reason"],
                "",
                "This is preserved failed-attempt evidence. It does not establish RTL",
                "correctness, selected-candidate physical feasibility, timing closure,",
                "or FPGA energy.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", type=Path, required=True)
    args = parser.parse_args(argv)
    smoke = args.smoke if args.smoke.is_absolute() else ROOT / args.smoke
    manifest = generate_report(smoke)
    print(json.dumps({"status": manifest["status"], "scope": manifest["scope"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

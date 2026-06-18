from __future__ import annotations

import argparse
import json
import subprocess
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "paper" / "pack"
REPORT = ROOT / "reports" / "phase7_validation.md"
FALLBACK_SHA = "0" * 40


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        sha = result.stdout.strip()
        return sha if len(sha) == 40 else FALLBACK_SHA
    except Exception:
        return FALLBACK_SHA


def _default_pack() -> Path:
    return PACK_DIR / f"submission_{_git_sha()}.zip"


def _has_any(names: set[str], prefix: str, suffix: str = "") -> bool:
    return any(name.startswith(prefix) and name.endswith(suffix) for name in names)


def _read_json_from_zip(archive: zipfile.ZipFile, name: str) -> dict[str, object]:
    with archive.open(name) as handle:
        return json.loads(handle.read().decode("utf-8"))


def validate_pack(pack: Path) -> tuple[list[Check], list[str]]:
    checks: list[Check] = []
    details: list[str] = []
    if not pack.exists():
        return [Check("pack exists", False, f"{pack} is missing")], details

    with zipfile.ZipFile(pack) as archive:
        names_list = archive.namelist()
        names = set(names_list)
        counts = Counter(names_list)

        duplicates = sorted(name for name, count in counts.items() if count > 1)
        checks.append(Check("no duplicate archive entries", not duplicates, ", ".join(duplicates) or "none"))

        required_exact = {
            "AGENTS.md",
            "paper/numbers.json",
            "paper/provenance.json",
            "paper/snippets/result_macros.tex",
            "paper/snippets/headline_speedup.tex",
            "paper/tables/main_results.tex",
            "paper/tables/recurrent_state_stress.tex",
            "paper/tables/state_storage_traffic.tex",
            "paper/results_section/results_section.tex",
            "paper/example_report.md",
            "reports/phase7_status.md",
            "reports/known_issues.md",
            "reports/decision_gate.md",
            "reports/golden/qwen_capture_status.md",
            "reports/benchmark/sweep.csv",
            "reports/benchmark/state_drift.csv",
            "reports/benchmark/stress_accuracy.csv",
            "reports/benchmark/state_boundary.csv",
            "reports/benchmark/storage_overhead.csv",
            "reports/benchmark/offchip_state_traffic.csv",
            "reports/cosim/latency.csv",
            "reports/cosim/gdn_top_cosim.rpt",
            "reports/csynth/util.md",
            "reports/vivado/impl_timing.rpt",
            "reports/vivado/impl_util.rpt",
            "reports/vivado/impl_power.rpt",
            "git_sha.txt",
            "git_log.txt",
            "git_status.txt",
            "git_diff_stat.txt",
        }
        missing = sorted(required_exact - names)
        checks.append(Check("required exact files", not missing, ", ".join(missing) or "all present"))

        class_checks = [
            ("generated PDF figures", _has_any(names, "paper/figures/", ".pdf")),
            ("IEEE PDF figures", _has_any(names, "paper/ieee_figures/", ".pdf")),
            ("generated LaTeX tables", _has_any(names, "paper/tables/", ".tex")),
            ("Vivado reports", _has_any(names, "reports/vivado/", ".rpt")),
            ("HLS csynth reports", _has_any(names, "reports/csynth/", ".rpt")),
            ("cosim reports", _has_any(names, "reports/cosim/", ".rpt")),
            ("cosim latency CSVs", _has_any(names, "reports/cosim/", ".csv")),
            ("calibration SHA manifests", _has_any(names, "data/calibration/", ".sha256")),
            ("sweep cosim CSVs", _has_any(names, "reports/benchmark/sweeps/", ".csv")),
            ("sweep Vivado reports", _has_any(names, "reports/benchmark/sweeps/", ".rpt")),
        ]
        for label, passed in class_checks:
            checks.append(Check(label, passed, "present" if passed else "missing"))

        try:
            numbers = _read_json_from_zip(archive, "paper/numbers.json")
            provenance = _read_json_from_zip(archive, "paper/provenance.json")
            checks.append(Check("numbers/provenance key match", set(numbers) == set(provenance), f"{len(numbers)} numbers, {len(provenance)} provenance records"))
            missing_sources = []
            for key, record_obj in numbers.items():
                record = record_obj if isinstance(record_obj, dict) else {}
                source = str(record.get("source", ""))
                if source != "external" and source and source not in names and not (ROOT / source).exists():
                    missing_sources.append(f"{key}->{source}")
            checks.append(Check("non-external number sources exist", not missing_sources, ", ".join(missing_sources[:10]) or "all present"))
            qwen_status = str(numbers.get("qwen_capture_status", {}).get("value", "unknown")) if isinstance(numbers.get("qwen_capture_status"), dict) else "unknown"
            caveat_ok = qwen_status == "available" or "reports/golden/qwen_capture_status.md" in names
            checks.append(Check("qwen caveat represented", caveat_ok, f"qwen_capture_status={qwen_status}"))
            details.append(f"Canonical numbers: {len(numbers)}")
            details.append(f"Qwen capture status: {qwen_status}")
        except Exception as exc:
            checks.append(Check("numbers/provenance parse", False, str(exc)))

    return checks, details


def write_report(pack: Path, checks: list[Check], details: list[str]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    passed = all(check.passed for check in checks)
    lines = [
        "# Phase 7 Pack Validation",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Pack: `{pack.relative_to(ROOT).as_posix() if pack.exists() else pack.as_posix()}`",
        f"Overall status: {'PASS' if passed else 'FAIL'}",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {'PASS' if check.passed else 'FAIL'} | {check.detail} |")
    if details:
        lines.extend(["", "## Details", ""])
        lines.extend(f"- {detail}" for detail in details)
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Phase 7 paper-pack archive.")
    parser.add_argument("--pack", type=Path, default=_default_pack())
    args = parser.parse_args(argv)
    pack = args.pack if args.pack.is_absolute() else ROOT / args.pack
    checks, details = validate_pack(pack)
    write_report(pack, checks, details)
    print(REPORT.relative_to(ROOT).as_posix())
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "paper" / "pack"
FALLBACK_SHA = "0" * 40


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git_sha() -> tuple[str, str]:
    try:
        sha = _git(["rev-parse", "HEAD"]).strip()
        if len(sha) == 40:
            return sha, ""
    except Exception as exc:
        return FALLBACK_SHA, f"No git commit was available: {exc}\n"
    return FALLBACK_SHA, "Git returned an invalid HEAD SHA.\n"


def _git_log(note: str) -> str:
    if note:
        return note
    try:
        return _git(["log", "--oneline", "--decorate", "--max-count=50"])
    except Exception as exc:
        return f"Could not read git log: {exc}\n"


def _git_status() -> str:
    try:
        status = _git(["status", "--short"])
        return status if status else "clean\n"
    except Exception as exc:
        return f"Could not read git status: {exc}\n"


def _git_diff_stat() -> str:
    try:
        diff = _git(["diff", "--stat"])
        return diff if diff else "no unstaged diff\n"
    except Exception as exc:
        return f"Could not read git diff stat: {exc}\n"


def _add_if_exists(archive: zipfile.ZipFile, path: Path) -> None:
    if path.exists() and path.is_file():
        archive.write(path, _rel(path))


def _add_glob(archive: zipfile.ZipFile, pattern: str) -> None:
    for path in sorted(ROOT.glob(pattern)):
        if path.is_file():
            archive.write(path, _rel(path))


def _phase7_status_lines(sha: str, output: Path) -> list[str]:
    lines = [
        "# Phase 7 Paper Pack Status",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Git SHA: `{sha}`",
        f"Pack path: `{output.relative_to(ROOT).as_posix()}`",
        "",
        "## Phase 6 Evidence",
        "",
    ]

    sweep_csv = ROOT / "reports" / "benchmark" / "sweep.csv"
    if sweep_csv.exists():
        with sweep_csv.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        cosim_rows = sum(1 for row in rows if row.get("latency_source_kind") == "cosim")
        post_impl_rows = sum(1 for row in rows if row.get("impl_status") == "post_impl")
        default_tokens = next((row.get("tokens", "0") for row in rows if row.get("config") == "ours_mxfp4_b32_pk16_pv8"), "0")
        lines.extend(
            [
                f"- Sweep rows: {len(rows)}",
                f"- RTL cosim latency rows: {cosim_rows}/{len(rows)}",
                f"- Vivado post-implementation rows: {post_impl_rows}/{len(rows)}",
                f"- Default cosim tokens: {default_tokens}",
            ]
        )
    else:
        lines.append("- Sweep CSV missing.")

    numbers_path = ROOT / "paper" / "numbers.json"
    if numbers_path.exists():
        numbers = json.loads(numbers_path.read_text(encoding="utf-8"))
        qwen_status = numbers.get("qwen_capture_status", {}).get("value", "unknown")
        latency = numbers.get("ours_mxfp4_b32_latency_us", {}).get("value", "unknown")
        speedup = numbers.get("headline_speedup_vs_h100", {}).get("value", "unknown")
        lines.extend(
            [
                "",
                "## Paper-Readiness Caveats",
                "",
                f"- Qwen realistic capture status: `{qwen_status}`",
                f"- Default latency: `{latency}` us/token",
                f"- Headline speedup vs H100: `{speedup}`x",
            ]
        )
    lines.extend(
        [
            "- If Qwen status is not `available`, realistic PPL/accuracy must not be claimed in the manuscript.",
            "- If speedup/latency are below hard floor, the manuscript must present this as current evidence, not the aspirational headline.",
            "",
        ]
    )
    return lines


def build_pack() -> Path:
    sha, sha_note = _git_sha()
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    output = PACK_DIR / f"submission_{sha}.zip"
    phase7_status = ROOT / "reports" / "phase7_status.md"
    phase7_status.parent.mkdir(parents=True, exist_ok=True)
    phase7_status.write_text("\n".join(_phase7_status_lines(sha, output)), encoding="utf-8")

    required = [
        ROOT / "AGENTS.md",
        ROOT / "paper" / "numbers.json",
        ROOT / "paper" / "provenance.json",
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required paper-pack file(s): {', '.join(missing)}")

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in required:
            archive.write(path, _rel(path))
        _add_glob(archive, "reports/benchmark/*.csv")
        _add_glob(archive, "reports/benchmark/*.md")
        _add_glob(archive, "reports/benchmark/sweeps/**/*.md")
        _add_glob(archive, "reports/benchmark/sweeps/**/*.csv")
        _add_glob(archive, "reports/benchmark/sweeps/**/*.rpt")
        _add_if_exists(archive, ROOT / "reports" / "phase7_status.md")
        _add_if_exists(archive, ROOT / "reports" / "phase7_validation.md")
        _add_if_exists(archive, ROOT / "reports" / "ieee_assets.md")
        _add_if_exists(archive, ROOT / "reports" / "graph_previews.md")
        _add_if_exists(archive, ROOT / "reports" / "table_previews.md")
        _add_if_exists(archive, ROOT / "reports" / "known_issues.md")
        _add_if_exists(archive, ROOT / "reports" / "decision_gate.md")
        _add_glob(archive, "paper/snippets/*.tex")
        _add_glob(archive, "paper/tables/*.tex")
        _add_glob(archive, "paper/results_section/*.tex")
        _add_if_exists(archive, ROOT / "paper" / "example_report.md")
        _add_glob(archive, "paper/figures/*.pdf")
        _add_glob(archive, "paper/ieee_figures/*.pdf")
        _add_glob(archive, "paper/ieee_figures/*.png")
        _add_glob(archive, "paper/ieee_tables/*.tex")
        _add_glob(archive, "paper/ieee_tables/*.png")
        _add_glob(archive, "paper/graph_previews/*.png")
        _add_glob(archive, "paper/table_previews/*.png")
        _add_glob(archive, "reports/vivado/*.rpt")
        _add_glob(archive, "reports/vivado/*.md")
        _add_glob(archive, "reports/csynth/*.rpt")
        _add_glob(archive, "reports/csynth/*.md")
        _add_glob(archive, "reports/cosim/*.rpt")
        _add_glob(archive, "reports/cosim/*.csv")
        _add_glob(archive, "reports/cosim/*.md")
        _add_glob(archive, "reports/csim/*.md")
        _add_glob(archive, "reports/golden/*.md")
        _add_glob(archive, "data/calibration/*.sha256")
        archive.writestr("git_sha.txt", sha + "\n")
        archive.writestr("git_log.txt", _git_log(sha_note))
        archive.writestr("git_status.txt", _git_status())
        archive.writestr("git_diff_stat.txt", _git_diff_stat())
        archive.writestr("pack_manifest.txt", f"Generated: {datetime.now(UTC).isoformat()}\n")

    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the paper-pack reproducibility archive.")
    parser.parse_args(argv)
    output = build_pack()
    print(output.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from pathlib import Path

import pytest

from scripts.hls_flow import TCL_BY_STEP, _archive_completed_step


def _trace_logs(root: Path, marker: str) -> None:
    solution = root / "gdn_rs2_trace_hls/u55c_250mhz"
    report = solution / "csim/report"
    report.mkdir(parents=True)
    (report / "gdn_rs2_top_csim.log").write_text(marker, encoding="utf-8")
    (solution / "u55c_250mhz.log").write_text(
        "CSim done with 0 errors\n", encoding="utf-8"
    )


def test_rs2_trace_archive_rejects_non_64_token_run(tmp_path: Path) -> None:
    _trace_logs(
        tmp_path,
        "PASS: 8 encoded random-state tokens, exact outputs/counters, and final snapshot\n",
    )
    with pytest.raises(RuntimeError, match="64-token PASS marker"):
        _archive_completed_step("rs2-trace-csim", tmp_path)


def test_rs2_trace_archive_accepts_64_token_run(tmp_path: Path) -> None:
    marker = (
        "PASS: 64 encoded random-state tokens, exact outputs/counters, "
        "and final snapshot\n"
    )
    _trace_logs(tmp_path, marker)
    _archive_completed_step("rs2-trace-csim", tmp_path)
    archived = (
        tmp_path
        / "reports/csim/corrected/rs2_current/trace64/gdn_rs2_top_csim.log"
    )
    assert archived.read_text(encoding="utf-8") == marker


def _cosim_artifacts(root: Path, project: str, marker: str) -> None:
    solution = root / project / "u55c_250mhz"
    report = solution / "sim/report/verilog"
    report.mkdir(parents=True)
    (solution / "sim/report/gdn_rs2_top_cosim.rpt").write_text("PASS\n", encoding="utf-8")
    (report / "gdn_rs2_top.log").write_text(marker + "\n", encoding="utf-8")
    for name in ("lat.rpt", "result.transaction.rpt"):
        (report / name).write_text("PASS\n", encoding="utf-8")
    wrap = solution / "sim/wrapc_pc"
    wrap.mkdir(parents=True)
    (wrap / "run_xsim.log").write_text("PASS\n", encoding="utf-8")
    (solution / "u55c_250mhz.log").write_text(
        marker + "\nC/RTL co-simulation finished: PASS\n", encoding="utf-8"
    )


def test_rs2_control_cosim_archive_requires_and_copies_pass(tmp_path: Path) -> None:
    marker = "PASS: corrected RS2 generated-RTL control smoke, two exact commands"
    _cosim_artifacts(tmp_path, "gdn_rs2_hls", marker)
    _archive_completed_step("rs2-control-cosim", tmp_path)
    archived = tmp_path / "reports/cosim/corrected/rs2_current/control"
    assert (archived / "gdn_rs2_top_cosim.rpt").is_file()
    assert marker in (archived / "verilog/gdn_rs2_top.log").read_text(
        encoding="utf-8"
    )
    assert "C/RTL co-simulation finished: PASS" in (
        archived / "u55c_250mhz.log"
    ).read_text(encoding="utf-8")


def test_rs2_trace_cosim_archive_rejects_control_only_pass(tmp_path: Path) -> None:
    _cosim_artifacts(
        tmp_path,
        "gdn_rs2_trace_cosim_hls",
        "PASS: corrected RS2 generated-RTL control smoke, two exact commands",
    )
    with pytest.raises(RuntimeError, match="RTL PASS markers"):
        _archive_completed_step("rs2-trace-cosim", tmp_path)


def test_rs2_reset_trace_cosim_archive_requires_and_copies_pass(
    tmp_path: Path,
) -> None:
    marker = (
        "PASS: 64 encoded reset-state tokens, exact outputs/counters, "
        "and final snapshot"
    )
    _cosim_artifacts(tmp_path, "gdn_rs2_reset_trace_cosim_hls", marker)
    _archive_completed_step("rs2-reset-trace-cosim", tmp_path)
    archived = tmp_path / "reports/cosim/corrected/rs2_current/trace64_reset"
    assert (archived / "gdn_rs2_top_cosim.rpt").is_file()
    assert marker in (archived / "verilog/gdn_rs2_top.log").read_text(
        encoding="utf-8"
    )


def test_rs2_reset_trace_cosim_resume_is_optimized_and_registered() -> None:
    path = TCL_BY_STEP["rs2-reset-trace-cosim-resume"]
    assert path == Path("hls/rs2/tcl/run_reset_trace_cosim_resume.tcl")
    text = (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")
    assert "cosim_design -O" in text
    assert "RS2_RESET_TRACE_COSIM_METADATA_REUSED" in text
    assert "RS2_TRACE_PATH" in text

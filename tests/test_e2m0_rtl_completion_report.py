from __future__ import annotations

from pathlib import Path

import pytest

from scripts.e2m0_rtl_completion_report import generate_report


def test_superseded_e2m0_completion_report_rejects_overwritten_assets(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError, match="bounded direct generated-RTL LOAD evidence is not PASS"
    ):
        generate_report(tmp_path / "report")

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from scripts.decision_gate import build_decision_gate_report, write_decision_gate_report


class TestDecisionGate(unittest.TestCase):
    def test_report_marks_missing_hls_evidence_as_blocked(self) -> None:
        tmp = Path.cwd() / "build" / "test_decision_gate_missing"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            text = build_decision_gate_report(tmp, remaining_work_days="0")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        self.assertIn("Overall status: **BLOCKED**", text)
        self.assertIn("Human decision required", text)
        self.assertIn("Csim bit-exact vectors", text)
        self.assertIn("Remaining work", text)

    def test_write_decision_gate_report(self) -> None:
        tmp = Path.cwd() / "build" / "test_decision_gate"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            output = write_decision_gate_report(Path.cwd(), tmp / "decision_gate.md")
            self.assertTrue(output.exists())
            self.assertIn("Phase 4 MXFP4 Decision Gate", output.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

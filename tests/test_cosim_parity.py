from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from golden.cosim_trace import compare_trace_csv


class TestCosimParity(unittest.TestCase):
    def test_matching_trace_has_no_mismatches(self) -> None:
        tmp = Path.cwd() / "build" / "test_cosim"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        trace = tmp / "trace.csv"
        trace.write_text(
            "name,expected_hex,actual_hex\n"
            "token0_output0,00ff,00FF\n"
            "token0_output1,7a10,7a10\n",
            encoding="utf-8",
        )
        try:
            self.assertEqual(compare_trace_csv(trace), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mismatch_reports_row_and_signal(self) -> None:
        tmp = Path.cwd() / "build" / "test_cosim_mismatch"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        trace = tmp / "trace.csv"
        trace.write_text(
            "name,expected_hex,actual_hex\n"
            "token0_output0,00ff,00fe\n",
            encoding="utf-8",
        )
        try:
            mismatches = compare_trace_csv(trace)
            self.assertEqual(len(mismatches), 1)
            self.assertEqual(mismatches[0].row, 2)
            self.assertEqual(mismatches[0].name, "token0_output0")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

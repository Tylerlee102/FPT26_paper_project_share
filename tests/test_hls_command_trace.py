from __future__ import annotations

import unittest

from scripts.verify_hls_command_trace import verify_trace


class TestHlsCommandTrace(unittest.TestCase):
    def test_frozen_trace_structure_hashes_and_summary(self) -> None:
        result = verify_trace()

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["tokens"], 64)
        self.assertEqual(result["final_generation"], 64)
        self.assertEqual(result["source_hashes_verified"], 5)


if __name__ == "__main__":
    unittest.main()

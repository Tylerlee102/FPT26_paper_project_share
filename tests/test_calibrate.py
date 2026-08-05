from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

import numpy as np

from golden.calibrate import run_calibration


class TestCalibrate(unittest.TestCase):
    def test_run_calibration_writes_scales_manifest_and_reports(self) -> None:
        tmp = Path.cwd() / "build" / "test_calibrate"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            result = run_calibration(
                output_path=tmp / "scales.npz",
                manifest_path=tmp / "manifest.sha256",
                report_path=tmp / "quantization.md",
                ablation_path=tmp / "ablation.md",
                count=2,
                seed=0xFB72,
                num_value_heads=2,
                num_qk_heads=1,
                head_dim=16,
                block_size=16,
                state_block_size=16,
            )

            self.assertTrue(result.output_path.exists())
            self.assertTrue(result.manifest_path.exists())
            self.assertTrue(result.report_path.exists())
            self.assertTrue(result.ablation_path.exists())

            with np.load(result.output_path) as data:
                metadata = json.loads(str(data["metadata_json"].item()))
                self.assertEqual(metadata["num_vectors"], 2)
                self.assertIn("q_mxfp4_b16_scales", data.files)
                self.assertIn("state_mxfp8_e4m3_b16_scales", data.files)
                self.assertIn("alpha_q1_15_codes", data.files)
                self.assertIn("beta_q1_15_codes", data.files)
                self.assertEqual(data["q_mxfp4_b16_scales"].shape, (2, 1, 1))
                self.assertEqual(data["state_mxfp4_b16_scales"].shape, (2, 2, 16, 1))
                self.assertEqual(metadata["state_orientation"], "KxV")

            report = result.report_path.read_text(encoding="utf-8")
            ablation = result.ablation_path.read_text(encoding="utf-8")
            self.assertIn("MXFP4", report)
            self.assertIn("INT4 fallback", report)
            self.assertIn("| state |", ablation)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

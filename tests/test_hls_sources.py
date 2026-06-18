from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path.cwd()


class TestHlsSources(unittest.TestCase):
    def test_required_phase3_files_exist(self) -> None:
        required = [
            "hls/include/mx_types.hpp",
            "hls/include/gdn_params.hpp",
            "hls/include/mac_e2m1.hpp",
            "hls/include/block_exp_align.hpp",
            "hls/include/gdn_kernel.hpp",
            "hls/src/gdn_top.cpp",
            "hls/src/mac_e2m1.cpp",
            "hls/src/block_exp_align.cpp",
            "hls/src/phase1_prepare.cpp",
            "hls/src/phase2_state_read.cpp",
            "hls/src/phase3_update.cpp",
            "hls/src/phase4_state_write.cpp",
            "hls/src/phase5_output.cpp",
            "hls/tb/tb_gdn_top.cpp",
            "hls/tb/tb_mac_e2m1.cpp",
            "hls/tb/tb_block_exp.cpp",
            "hls/tb/tb_phaseN.cpp",
            "hls/tcl/run_csim.tcl",
            "hls/tcl/run_csynth.tcl",
            "hls/tcl/run_cosim.tcl",
            "hls/tcl/run_export.tcl",
        ]

        for relpath in required:
            self.assertTrue((ROOT / relpath).exists(), relpath)

    def test_mac_is_integer_lut_based(self) -> None:
        text = (ROOT / "hls/src/mac_e2m1.cpp").read_text(encoding="utf-8")

        self.assertIn("product_mag_q3", text)
        self.assertIn("ARRAY_PARTITION", text)
        self.assertNotIn("float", text)
        self.assertNotIn("double", text)

    def test_block_exp_align_has_int24_saturation_and_ii1_loop(self) -> None:
        text = (ROOT / "hls/src/block_exp_align.cpp").read_text(encoding="utf-8")

        self.assertIn("effective_block_exp", text)
        self.assertIn("saturate_int24", text)
        self.assertIn("PIPELINE II=1", text)

    def test_tcl_targets_u55c_250mhz(self) -> None:
        csynth = (ROOT / "hls/tcl/run_csynth.tcl").read_text(encoding="utf-8")

        self.assertIn("xcu55c-fsvh2892-2L-e", csynth)
        self.assertIn("create_clock -period 4.0", csynth)

    def test_cosim_defaults_to_phase5_token_count(self) -> None:
        cosim = (ROOT / "hls/tcl/run_cosim.tcl").read_text(encoding="utf-8")
        tb = (ROOT / "hls/tb/tb_gdn_top.cpp").read_text(encoding="utf-8")

        self.assertIn("set cosim_vectors 64", cosim)
        self.assertIn("#define GDN_TB_VECTORS 64", tb)

    def test_top_uses_persistent_partitioned_state(self) -> None:
        params = (ROOT / "hls/include/gdn_params.hpp").read_text(encoding="utf-8")
        top = (ROOT / "hls/src/gdn_top.cpp").read_text(encoding="utf-8")

        self.assertIn("GDN_STATE_READBACK", params)
        self.assertIn("static state_tensor_t resident_state", top)
        self.assertIn("BIND_STORAGE variable=resident_state", top)
        self.assertIn("ARRAY_PARTITION variable=resident_state cyclic factor=P_V dim=2", top)
        self.assertIn("ARRAY_PARTITION variable=resident_state cyclic factor=P_K dim=3", top)

    def test_no_phase3_placeholder_markers(self) -> None:
        forbidden = ("TODO", "placeholder", "not implemented", "NotImplemented")
        for relpath in (ROOT / "hls").rglob("*"):
            if relpath.is_file() and relpath.suffix in {".cpp", ".hpp", ".tcl"}:
                text = relpath.read_text(encoding="utf-8")
                for marker in forbidden:
                    self.assertNotIn(marker, text, str(relpath))


if __name__ == "__main__":
    unittest.main()

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

    def test_mac_is_integer_lut_and_shift_add_based(self) -> None:
        text = (ROOT / "hls/src/mac_e2m1.cpp").read_text(encoding="utf-8")

        self.assertIn("product_mag", text)
        self.assertIn("scale_by_e2m1", text)
        self.assertIn("ARRAY_PARTITION", text)
        self.assertNotIn("float", text)
        self.assertNotIn("double", text)

    def test_alignment_contract_has_rne_int32_saturation_and_ii1(self) -> None:
        text = (ROOT / "hls/src/block_exp_align.cpp").read_text(encoding="utf-8")

        self.assertIn("round_shift_rne", text)
        self.assertIn("saturate_int32", text)
        self.assertIn("COUNTER_ALIGNMENT_UNDERFLOWS", text)
        self.assertIn("PIPELINE II=1", text)

    def test_corrected_dimensions_commands_and_gates_are_frozen(self) -> None:
        params = (ROOT / "hls/include/gdn_params.hpp").read_text(encoding="utf-8")
        kernel = (ROOT / "hls/include/gdn_kernel.hpp").read_text(encoding="utf-8")

        self.assertIn("NUM_QK_HEADS = 16", params)
        self.assertIn("NUM_VALUE_HEADS = 32", params)
        self.assertIn("NUM_LAYERS = 36", params)
        self.assertIn("COMMAND_RESET = 0", params)
        self.assertIn("COMMAND_READBACK = 3", params)
        self.assertIn("STATUS_SHAPE_MISMATCH = 8", params)
        self.assertIn("q1_15_t", kernel)
        self.assertIn("ap_uint<24>", (ROOT / "hls/include/mx_types.hpp").read_text())
        self.assertNotIn("gate", kernel.lower())

    def test_top_uses_runtime_identity_persistent_state_and_all_phases(self) -> None:
        top = (ROOT / "hls/src/gdn_top.cpp").read_text(encoding="utf-8")

        self.assertIn("state_block_word_t resident_state", top)
        self.assertIn("ap_uint<MX_ELEMENT_BITS * BLOCK_SIZE>", top)
        self.assertIn("constexpr int MX_ELEMENT_BITS = 4", (ROOT / "hls/include/gdn_kernel.hpp").read_text(encoding="utf-8"))
        self.assertNotIn("ARRAY_PARTITION variable=resident_state", top)
        self.assertIn("NUM_SEQUENCES", top)
        self.assertIn("NUM_LAYERS", top)
        self.assertIn("BIND_STORAGE variable=resident_state", top)
        self.assertIn("phase1_validate_token", top)
        self.assertIn("q_local", top)
        self.assertIn("k_local", top)
        self.assertIn("v_local", top)
        self.assertIn("command_counter_t command_counters", top)
        self.assertIn("phase2_decay_predict_tile", top)
        self.assertIn("phase3_delta_tile", top)
        self.assertIn("phase4_update_state_tile", top)
        self.assertIn("phase5_output_tile", top)

    def test_state_requantization_is_b32_rne_and_counted(self) -> None:
        text = (ROOT / "hls/src/phase4_state_write.cpp").read_text(
            encoding="utf-8"
        )

        self.assertIn("select_scale_power", text)
        self.assertIn("reduce_scale_16", text)
        self.assertIn("quantize_exact_e2m1", text)
        self.assertIn("COUNTER_ELEMENT_SATURATIONS", text)
        self.assertIn("COUNTER_STATE_SCALE_CHANGES", text)

    def test_transport_validation_does_not_request_unsatisfied_pipeline(self) -> None:
        validation = (ROOT / "hls/src/phase1_prepare.cpp").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("#pragma HLS PIPELINE\n", validation)

    def test_tcl_targets_u55c_250mhz(self) -> None:
        csynth = (ROOT / "hls/tcl/run_csynth.tcl").read_text(encoding="utf-8")

        self.assertIn("xcu55c-fsvh2892-2L-e", csynth)
        self.assertIn("create_clock -period 4.0", csynth)
        self.assertIn("config_compile -pipeline_loops 0", csynth)
        self.assertIn("-std=c++14", csynth)

    def test_cosim_defaults_to_64_commands(self) -> None:
        cosim = (ROOT / "hls/tcl/run_cosim.tcl").read_text(encoding="utf-8")
        tb = (ROOT / "hls/tb/tb_gdn_top.cpp").read_text(encoding="utf-8")

        self.assertIn("set cosim_vectors 64", cosim)
        self.assertIn("GDN_COSIM_TRACE", cosim)
        self.assertIn('set cosim_rtl "verilog"', cosim)
        self.assertIn("GDN_COSIM_RTL", cosim)
        self.assertIn("cosim_design -rtl $cosim_rtl", cosim)
        self.assertIn("#define GDN_TB_VECTORS 64", tb)
        self.assertIn("COMMAND_READBACK", tb)
        self.assertIn("STATUS_INVALID_ENCODING", tb)

    def test_no_phase3_placeholder_markers(self) -> None:
        forbidden = ("TODO", "placeholder", "not implemented", "NotImplemented")
        for relpath in (ROOT / "hls").rglob("*"):
            if relpath.is_file() and relpath.suffix in {".cpp", ".hpp", ".tcl"}:
                text = relpath.read_text(encoding="utf-8")
                for marker in forbidden:
                    self.assertNotIn(marker, text, str(relpath))


if __name__ == "__main__":
    unittest.main()

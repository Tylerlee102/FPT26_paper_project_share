from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
import zipfile
import csv
from pathlib import Path

from scripts.validate_paper_pack import validate_pack


class TestLegacyPaperProvenancePreservation(unittest.TestCase):
    """Audit preserved pre-correction artifacts; never validates current claims."""

    def test_legacy_artifacts_are_explicitly_invalidated(self) -> None:
        status = Path("paper/README.md").read_text(encoding="utf-8")
        gate = json.loads(
            Path("reports/final_completion_gate.json").read_text(encoding="utf-8")
        )
        self.assertIn("READY FOR HUMAN SUBMISSION REVIEW", status)
        self.assertIn("must not be", status)
        self.assertIn("current paper evidence", status)
        self.assertTrue(gate["paper_pdf_permitted"])
        self.assertEqual(gate["required_nonpassing_gate_count"], 0)
        self.assertTrue(Path("paper/corrected/paper.pdf").is_file())

    def test_legacy_every_number_has_provenance(self) -> None:
        numbers = json.loads(Path("paper/numbers.json").read_text(encoding="utf-8"))
        provenance = json.loads(Path("paper/provenance.json").read_text(encoding="utf-8"))

        self.assertEqual(set(numbers), set(provenance))
        for key, record in numbers.items():
            self.assertRegex(key, r"^[a-z][a-z0-9_]*$")
            for field in ("value", "units", "source", "git_sha", "timestamp", "extractor"):
                self.assertIn(field, record, key)
            self.assertRegex(record["git_sha"], r"^[0-9a-f]{40}$")
            if record["source"] != "external":
                self.assertTrue(Path(record["source"]).exists(), record["source"])
                self.assertIsNotNone(record.get("source_line"), key)
            else:
                self.assertIn("notes", record, key)

    def test_legacy_snippet_macros_have_backing_numbers_when_present(self) -> None:
        numbers = json.loads(Path("paper/numbers.json").read_text(encoding="utf-8"))
        snippets = Path("paper/snippets")
        macro_file = snippets / "result_macros.tex"
        if not macro_file.exists():
            return

        text = macro_file.read_text(encoding="utf-8")
        macro_keys = set(re.findall(r"%\s*numbers\.json:([a-z][a-z0-9_]*)", text))
        self.assertTrue(macro_keys <= set(numbers))

    def test_legacy_generated_phase6_artifacts_exist(self) -> None:
        required = [
            Path("paper/snippets/result_macros.tex"),
            Path("paper/snippets/headline_speedup.tex"),
            Path("paper/tables/main_results.tex"),
            Path("paper/tables/ablation_quantization.tex"),
            Path("paper/tables/ablation_block_size.tex"),
            Path("paper/tables/area_breakdown.tex"),
            Path("paper/tables/recurrent_state_stress.tex"),
            Path("paper/tables/state_storage_traffic.tex"),
            Path("reports/benchmark/sweep.csv"),
            Path("reports/benchmark/notes.md"),
        ]
        for path in required:
            self.assertTrue(path.exists(), path)

        for name in (
            "parallelism_pareto",
            "block_size_accuracy",
            "latency_comparison",
            "area_breakdown",
            "roofline",
            "state_precision_stress",
            "state_traffic",
        ):
            pdf = Path("paper/figures") / f"{name}.pdf"
            source = Path("paper/figures") / f"{name}.py"
            self.assertTrue(pdf.exists(), pdf)
            self.assertTrue(source.exists(), source)
            self.assertEqual(pdf.read_bytes()[:5], b"%PDF-")

    def test_legacy_phase6_sweep_rows_preserve_report_links(self) -> None:
        sweep = Path("reports/benchmark/sweep.csv")
        with sweep.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        self.assertGreaterEqual(len(rows), 5)
        for row in rows:
            self.assertIn(
                row["latency_source_kind"],
                {"cosim", "csynth_estimate"},
                row["config"],
            )
            self.assertEqual(row["impl_status"], "post_impl", row["config"])
            self.assertGreater(int(row["tokens"]), 0, row["config"])
            for field in ("source_latency", "source_util", "source_power"):
                self.assertTrue(Path(row[field]).exists(), f"{row['config']} {field}: {row[field]}")

        default = next(row for row in rows if row["config"] == "ours_mxfp4_b32_pk16_pv8")
        self.assertEqual(default["latency_source_kind"], "csynth_estimate")
        self.assertTrue(
            all(
                row["latency_source_kind"] == "cosim"
                for row in rows
                if row is not default
            )
        )
        self.assertGreaterEqual(int(default["tokens"]), 64)

    def test_legacy_ieee_tables_match_legacy_numbers(self) -> None:
        numbers = json.loads(Path("paper/numbers.json").read_text(encoding="utf-8"))
        with Path("reports/benchmark/sweep.csv").open(newline="", encoding="utf-8") as handle:
            sweep_rows = list(csv.DictReader(handle))
        default = next(row for row in sweep_rows if row["config"] == "ours_mxfp4_b32_pk16_pv8")

        tab2 = Path("paper/ieee_tables/tab2_implementation_evidence.tex").read_text(encoding="utf-8")
        tokens = int(numbers["ours_mxfp4_b32_tokens_cosim"]["value"])
        qwen_status = str(numbers["qwen_capture_status"]["value"]).replace("_", r"\_")
        self.assertIn(f"C/RTL cosim length & {tokens} tokens", tab2)
        self.assertIn(f"Qwen capture status & {qwen_status}", tab2)

        tab3 = Path("paper/ieee_tables/tab3_design_sweep.tex").read_text(encoding="utf-8")
        expected_default = (
            f"default & {default['block_size']} & {default['p_k']} & {default['p_v']} & {default['tokens']} "
            f"& {float(default['latency_us']):.3f} & {float(default['power_w']):.3f} "
            f"& {float(default['lut_pct']):.2f} & {float(default['dsp_pct']):.2f}"
        )
        self.assertIn(expected_default, tab3)

        standalone = Path("paper/compiled_tables_graphs/ieee_tables_graphs.tex").read_text(encoding="utf-8")
        for stale_value in ("51.788", "9.096", r"3.77\%", r"1.57\%"):
            self.assertNotIn(stale_value, standalone)

    def test_legacy_extended_synthetic_metrics_preserve_provenance(self) -> None:
        numbers = json.loads(Path("paper/numbers.json").read_text(encoding="utf-8"))
        provenance = json.loads(Path("paper/provenance.json").read_text(encoding="utf-8"))

        required = {
            "synthetic_drift_tokens": "reports/benchmark/state_drift.csv",
            "synthetic_drift_mxfp4_final_output_cosine": "reports/benchmark/state_drift.csv",
            "synthetic_drift_mxfp8_final_output_cosine": "reports/benchmark/state_drift.csv",
            "synthetic_boundary_state_mxfp4_b16_output_cosine": "reports/benchmark/state_boundary.csv",
            "synthetic_boundary_state_mxfp8_b16_output_cosine": "reports/benchmark/state_boundary.csv",
            "synthetic_stress_combined_stress_state_mxfp4_b16_worst_output_cosine": "reports/benchmark/stress_accuracy.csv",
            "synthetic_stress_combined_stress_state_mxfp8_b16_worst_output_cosine": "reports/benchmark/stress_accuracy.csv",
            "state_storage_mxfp4_b32_bytes": "reports/benchmark/storage_overhead.csv",
            "offchip_mxfp4_b32_naive_three_pass_bytes_per_token": "reports/benchmark/offchip_state_traffic.csv",
            "offchip_mxfp4_b32_persistent_bytes_per_token": "reports/benchmark/offchip_state_traffic.csv",
        }
        for key, source in required.items():
            self.assertIn(key, numbers)
            self.assertEqual(numbers[key]["source"], source)
            self.assertEqual(provenance[key]["source"], source)
            self.assertIsNotNone(numbers[key]["source_line"], key)

        self.assertEqual(numbers["synthetic_drift_tokens"]["value"], 1024)
        self.assertGreater(numbers["synthetic_drift_mxfp8_final_output_cosine"]["value"], numbers["synthetic_drift_mxfp4_final_output_cosine"]["value"])
        self.assertEqual(numbers["offchip_mxfp4_b32_persistent_bytes_per_token"]["value"], 0)

    def test_corrected_phase7_pack_contents_when_present(self) -> None:
        git_exe = shutil.which("git")
        if git_exe is None:
            self.skipTest("git executable is not available")
        result = subprocess.run(
            [git_exe, "-c", f"safe.directory={Path.cwd().as_posix()}", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        sha = result.stdout.strip()
        pack = Path("paper/pack") / f"submission_{sha}.zip"
        if not pack.exists():
            self.skipTest(f"Phase 7 pack has not been generated for {sha}")

        with zipfile.ZipFile(pack) as archive:
            name_list = archive.namelist()
            names = set(name_list)

        required = {
            "paper/numbers.json",
            "paper/provenance.json",
            "paper/corrected/numbers.json",
            "paper/corrected/provenance.json",
            "paper/corrected/asset_manifest.json",
            "paper/corrected/paper.tex",
            "paper/corrected/paper_audit_candidate.pdf",
            "paper/corrected/paper_audit_build_manifest.json",
            "paper/corrected/paper_visual_audit.json",
            "paper/corrected/paper.pdf",
            "paper/corrected/paper_finalization_manifest.json",
            "reports/phase7_status.md",
            "reports/known_issues.md",
            "docs/reviewer_traceability.md",
            "docs/evidence_manifest.md",
            "paper/corrected/tables/long_sequence.tex",
            "paper/corrected/tables/controlled_hls.tex",
            "paper/corrected/tables/mitigation_hls.tex",
            "paper/corrected/tables/corrected_heldout.tex",
            "paper/corrected/tables/scale_policy.tex",
            "paper/corrected/snippets/corrected_result_macros.tex",
            "pack_manifest.json",
            "git_sha.txt",
            "git_status.txt",
            "git_diff_stat.txt",
        }
        self.assertTrue(required <= names)
        for name in required:
            self.assertEqual(name_list.count(name), 1, name)

        checks, _details = validate_pack(pack)
        failures = [check for check in checks if not check.passed]
        self.assertFalse(failures, "; ".join(f"{check.name}: {check.detail}" for check in failures))


if __name__ == "__main__":
    unittest.main()

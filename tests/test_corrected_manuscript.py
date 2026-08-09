import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "corrected" / "paper.tex"
MACROS = (
    ROOT
    / "paper"
    / "corrected"
    / "snippets"
    / "corrected_result_macros.tex"
)
EXTENDED = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_encoded"
    / "rs2_encoded_candidate_summary.json"
)


def test_corrected_manuscript_uses_the_controlled_question_and_current_assets() -> None:
    text = PAPER.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "Can Native MXFP4 Replace BF16 in FPGA Gated DeltaNet Decode?" in text
    assert "Cost and Long-Horizon Recurrent-State Drift" in text
    assert "inherited from prior work" in normalized
    assert "recurrence-core kernel" in text
    assert "layer-level and synthetic" in text
    assert "does not replace BF16" in text
    assert "paper/corrected/snippets/corrected_result_macros.tex" in text
    for name in (
        "rs2_transfer_sizes.tex",
        "rs2_controlled_long.tex",
        "qwen_recurrent_stability.tex",
        "rs2_hls.tex",
        "rs2_stability_gates.tex",
        "rs2_postroute.tex",
        "rs2_power_breakdown.tex",
        "scale_policy.tex",
    ):
        assert f"paper/corrected/tables/{name}" in text
    assert "paper/figures/corrected/corrected_candidate_datapath.pdf" in text
    assert "paper/figures/corrected/rs2_output_cosine_vs_token.pdf" in text
    assert "paper/figures/corrected/rs2_state_relative_l2_vs_token.pdf" in text
    assert "paper/figures/corrected/rs2_memory_performance_accuracy.pdf" in text
    assert "same high-retention random-state input prefix" in normalized
    assert "performs reductions in FP32" in text
    assert "signed symmetric four-bit quantization" in text
    assert "MXFP4 floating Q/DQ" in text
    assert "native encoded path" in text
    assert "not a formal stability certificate" in normalized
    assert "not board energy or a measured end-to-end Pareto frontier" in normalized
    assert (
        "type-layout counts before interface packing, not measured AXI traffic"
        in normalized
    )
    assert "There are no projection weights in a test vector" in normalized
    assert "s=\\lceil\\log_2(m/x_{\\max})\\rceil" in text
    assert "short model-derived Qwen" in normalized
    assert "native-MXFP8, and RS2/R3 HLS comparison" in normalized
    assert "\\RsTwoCandidateCosineEightK{}" in text
    assert "\\RsTwoCandidateStateLTwoEightK{}" in text


def test_corrected_manuscript_defines_formats_and_positions_prior_work() -> None:
    text = PAPER.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for phrase in (
        "Open Compute Project (OCP)",
        "bfloat16 (BF16)",
        "field-programmable gate array (FPGA)",
        "lookup-table (LUT)",
        "high-level synthesis (HLS)",
        "round-to-nearest-even (RNE)",
        "digital signal-processing (DSP)",
        "Xilinx Runtime (XRT)",
        "initiation interval (II)",
        "register-transfer-level (RTL)",
        "exclusive-or (XOR)",
        "comma-separated values (CSV)",
        "Microscaling Representation",
    ):
        assert phrase in normalized
    cited = {
        key.strip()
        for group in re.findall(r"\\cite\{([^}]+)\}", text)
        for key in group.split(",")
    }
    for key in (
        "qwen3nextmodel",
        "transformersqwen",
        "fla021",
        "deltanet",
        "jackscales",
        "mxformer",
        "micromix",
        "mxattention",
        "mxfpbenchmark",
        "quantgdn",
        "ssdi8",
    ):
        assert key in cited
        assert f"\\bibitem{{{key}}}" in text
    for classification in ("Inherited", "Corrected", "Modified", "Newly proposed"):
        assert classification in text
    assert "E2M1/E8M0 FPGA arithmetic & Modified" in text
    assert "not a claim of literature priority" in text

    introduction = text.split("\\section{Introduction}", 1)[1].split(
        "\\section{Background and Scope}", 1
    )[0]
    assert "field-programmable gate array (FPGA)" in introduction
    assert introduction.rstrip().endswith("long synthetic decode traces?")


def test_uniform_encoded_reduction_contract_is_not_the_corrected_guarded_contract() -> None:
    text = PAPER.read_text(encoding="utf-8")
    uniform = text.split("\\subsection{Uniform MXFP4 Path}", 1)[1].split(
        "\\subsection{Recurrence-Aware Correction}", 1
    )[0]
    correction = text.split("\\subsection{Recurrence-Aware Correction}", 1)[1].split(
        "\\section{FPGA Implementation}", 1
    )[0]
    assert "One flat 128-term reduction" in uniform
    assert "greatest nonzero product exponent" in uniform
    assert "This uniform baseline has no guard-bit offset" in uniform
    assert "\\CorrectedAlignmentGuardBits{}" not in uniform
    assert "\\CorrectedAlignmentGuardBits{}" in correction


def test_corrected_manuscript_states_the_finite_horizon_error_bound() -> None:
    text = PAPER.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "parallel and orthogonal components obey" in normalized
    assert "worst-case operator norm is one because $K>1$" in normalized
    assert "\\prod_{i=1}^{T}\\alpha_i" in text
    assert "\\prod_{i=j+1}^{T}\\alpha_i" in text
    assert "permits decay arbitrarily close to one" in normalized
    assert "persistent-excitation bound is not established" in normalized


def test_corrected_manuscript_consolidates_adjacent_quality_tables() -> None:
    text = PAPER.read_text(encoding="utf-8")
    assert len(re.findall(r"\\begin\{table\*?\}", text)) == 9
    assert len(re.findall(r"\\begin\{figure\*?\}", text)) == 4
    assert "\\label{tab:rs2-stability}" in text
    assert "paper/corrected/tables/rs2_stability_gates.tex" in text
    assert "paper/corrected/tables/corrected_quality.tex" not in text
    assert "paper/corrected/tables/mitigation_hls.tex" not in text


def test_corrected_manuscript_avoids_invalidated_claims() -> None:
    text = PAPER.read_text(encoding="utf-8").lower()
    forbidden = (
        "h100 baseline",
        "speedup versus h100",
        "energy efficiency improvement",
        "perplexity preservation",
        "full qwen3-next accuracy",
        "complete gdn layer accelerator",
        "first native",
        "the open question",
        "we present a novel",
        "certified",
    )
    for phrase in forbidden:
        assert phrase not in text
    assert "example_research_paper_draft" not in text
    assert "result_macros.tex" not in text.replace(
        "corrected_result_macros.tex", ""
    )
    assert "author metadata check required" not in text


def test_corrected_manuscript_macro_references_are_defined_and_not_bare() -> None:
    text = PAPER.read_text(encoding="utf-8")
    macro_text = MACROS.read_text(encoding="utf-8")
    defined = set(
        re.findall(r"\\newcommand\{\\((?:Corrected|RsTwo)[A-Za-z]+)\}", macro_text)
    )
    used = set(re.findall(r"\\((?:Corrected|RsTwo)[A-Za-z]+)", text))
    assert used
    assert used <= defined
    assert re.search(r"(?<!\\)\bCorrected[A-Z][A-Za-z]+", text) is None
    assert re.search(r"(?<!\\)\bRsTwo[A-Z][A-Za-z]+", text) is None
    for stale_literal in (
        "0.729275",
        "1.103841",
        "0.994430",
        "0.098653",
        "435,089",
        "17,954,144",
        "39,947,365",
        "4.25 logical bits",
        "0xFB72",
        "16,512",
        "4,480",
        "8,832",
        "24,576",
        "0.410379",
        "0.698070",
        "0.981307",
        "0.997011",
    ):
        assert stale_literal not in text


def test_corrected_manuscript_has_balanced_latex_and_resolved_dependencies() -> None:
    text = PAPER.read_text(encoding="utf-8")
    uncommented = "\n".join(line.split("%", 1)[0] for line in text.splitlines())
    assert len(re.findall(r"(?<!\\)\{", uncommented)) == len(
        re.findall(r"(?<!\\)\}", uncommented)
    )

    stack: list[str] = []
    for match in re.finditer(r"\\(begin|end)\{([^}]+)\}", uncommented):
        action, environment = match.groups()
        if action == "begin":
            stack.append(environment)
        else:
            assert stack and stack.pop() == environment
    assert not stack

    cited = {
        key.strip()
        for group in re.findall(r"\\cite\{([^}]+)\}", uncommented)
        for key in group.split(",")
    }
    defined = set(re.findall(r"\\bibitem\{([^}]+)\}", uncommented))
    assert cited == defined
    first_use: list[str] = []
    for group in re.findall(r"\\cite\{([^}]+)\}", uncommented):
        for key in (item.strip() for item in group.split(",")):
            if key not in first_use:
                first_use.append(key)
    bibliography_order = re.findall(r"\\bibitem\{([^}]+)\}", uncommented)
    assert bibliography_order == first_use

    labels = set(re.findall(r"\\label\{([^}]+)\}", uncommented))
    references = set(re.findall(r"\\ref\{([^}]+)\}", uncommented))
    assert labels <= references

    for command, relative in re.findall(
        r"\\(input|includegraphics)(?:\[[^]]+\])?\{([^}]+)\}", uncommented
    ):
        path = ROOT / relative
        if command == "input" and not path.suffix:
            path = path.with_suffix(".tex")
        assert path.is_file(), relative


def test_corrected_manuscript_extended_pass_claim_has_full_replay_evidence() -> None:
    payload = json.loads(EXTENDED.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    extended = payload["gate_results"]["extended_development"]
    assert extended["status"] == "PASS"
    assert extended["run_count"] == extended["expected_run_count"] == 2

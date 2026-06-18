from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NUMBERS = ROOT / "paper" / "numbers.json"
SNIPPETS = ROOT / "paper" / "snippets"
TABLES = ROOT / "paper" / "tables"


TOKEN_MAP = {
    "mxfp4": "MxfpFour",
    "mxfp8": "MxfpEight",
    "int4": "IntFour",
    "fp32": "FpThirtyTwo",
    "b16": "BSixteen",
    "b32": "BThirtyTwo",
    "h100": "HOneHundred",
    "usc": "Usc",
    "q": "Q",
    "k": "K",
    "v": "V",
    "us": "Us",
    "ns": "Ns",
    "w": "W",
    "mj": "Mj",
}

NUMBER_TOKEN_MAP = {
    "0": "Zero",
    "1": "One",
    "2": "Two",
    "3": "Three",
    "4": "Four",
    "5": "Five",
    "6": "Six",
    "7": "Seven",
    "8": "Eight",
    "9": "Nine",
    "16": "Sixteen",
    "32": "ThirtyTwo",
    "64": "SixtyFour",
    "100": "OneHundred",
}


def _load() -> dict[str, dict[str, Any]]:
    return json.loads(NUMBERS.read_text(encoding="utf-8"))


def _macro_name(key: str) -> str:
    parts: list[str] = []
    for token in key.split("_"):
        if token in TOKEN_MAP:
            parts.append(TOKEN_MAP[token])
        elif re.fullmatch(r"\d+", token):
            parts.append(NUMBER_TOKEN_MAP.get(token, "".join(NUMBER_TOKEN_MAP[d] for d in token)))
        else:
            subparts: list[str] = []
            for piece in re.findall(r"[A-Za-z]+|\d+", token):
                if piece.isdigit():
                    subparts.append(NUMBER_TOKEN_MAP.get(piece, "".join(NUMBER_TOKEN_MAP[d] for d in piece)))
                else:
                    subparts.append(piece[:1].upper() + piece[1:])
            parts.append("".join(subparts))
    return "".join(parts)


def _escape_latex_text(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def _latex_value(record: dict[str, Any]) -> str:
    value = record["value"]
    units = record["units"]
    if isinstance(value, float):
        raw = f"{value:.3f}".rstrip("0").rstrip(".")
    elif isinstance(value, str):
        raw = _escape_latex_text(value)
    else:
        raw = str(value)
    unit_map = {
        "x": "$\\times$",
        "percent": "\\%",
        "watts": "\\,W",
        "watts_tdp": "\\,W",
        "watts_tdp_upper_bound": "\\,W",
        "us_per_token": "\\,$\\mu$s",
        "cycles": "\\,cycles",
        "tokens": "\\,tokens",
        "mj_per_token": "\\,mJ",
        "mj_per_token_upper_bound": "\\,mJ",
        "mhz": "\\,MHz",
        "ns": "\\,ns",
    }
    return raw + unit_map.get(units, "")


def _v(numbers: dict[str, dict[str, Any]], key: str) -> Any:
    return numbers[key]["value"]


def _maybe_v(numbers: dict[str, dict[str, Any]], key: str) -> str:
    if key not in numbers:
        return "--"
    return str(numbers[key]["value"])


def _maybe_power(numbers: dict[str, dict[str, Any]], key: str) -> str:
    if key not in numbers:
        return "--"
    return f"{numbers[key]['value']} W"


def _maybe_fmt(numbers: dict[str, dict[str, Any]], key: str, digits: int = 3) -> str:
    if key not in numbers:
        return "--"
    value = numbers[key]["value"]
    if isinstance(value, float):
        return f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def _write_macros(numbers: dict[str, dict[str, Any]]) -> None:
    SNIPPETS.mkdir(parents=True, exist_ok=True)
    lines = [
        "% AUTO-GENERATED -- DO NOT EDIT BY HAND",
        "% Generated from paper/numbers.json",
        "\\providecommand{\\xspace}{}",
        "",
    ]
    for key in sorted(numbers):
        lines.append(f"% numbers.json:{key}")
        lines.append(f"\\newcommand{{\\{_macro_name(key)}}}{{{_latex_value(numbers[key])}\\xspace}}")
    (SNIPPETS / "result_macros.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (SNIPPETS / "headline_speedup.tex").write_text(
        "\n".join(
            [
                "% AUTO-GENERATED -- DO NOT EDIT BY HAND",
                "\\providecommand{\\xspace}{}",
                "% numbers.json:headline_speedup_vs_h100",
                f"\\newcommand{{\\headlineSpeedup}}{{{_latex_value(numbers['headline_speedup_vs_h100'])}\\xspace}}",
                "% numbers.json:headline_energy_efficiency_vs_h100",
                f"\\newcommand{{\\headlineEnergyEff}}{{{_latex_value(numbers['headline_energy_efficiency_vs_h100'])}\\xspace}}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_tables(numbers: dict[str, dict[str, Any]]) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    main = f"""% AUTO-GENERATED -- DO NOT EDIT BY HAND
\\begin{{tabular}}{{lrrrrr}}
\\toprule
Configuration & Latency & LUT & DSP & BRAM & Power \\\\
\\midrule
H100 PCIe GPU (paper-cited)
  & {_v(numbers, 'h100_baseline_latency_us')} $\\mu$s & -- & -- & -- & {_v(numbers, 'h100_baseline_power_w')} W \\\\
USC FPGA Hiter=8 (paper-cited)
  & {_v(numbers, 'usc_baseline_latency_us')} $\\mu$s & -- & -- & -- & $\\le${_v(numbers, 'usc_baseline_power_w')} W \\\\
\\midrule
Ours, MXFP4 B=32, P\\_K=16, P\\_V=8
  & {_v(numbers, 'ours_mxfp4_b32_latency_us')} $\\mu$s & {_v(numbers, 'ours_mxfp4_b32_lut_pct')}\\% & {_v(numbers, 'ours_mxfp4_b32_dsp_pct')}\\% & {_v(numbers, 'ours_mxfp4_b32_bram_pct')}\\% & {_v(numbers, 'ours_mxfp4_b32_power_w')} W \\\\
Ours, MXFP4 B=16, P\\_K=32, P\\_V=16 (sweep)
  & {_maybe_v(numbers, 'ours_mxfp4_b16_pk32_pv16_latency_us')} $\\mu$s & {_maybe_v(numbers, 'ours_mxfp4_b16_pk32_pv16_lut_pct')}\\% & {_maybe_v(numbers, 'ours_mxfp4_b16_pk32_pv16_dsp_pct')}\\% & {_maybe_v(numbers, 'ours_mxfp4_b16_pk32_pv16_bram_pct')}\\% & {_maybe_power(numbers, 'ours_mxfp4_b16_pk32_pv16_power_w')} \\\\
Ours, MXFP4 B=32, P\\_K=32, P\\_V=16 (sweep)
  & {_maybe_v(numbers, 'ours_mxfp4_pk32_pv16_b32_latency_us')} $\\mu$s & {_maybe_v(numbers, 'ours_mxfp4_pk32_pv16_b32_lut_pct')}\\% & {_maybe_v(numbers, 'ours_mxfp4_pk32_pv16_b32_dsp_pct')}\\% & {_maybe_v(numbers, 'ours_mxfp4_pk32_pv16_b32_bram_pct')}\\% & {_maybe_power(numbers, 'ours_mxfp4_pk32_pv16_b32_power_w')} \\\\
\\bottomrule
\\end{{tabular}}
"""
    (TABLES / "main_results.tex").write_text(main, encoding="utf-8")

    ablation = f"""% AUTO-GENERATED -- DO NOT EDIT BY HAND
\\begin{{tabular}}{{lrr}}
\\toprule
Tensor & Output cosine & Source \\\\
\\midrule
q & {_v(numbers, 'ablation_q_output_cosine')} & synthetic \\\\
k & {_v(numbers, 'ablation_k_output_cosine')} & synthetic \\\\
v & {_v(numbers, 'ablation_v_output_cosine')} & synthetic \\\\
gate & {_v(numbers, 'ablation_gate_output_cosine')} & synthetic \\\\
state & {_v(numbers, 'ablation_state_output_cosine')} & synthetic \\\\
\\bottomrule
\\end{{tabular}}
"""
    (TABLES / "ablation_quantization.tex").write_text(ablation, encoding="utf-8")

    area = f"""% AUTO-GENERATED -- DO NOT EDIT BY HAND
\\begin{{tabular}}{{lrrr}}
\\toprule
Configuration & LUT & DSP & BRAM \\\\
\\midrule
Ours, MXFP4 B=32 & {_v(numbers, 'ours_mxfp4_b32_lut_pct')}\\% & {_v(numbers, 'ours_mxfp4_b32_dsp_pct')}\\% & {_v(numbers, 'ours_mxfp4_b32_bram_pct')}\\% \\\\
\\bottomrule
\\end{{tabular}}
"""
    (TABLES / "area_breakdown.tex").write_text(area, encoding="utf-8")

    block = f"""% AUTO-GENERATED -- DO NOT EDIT BY HAND
\\begin{{tabular}}{{lrr}}
\\toprule
Block size & Synthetic output cosine & State rel L2 \\\\
\\midrule
32 & {_v(numbers, 'synthetic_mxfp4_b32_output_cosine')} & {_v(numbers, 'synthetic_mxfp4_b32_state_rel_l2')} \\\\
16 & {_v(numbers, 'synthetic_mxfp4_b16_output_cosine')} & {_v(numbers, 'synthetic_mxfp4_b16_state_rel_l2')} \\\\
\\bottomrule
\\end{{tabular}}
"""
    (TABLES / "ablation_block_size.tex").write_text(block, encoding="utf-8")

    recurrent = f"""% AUTO-GENERATED -- DO NOT EDIT BY HAND
\\begin{{tabular}}{{lrr}}
\\toprule
Synthetic test & MXFP4 state & MXFP8 state \\\\
\\midrule
1024-token final output cosine
  & {_maybe_fmt(numbers, 'synthetic_drift_mxfp4_final_output_cosine')} & {_maybe_fmt(numbers, 'synthetic_drift_mxfp8_final_output_cosine')} \\\\
1024-token final state rel. L2
  & {_maybe_fmt(numbers, 'synthetic_drift_mxfp4_final_state_rel_l2')} & {_maybe_fmt(numbers, 'synthetic_drift_mxfp8_final_state_rel_l2')} \\\\
256-token boundary output cosine
  & {_maybe_fmt(numbers, 'synthetic_boundary_state_mxfp4_b16_output_cosine')} & {_maybe_fmt(numbers, 'synthetic_boundary_state_mxfp8_b16_output_cosine')} \\\\
Combined-stress worst output cosine
  & {_maybe_fmt(numbers, 'synthetic_stress_combined_stress_state_mxfp4_b16_worst_output_cosine')} & {_maybe_fmt(numbers, 'synthetic_stress_combined_stress_state_mxfp8_b16_worst_output_cosine')} \\\\
Outlier-stress worst output cosine
  & {_maybe_fmt(numbers, 'synthetic_stress_outlier_state_mxfp4_b16_worst_output_cosine')} & {_maybe_fmt(numbers, 'synthetic_stress_outlier_state_mxfp8_b16_worst_output_cosine')} \\\\
\\bottomrule
\\end{{tabular}}
"""
    (TABLES / "recurrent_state_stress.tex").write_text(recurrent, encoding="utf-8")

    traffic = f"""% AUTO-GENERATED -- DO NOT EDIT BY HAND
\\begin{{tabular}}{{lr}}
\\toprule
Metric & Value \\\\
\\midrule
MXFP4 B=32 recurrent-state storage & {_maybe_v(numbers, 'state_storage_mxfp4_b32_bytes')} bytes \\\\
Reduction vs FP32 & {_maybe_v(numbers, 'state_storage_mxfp4_b32_reduction_vs_fp32_pct')}\\% \\\\
Reduction vs BF16 & {_maybe_v(numbers, 'state_storage_mxfp4_b32_reduction_vs_bf16_pct')}\\% \\\\
Naive three-pass off-chip state traffic & {_maybe_v(numbers, 'offchip_mxfp4_b32_naive_three_pass_bytes_per_token')} bytes/token \\\\
Persistent steady-state off-chip state traffic & {_maybe_v(numbers, 'offchip_mxfp4_b32_persistent_bytes_per_token')} bytes/token \\\\
\\bottomrule
\\end{{tabular}}
"""
    (TABLES / "state_storage_traffic.tex").write_text(traffic, encoding="utf-8")


def main() -> int:
    numbers = _load()
    _write_macros(numbers)
    _write_tables(numbers)
    print("Wrote paper snippets and tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

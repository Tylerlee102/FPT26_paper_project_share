"""Generate a scheduler-free wrapper around the selected HLS Verilog."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hls" / "rtl_tb" / "tb_gdn_rs2_top_direct.sv"
AXI_SOURCE = ROOT / "hls" / "rtl_tb" / "axi_memory_model.sv"
DEFAULT_OUTPUT = ROOT / "build" / "verilator_fast" / "rs2_fast_wrapper.sv"
PUBLIC_SIGNALS = {
    "ap_clk",
    "ap_rst_n",
    "live_entries_in",
    "s_axi_control_AWVALID",
    "s_axi_control_AWREADY",
    "s_axi_control_AWADDR",
    "s_axi_control_WVALID",
    "s_axi_control_WREADY",
    "s_axi_control_WDATA",
    "s_axi_control_WSTRB",
    "s_axi_control_ARVALID",
    "s_axi_control_ARADDR",
    "s_axi_control_RREADY",
    "s_axi_control_BVALID",
    "s_axi_control_BREADY",
    "s_axi_control_r_AWVALID",
    "s_axi_control_r_AWREADY",
    "s_axi_control_r_AWADDR",
    "s_axi_control_r_WVALID",
    "s_axi_control_r_WREADY",
    "s_axi_control_r_WDATA",
    "s_axi_control_r_WSTRB",
    "s_axi_control_r_ARVALID",
    "s_axi_control_r_ARADDR",
    "s_axi_control_r_RREADY",
    "s_axi_control_r_BVALID",
    "s_axi_control_r_BREADY",
}


def _mark_public(line: str, found: set[str]) -> str:
    for name in PUBLIC_SIGNALS:
        if re.search(rf"\b{re.escape(name)}\b", line):
            found.add(name)
            if " = " in line:
                return line.replace(
                    " = ", " /* verilator public_flat_rw */ = ", 1
                )
            return line.replace(";", " /* verilator public_flat_rw */;", 1)
    return line


def generate(
    output: Path = DEFAULT_OUTPUT, memory_output: Path | None = None
) -> dict[str, object]:
    if memory_output is None:
        memory_output = output.with_name("axi_memory_model_fast.sv")
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    stop = next(
        index for index, line in enumerate(lines) if "gdn_rs2_top dut (.*);" in line
    )
    prefix = lines[: stop + 1]
    found: set[str] = set()
    prefix = [
        line.replace("module tb_gdn_rs2_top_direct;", "module rs2_fast_wrapper;")
        for line in prefix
        if "always #2 ap_clk" not in line
    ]
    prefix = [_mark_public(line, found) for line in prefix]
    missing = PUBLIC_SIGNALS - found
    if missing:
        raise ValueError(f"fast-wrapper public signals are absent: {sorted(missing)}")
    prefix.extend(
        [
            "",
            "    wire fast_ap_idle /* verilator public_flat_rw */;",
            "    wire fast_ap_done /* verilator public_flat_rw */;",
            "    wire fast_ap_start /* verilator public_flat_rw */;",
            "    assign fast_ap_idle = dut.ap_idle;",
            "    assign fast_ap_done = dut.ap_done;",
            "    assign fast_ap_start = dut.ap_start;",
            "endmodule",
            "",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(prefix), encoding="utf-8", newline="\n")
    memory_text = AXI_SOURCE.read_text(encoding="utf-8")
    memory_declaration = "reg [7:0] mem [0:MEM_BYTES-1];"
    if memory_text.count(memory_declaration) != 1:
        raise ValueError("AXI memory declaration is absent or ambiguous")
    memory_text = memory_text.replace(
        memory_declaration,
        "reg [7:0] mem [0:MEM_BYTES-1] /* verilator public_flat_rw */;",
    )
    memory_output.parent.mkdir(parents=True, exist_ok=True)
    memory_output.write_text(memory_text, encoding="utf-8", newline="\n")
    payload = {
        "schema": 1,
        "status": "PASS",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper(),
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest().upper(),
        "memory_source": AXI_SOURCE.relative_to(ROOT).as_posix(),
        "memory_source_sha256": hashlib.sha256(AXI_SOURCE.read_bytes()).hexdigest().upper(),
        "memory_output": memory_output.relative_to(ROOT).as_posix(),
        "memory_output_sha256": hashlib.sha256(memory_output.read_bytes()).hexdigest().upper(),
        "transformation": (
            "retain the exact DUT and AXI memory-model wiring, remove only the "
            "timed clock generator and procedural test sequence"
        ),
    }
    manifest = output.with_suffix(".json")
    manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--memory-output", type=Path)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    memory_output = args.memory_output
    if memory_output is not None and not memory_output.is_absolute():
        memory_output = ROOT / memory_output
    print(json.dumps(generate(output, memory_output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

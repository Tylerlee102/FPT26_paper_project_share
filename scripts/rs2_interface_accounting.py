"""Generate logical command-payload accounting for BF16 and RS2/R3 kernels."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.evidence_source_snapshot import describe_source_files


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_encoded_candidate_preregistration.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "benchmark"
    / "corrected"
    / "rs2_interface_accounting.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def generate(output: Path) -> dict[str, object]:
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    if registration.get("registration_status") != "PASS":
        raise ValueError("selected RS2 registration is not PASS")
    config = registration["controlled_configuration"]
    qk_heads = int(config["num_qk_heads"])
    value_heads = int(config["num_value_heads"])
    key_dim = int(config["key_dim"])
    value_dim = int(config["value_dim"])
    block = int(config["activation_block_size"])
    stack = int(config["activation_stack_depth"])
    qk_blocks = key_dim // block
    value_blocks = value_dim // block

    bf16_step_input = (
        2 * qk_heads * key_dim * 2
        + value_heads * value_dim * 2
        + 2 * value_heads * 2
    )
    rs2_step_input = (
        2 * stack * qk_heads * key_dim * 4 // 8
        + stack * value_heads * value_dim * 4 // 8
        + 2 * stack * qk_heads * qk_blocks
        + stack * value_heads * value_blocks
        + 2 * value_heads * 2
    )
    bf16_step_output = value_heads * value_dim * 2
    rs2_step_output = value_heads * value_dim * (4 + 2)
    logical = registration["logical_state_bytes"]
    report = {
        "schema": 1,
        "status": "PASS",
        "scope": "logical command payloads before AXI packing for matched BF16 and selected RS2/R3 recurrence-core kernels",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "num_qk_heads": qk_heads,
            "num_value_heads": value_heads,
            "key_dim": key_dim,
            "value_dim": value_dim,
            "block_size": block,
            "activation_stack_depth": stack,
            "coefficient_bytes": 2,
            "bf16_bytes": 2,
            "e2m1_bits": 4,
            "e8m0_scale_bytes": 1,
            "rs2_output_mantissa_bytes": 4,
            "rs2_output_exponent_bytes": 2,
        },
        "commands": {
            "RESET": {
                "bf16_input_bytes": 0,
                "rs2_input_bytes": 0,
                "output_bytes": 0,
            },
            "LOAD": {
                "bf16_input_bytes": int(logical["uniform_bf16"]),
                "rs2_input_bytes": int(logical["encoded_candidate"]),
                "output_bytes": 0,
            },
            "STEP": {
                "bf16_input_bytes": bf16_step_input,
                "rs2_input_bytes": rs2_step_input,
                "bf16_output_bytes": bf16_step_output,
                "rs2_output_bytes": rs2_step_output,
            },
            "READBACK": {
                "input_bytes": 0,
                "bf16_output_bytes": int(logical["uniform_bf16"]),
                "rs2_output_bytes": int(logical["encoded_candidate"]),
            },
        },
        "formulas": {
            "bf16_step_input": "2*(QK_HEADS*KEY_DIM*2 bytes) + VALUE_HEADS*VALUE_DIM*2 bytes + 2*VALUE_HEADS*2-byte coefficients",
            "rs2_step_input": "q+k+v two-term E2M1 payloads + one E8M0 byte per B32 term block + alpha/beta Q1.15",
            "bf16_step_output": "VALUE_HEADS*VALUE_DIM*2 bytes",
            "rs2_step_output": "VALUE_HEADS*VALUE_DIM*(INT32 mantissa + INT16 exponent)",
        },
        "source_sha256": {
            REGISTRATION.relative_to(ROOT).as_posix(): _sha256(REGISTRATION),
        },
        "source_identity": describe_source_files(
            [
                Path(__file__).resolve(),
                ROOT / "hls" / "rs2" / "include" / "gdn_rs2_kernel.hpp",
                ROOT / "hls" / "rs2" / "src" / "gdn_rs2_top.cpp",
                ROOT / "hls" / "bf16" / "include" / "gdn_bf16_kernel.hpp",
            ]
        ),
        "limitations": [
            "logical type-layout accounting before AXI beat padding, host packing, or protocol overhead",
            "not measured PCIe, HBM, or board traffic",
            "persistent STEP does not transfer recurrent state",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = generate(_resolve(args.output))
    print(json.dumps({"status": report["status"], "output": str(_resolve(args.output))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

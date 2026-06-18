"""Golden reference models for the Gated DeltaNet FPGA project."""

from .gdn_fp32 import gdn_decode_step, ungated_decode_step

__all__ = ["gdn_decode_step", "ungated_decode_step"]


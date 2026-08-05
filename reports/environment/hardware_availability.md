# Local Hardware Availability

Generated: `2026-08-05T16:47:17.125136+00:00` on `Tyler`.

| Experiment prerequisite | Status | Observation |
|---|---|---|
| Vitis HLS and Vivado | AVAILABLE | HLS: `C:\AMDDesignTools\2025.2\Vitis\bin\unwrapped\win64.o\vitis_hls.exe`; Vivado: `C:\AMDDesignTools\2025.2\Vivado\bin\vivado.bat` |
| U55C board parity and telemetry | BLOCKED_EXTERNAL_NO_U55C_DEVICE_OR_XRT | PCI device: `False`; U55C platforms: `0`; xbutil: `None`; xrt-smi: `None` |
| Native-FP4 GPU baseline | BLOCKED_EXTERNAL_NO_NATIVE_FP4_GPU | NVIDIA GeForce RTX 3070 (CC 8.6, 8192 MiB) |

The installed synthesis tools support HLS and out-of-context Vivado experiments. They do not substitute for an attached U55C, XRT platform, or board telemetry. Likewise, a detected pre-native-FP4 GPU cannot provide the requested matched native-FP4 GPU baseline. These two measurements remain externally blocked and are not represented by estimates.

# Corrected HLS Command Trace Format

The binary file `data/vectors/corrected_gdn_command_trace.bin` is the frozen
software-oracle input to corrected HLS C simulation and RTL cosimulation. All
integers are little-endian and arrays use C row-major order.

## Header

```text
char[8] magic = "GDNTRC01"
uint32 version = 1
uint32 endian_marker = 0x01020304
uint32 token_count
uint32 num_qk_heads
uint32 num_value_heads
uint32 key_dim
uint32 value_dim
uint32 block_size
```

## Token Record

Each token contains, in order:

```text
uint8  q_elements[16][128]
uint8  q_scales[16][4]
uint8  k_elements[16][128]
uint8  k_scales[16][4]
uint8  v_elements[32][128]
uint8  v_scales[32][4]
uint16 alpha_codes[32]
uint16 beta_codes[32]
uint8  expected_status
uint64 expected_generation
uint64 expected_command_counters[8]
uint64 expected_cumulative_counters[8]
int32  expected_output_mantissas[32][128]
int16  expected_output_exponents[32][128]
```

Counter order is element saturation, accumulator saturation, scale clamp,
alignment underflow, state-scale change, invalid encoding, rejected command,
and committed state generation.

## Final Readback

After all token records:

```text
uint8  expected_state_elements[32][128][128]
uint8  expected_state_scales[32][128][4]
uint8  expected_readback_status
uint64 expected_readback_generation
uint64 expected_readback_cumulative_counters[8]
```

The generator manifest records the seed, dimensions, source hashes, input-stream
hash, complete binary hash, runtime versions, and final counters. The C++
testbench must reject a header mismatch, short read, trailing byte, output or
counter difference, or final state difference.

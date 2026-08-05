#include "gdn_kernel.hpp"

#include <cstdint>

#include "block_exp_align.hpp"
#include "mac_e2m1.hpp"

namespace gdn {

namespace {

std::uint64_t magnitude_u32(mantissa_t value) {
#pragma HLS INLINE
  return value < 0
      ? static_cast<std::uint64_t>(
            -static_cast<wide_mantissa_t>(value))
      : static_cast<std::uint64_t>(value);
}

int bit_length(std::uint64_t value) {
#pragma HLS INLINE
  if (value == 0) {
    return 0;
  }
  int bits = 1;
  if (value >= (static_cast<std::uint64_t>(1) << 32)) {
    value >>= 32;
    bits += 32;
  }
  if (value >= (static_cast<std::uint64_t>(1) << 16)) {
    value >>= 16;
    bits += 16;
  }
  if (value >= (static_cast<std::uint64_t>(1) << 8)) {
    value >>= 8;
    bits += 8;
  }
  if (value >= (static_cast<std::uint64_t>(1) << 4)) {
    value >>= 4;
    bits += 4;
  }
  if (value >= (static_cast<std::uint64_t>(1) << 2)) {
    value >>= 2;
    bits += 2;
  }
  if (value >= (static_cast<std::uint64_t>(1) << 1)) {
    bits += 1;
  }
  return bits;
}

bool greater_abs_scaled(
    mantissa_t left_mantissa,
    exponent_t left_exponent,
    mantissa_t right_mantissa,
    exponent_t right_exponent) {
#pragma HLS INLINE
  const std::uint64_t left = magnitude_u32(left_mantissa);
  const std::uint64_t right = magnitude_u32(right_mantissa);
  if (right == 0) {
    return left != 0;
  }
  if (left == 0) {
    return false;
  }
  const int left_top = static_cast<int>(left_exponent) + bit_length(left) - 1;
  const int right_top = static_cast<int>(right_exponent) + bit_length(right) - 1;
  if (left_top != right_top) {
    return left_top > right_top;
  }
  const int common =
      left_exponent < right_exponent ? left_exponent : right_exponent;
  const std::uint64_t left_aligned =
      left << (static_cast<int>(left_exponent) - common);
  const std::uint64_t right_aligned =
      right << (static_cast<int>(right_exponent) - common);
  return left_aligned > right_aligned;
}

bool exceeds_e2m1_max(
    mantissa_t mantissa,
    exponent_t exponent,
    int scale_power) {
#pragma HLS INLINE
  return greater_abs_scaled(
      mantissa,
      exponent,
      static_cast<mantissa_t>(12),
      static_cast<exponent_t>(scale_power - 1));
}

int select_scale_power(
    const mantissa_t mantissas[BLOCK_SIZE],
    const exponent_t exponents[BLOCK_SIZE],
    command_counter_array_t counters) {
#pragma HLS INLINE
  constexpr int EMPTY_SCALE = -32768;
  constexpr int REDUCTION_WIDTH = 32;
  int lane_scales[REDUCTION_WIDTH];
  int reduce_16[16];
  int reduce_8[8];
  int reduce_4[4];
  int reduce_2[2];
#pragma HLS ARRAY_PARTITION variable=lane_scales complete dim=1
#pragma HLS ARRAY_PARTITION variable=reduce_16 complete dim=1
#pragma HLS ARRAY_PARTITION variable=reduce_8 complete dim=1
#pragma HLS ARRAY_PARTITION variable=reduce_4 complete dim=1
#pragma HLS ARRAY_PARTITION variable=reduce_2 complete dim=1

scale_candidates:
  for (int lane = 0; lane < REDUCTION_WIDTH; ++lane) {
#pragma HLS UNROLL
    int required_scale = EMPTY_SCALE;
    if (lane < BLOCK_SIZE && mantissas[lane] != 0) {
      required_scale = static_cast<int>(exponents[lane]) +
                       bit_length(magnitude_u32(mantissas[lane])) - 3;
      if (exceeds_e2m1_max(
              mantissas[lane], exponents[lane], required_scale)) {
        ++required_scale;
      }
    }
    lane_scales[lane] = required_scale;
  }
reduce_scale_16:
  for (int index = 0; index < 16; ++index) {
#pragma HLS UNROLL
    reduce_16[index] = lane_scales[2 * index] > lane_scales[2 * index + 1]
        ? lane_scales[2 * index]
        : lane_scales[2 * index + 1];
  }
reduce_scale_8:
  for (int index = 0; index < 8; ++index) {
#pragma HLS UNROLL
    reduce_8[index] = reduce_16[2 * index] > reduce_16[2 * index + 1]
        ? reduce_16[2 * index]
        : reduce_16[2 * index + 1];
  }
reduce_scale_4:
  for (int index = 0; index < 4; ++index) {
#pragma HLS UNROLL
    reduce_4[index] = reduce_8[2 * index] > reduce_8[2 * index + 1]
        ? reduce_8[2 * index]
        : reduce_8[2 * index + 1];
  }
reduce_scale_2:
  for (int index = 0; index < 2; ++index) {
#pragma HLS UNROLL
    reduce_2[index] = reduce_4[2 * index] > reduce_4[2 * index + 1]
        ? reduce_4[2 * index]
        : reduce_4[2 * index + 1];
  }
  int scale_power = reduce_2[0] > reduce_2[1] ? reduce_2[0] : reduce_2[1];
  if (scale_power == EMPTY_SCALE) {
    return 0;
  }
  if (scale_power < -127) {
    ++counters[COUNTER_SCALE_CLAMPS];
    return -127;
  }
  if (scale_power > 127) {
    ++counters[COUNTER_SCALE_CLAMPS];
    return 127;
  }
  return scale_power;
}

mx_e2m1_t quantize_exact_e2m1(
    mantissa_t mantissa,
    exponent_t exponent,
    int scale_power,
    command_counter_array_t counters) {
#pragma HLS INLINE
  if (mantissa == 0) {
    return static_cast<mx_e2m1_t>(0);
  }
  const bool negative = mantissa < 0;
  const std::uint64_t magnitude = magnitude_u32(mantissa);
  const int element_exponent = scale_power - 1;

  if (exceeds_e2m1_max(mantissa, exponent, scale_power)) {
    ++counters[COUNTER_ELEMENT_SATURATIONS];
    return static_cast<mx_e2m1_t>((negative ? 0x08u : 0u) | 0x07u);
  }

  static const std::uint8_t candidate_magnitudes[8] =
      {0, 1, 2, 3, 4, 6, 8, 12};
#pragma HLS ARRAY_PARTITION variable=candidate_magnitudes complete dim=1
  std::uint64_t value_integer = magnitude;
  std::uint64_t candidate_scale = 1;
  if (static_cast<int>(exponent) >= element_exponent) {
    const int shift = static_cast<int>(exponent) - element_exponent;
    value_integer = magnitude << shift;
  } else {
    const int shift = element_exponent - static_cast<int>(exponent);
    if (shift >= 33) {
      return static_cast<mx_e2m1_t>(0);
    }
    candidate_scale = static_cast<std::uint64_t>(1) << shift;
  }

  unsigned best_code = 0;
  std::uint64_t best_distance = ~static_cast<std::uint64_t>(0);
select_quantized_code:
  for (unsigned code = 0; code < 8; ++code) {
#pragma HLS UNROLL
    const std::uint64_t candidate =
        static_cast<std::uint64_t>(candidate_magnitudes[code]) *
        candidate_scale;
    const std::uint64_t distance = value_integer >= candidate
        ? value_integer - candidate
        : candidate - value_integer;
    if (distance < best_distance ||
        (distance == best_distance && (code & 1u) == 0u &&
         (best_code & 1u) != 0u)) {
      best_code = code;
      best_distance = distance;
    }
  }
  if (best_code == 0) {
    return static_cast<mx_e2m1_t>(0);
  }
  return static_cast<mx_e2m1_t>((negative ? 0x08u : 0u) | best_code);
}

}  // namespace

void phase4_update_state_tile(
    const qk_head_t k,
    const qk_head_scales_t k_scales,
    const block_mantissa_t delta_mantissas,
    const block_exponent_t delta_exponents,
    const tile_mantissa_t decayed_mantissas,
    const tile_exponent_t decayed_exponents,
    state_block_tile_t state,
    state_scale_tile_t state_scales,
    tile_mantissa_t updated_mantissas,
    tile_exponent_t updated_exponents,
    command_counter_array_t counters) {
update_rows:
  for (int row = 0; row < KEY_DIM; ++row) {
    mantissa_t row_mantissas[BLOCK_SIZE];
    exponent_t row_exponents[BLOCK_SIZE];
    std::uint8_t alignment_underflows = 0;
#pragma HLS ARRAY_PARTITION variable=row_mantissas cyclic factor=P_V dim=1
#pragma HLS ARRAY_PARTITION variable=row_exponents cyclic factor=P_V dim=1
  update_lanes:
    for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
      const wide_mantissa_t write_mantissa =
          scale_by_e2m1(k[row], delta_mantissas[lane]);
      const exponent_t write_exponent = static_cast<exponent_t>(
          static_cast<int>(decode_e2m1_exponent(
              k_scales[row / BLOCK_SIZE])) +
          static_cast<int>(delta_exponents[lane]));
      bool alignment_underflow = false;
      const aligned_value_t updated = aligned_pair(
          decayed_mantissas[row][lane],
          decayed_exponents[row][lane],
          write_mantissa,
          write_exponent,
          alignment_underflow,
          counters);
      alignment_underflows += static_cast<std::uint8_t>(alignment_underflow);
      row_mantissas[lane] = updated.mantissa;
      row_exponents[lane] = updated.exponent;
      updated_mantissas[row][lane] = updated.mantissa;
      updated_exponents[row][lane] = updated.exponent;
    }
    counters[COUNTER_ALIGNMENT_UNDERFLOWS] += alignment_underflows;

    const int scale_power =
        select_scale_power(row_mantissas, row_exponents, counters);
    const unsigned scale_code = static_cast<unsigned>(scale_power + E8M0_BIAS);
    if (to_u8(state_scales[row]) != scale_code) {
      ++counters[COUNTER_STATE_SCALE_CHANGES];
    }
    state_scales[row] = static_cast<mx_scale_t>(scale_code);
  requantize_lanes:
    for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
      state[row][lane] = quantize_exact_e2m1(
          row_mantissas[lane], row_exponents[lane], scale_power, counters);
    }
  }
}

}  // namespace gdn

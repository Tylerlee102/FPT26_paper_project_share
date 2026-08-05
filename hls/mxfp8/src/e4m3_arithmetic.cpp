#include "e4m3_arithmetic.hpp"

#include <cstdint>

#include "block_exp_align.hpp"

namespace gdn_mxfp8 {

namespace {

std::uint64_t magnitude_u32(mantissa_t value) {
#pragma HLS INLINE
  return value < 0
      ? static_cast<std::uint64_t>(-static_cast<wide_mantissa_t>(value))
      : static_cast<std::uint64_t>(value);
}

int bit_length(std::uint64_t value) {
#pragma HLS INLINE
  if (value == 0) {
    return 0;
  }
  int bits = 1;
  if (value >= (static_cast<std::uint64_t>(1) << 32)) { value >>= 32; bits += 32; }
  if (value >= (static_cast<std::uint64_t>(1) << 16)) { value >>= 16; bits += 16; }
  if (value >= (static_cast<std::uint64_t>(1) << 8)) { value >>= 8; bits += 8; }
  if (value >= (static_cast<std::uint64_t>(1) << 4)) { value >>= 4; bits += 4; }
  if (value >= (static_cast<std::uint64_t>(1) << 2)) { value >>= 2; bits += 2; }
  if (value >= (static_cast<std::uint64_t>(1) << 1)) { bits += 1; }
  return bits;
}

bool greater_abs_scaled(
    mantissa_t left_mantissa, exponent_t left_exponent,
    mantissa_t right_mantissa, exponent_t right_exponent) {
#pragma HLS INLINE
  const std::uint64_t left = magnitude_u32(left_mantissa);
  const std::uint64_t right = magnitude_u32(right_mantissa);
  if (right == 0) return left != 0;
  if (left == 0) return false;
  const int left_top = static_cast<int>(left_exponent) + bit_length(left) - 1;
  const int right_top = static_cast<int>(right_exponent) + bit_length(right) - 1;
  if (left_top != right_top) return left_top > right_top;
  const int common = left_exponent < right_exponent ? left_exponent : right_exponent;
  const int left_shift = static_cast<int>(left_exponent) - common;
  const int right_shift = static_cast<int>(right_exponent) - common;
  if (left_shift >= 64) return true;
  if (right_shift >= 64) return false;
  return (left << left_shift) > (right << right_shift);
}

bool exceeds_e4m3_max(mantissa_t mantissa, exponent_t exponent, int scale_power) {
#pragma HLS INLINE
  return greater_abs_scaled(
      mantissa, exponent, static_cast<mantissa_t>(14),
      static_cast<exponent_t>(scale_power + 5));
}

std::uint64_t rounded_grid_magnitude(
    std::uint64_t magnitude, int exponent, int grid_exponent) {
#pragma HLS INLINE
  const int shift = exponent - grid_exponent;
  if (shift >= 0) {
    if (shift >= 63 || magnitude > (~static_cast<std::uint64_t>(0) >> shift)) {
      return ~static_cast<std::uint64_t>(0);
    }
    return magnitude << shift;
  }
  return static_cast<std::uint64_t>(gdn::round_shift_rne(
      static_cast<wide_mantissa_t>(magnitude), -shift));
}

}  // namespace

unsigned raw_e4m3(mx_element_t value) {
#pragma HLS INLINE
  return static_cast<unsigned>(value) & 0xffu;
}

bool valid_e4m3(mx_element_t value) {
#pragma HLS INLINE
  const unsigned code = raw_e4m3(value);
  return code != 0x7fu && code != 0x80u && code != 0xffu;
}

mantissa_t decode_e4m3_mantissa(mx_element_t value) {
#pragma HLS INLINE
  const unsigned code = raw_e4m3(value);
  const unsigned exponent_field = (code >> 3) & 0x0fu;
  const unsigned fraction = code & 0x07u;
  const mantissa_t magnitude = exponent_field == 0u
      ? static_cast<mantissa_t>(fraction)
      : static_cast<mantissa_t>(8u + fraction);
  return ((code & 0x80u) != 0u && magnitude != 0) ? -magnitude : magnitude;
}

exponent_t decode_e4m3_exponent(mx_element_t value, mx_scale_t scale) {
#pragma HLS INLINE
  const unsigned exponent_field = (raw_e4m3(value) >> 3) & 0x0fu;
  const int scale_power = static_cast<int>(gdn::to_u8(scale)) - E8M0_BIAS;
  return static_cast<exponent_t>(
      scale_power + (exponent_field == 0u ? -9 : static_cast<int>(exponent_field) - 10));
}

wide_mantissa_t scale_by_e4m3(mx_element_t coefficient, mantissa_t value) {
#pragma HLS INLINE
  const mantissa_t decoded = decode_e4m3_mantissa(coefficient);
  const bool negative = decoded < 0;
  const unsigned magnitude = static_cast<unsigned>(negative ? -decoded : decoded);
  const wide_mantissa_t x = static_cast<wide_mantissa_t>(value);
  wide_mantissa_t product = 0;
  if ((magnitude & 1u) != 0u) product += x;
  if ((magnitude & 2u) != 0u) product += x << 1;
  if ((magnitude & 4u) != 0u) product += x << 2;
  if ((magnitude & 8u) != 0u) product += x << 3;
  return negative ? -product : product;
}

int select_scale_power_e4m3(
    const mantissa_t mantissas[BLOCK_SIZE],
    const exponent_t exponents[BLOCK_SIZE],
    command_counter_array_t counters) {
#pragma HLS INLINE
  constexpr int EMPTY_SCALE = -32768;
  int scale_power = EMPTY_SCALE;
select_e4m3_scale:
  for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS UNROLL
    if (mantissas[lane] == 0) continue;
    int required = static_cast<int>(exponents[lane])
        + bit_length(magnitude_u32(mantissas[lane])) - 9;
    if (exceeds_e4m3_max(mantissas[lane], exponents[lane], required)) {
      ++required;
    }
    if (required > scale_power) scale_power = required;
  }
  if (scale_power == EMPTY_SCALE) return 0;
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

mx_element_t quantize_exact_e4m3(
    mantissa_t mantissa,
    exponent_t exponent,
    int scale_power,
    command_counter_array_t counters) {
#pragma HLS INLINE
  if (mantissa == 0) return static_cast<mx_element_t>(0);
  const bool negative = mantissa < 0;
  const std::uint64_t magnitude = magnitude_u32(mantissa);
  if (exceeds_e4m3_max(mantissa, exponent, scale_power)) {
    ++counters[COUNTER_ELEMENT_SATURATIONS];
    return static_cast<mx_element_t>((negative ? 0x80u : 0u) | 0x7eu);
  }

  const int top_power = static_cast<int>(exponent) - scale_power
      + bit_length(magnitude) - 1;
  unsigned magnitude_code = 0;
  if (top_power < -6) {
    const std::uint64_t rounded = rounded_grid_magnitude(
        magnitude, static_cast<int>(exponent), scale_power - 9);
    magnitude_code = rounded >= 8u ? 0x08u : static_cast<unsigned>(rounded);
  } else {
    int exponent_field = top_power + 7;
    if (exponent_field < 1) exponent_field = 1;
    if (exponent_field > 15) exponent_field = 15;
    std::uint64_t significand = rounded_grid_magnitude(
        magnitude, static_cast<int>(exponent), scale_power + exponent_field - 10);
    if (significand >= 16u) {
      ++exponent_field;
      significand = 8u;
    }
    if (exponent_field > 15 || (exponent_field == 15 && significand > 14u)) {
      ++counters[COUNTER_ELEMENT_SATURATIONS];
      magnitude_code = 0x7eu;
    } else {
      if (significand < 8u) significand = 8u;
      magnitude_code = static_cast<unsigned>((exponent_field << 3) | (significand - 8u));
    }
  }
  if (magnitude_code == 0u) return static_cast<mx_element_t>(0);
  return static_cast<mx_element_t>((negative ? 0x80u : 0u) | magnitude_code);
}

}  // namespace gdn_mxfp8

#include "gdn_rs2_kernel.hpp"

namespace gdn_rs2 {

namespace {

ap_uint<32> magnitude32(mantissa_t value) {
#pragma HLS INLINE
  return value < 0
      ? static_cast<ap_uint<32>>(-static_cast<ap_int<33>>(value))
      : static_cast<ap_uint<32>>(value);
}

int bit_length32(ap_uint<32> value) {
#pragma HLS INLINE
  if (value == 0) {
    return 0;
  }
  int length = 0;
bit_length_loop:
  for (int bit = 31; bit >= 0; --bit) {
#pragma HLS UNROLL
    if (length == 0 && value[bit]) {
      length = bit + 1;
    }
  }
  return length;
}

bool greater_abs_scaled(
    mantissa_t left_mantissa,
    exponent_t left_exponent,
    mantissa_t right_mantissa,
    exponent_t right_exponent) {
#pragma HLS INLINE
  const ap_uint<32> left = magnitude32(left_mantissa);
  const ap_uint<32> right = magnitude32(right_mantissa);
  if (right == 0) {
    return left != 0;
  }
  if (left == 0) {
    return false;
  }
  const int left_top = static_cast<int>(left_exponent) + bit_length32(left) - 1;
  const int right_top = static_cast<int>(right_exponent) + bit_length32(right) - 1;
  if (left_top != right_top) {
    return left_top > right_top;
  }
  const int common = left_exponent < right_exponent
      ? static_cast<int>(left_exponent)
      : static_cast<int>(right_exponent);
  const ap_uint<64> left_aligned =
      static_cast<ap_uint<64>>(left) <<
      (static_cast<int>(left_exponent) - common);
  const ap_uint<64> right_aligned =
      static_cast<ap_uint<64>>(right) <<
      (static_cast<int>(right_exponent) - common);
  return left_aligned > right_aligned;
}

int compare_nonnegative_scaled(
    ap_uint<33> left_magnitude,
    int left_exponent,
    ap_uint<33> right_magnitude,
    int right_exponent) {
#pragma HLS INLINE
  if (left_magnitude == 0 || right_magnitude == 0) {
    if (left_magnitude == right_magnitude) {
      return 0;
    }
    return left_magnitude == 0 ? -1 : 1;
  }
  int left_bits = 0;
  int right_bits = 0;
compare_scaled_bits:
  for (int bit = 32; bit >= 0; --bit) {
#pragma HLS UNROLL
    if (left_bits == 0 && left_magnitude[bit]) {
      left_bits = bit + 1;
    }
    if (right_bits == 0 && right_magnitude[bit]) {
      right_bits = bit + 1;
    }
  }
  const int left_top = left_exponent + left_bits - 1;
  const int right_top = right_exponent + right_bits - 1;
  if (left_top != right_top) {
    return left_top < right_top ? -1 : 1;
  }
  const int common = left_exponent < right_exponent
      ? left_exponent
      : right_exponent;
  const ap_uint<65> left =
      static_cast<ap_uint<65>>(left_magnitude) << (left_exponent - common);
  const ap_uint<65> right =
      static_cast<ap_uint<65>>(right_magnitude) << (right_exponent - common);
  if (left == right) {
    return 0;
  }
  return left < right ? -1 : 1;
}

bool exceeds_magnitude(
    mantissa_t mantissa,
    exponent_t exponent,
    int candidate_magnitude,
    int candidate_exponent) {
#pragma HLS INLINE
  if (mantissa == 0) {
    return false;
  }
  const int value_top = static_cast<int>(exponent) +
                        bit_length32(magnitude32(mantissa)) - 1;
  int candidate_bits = 0;
  int temporary = candidate_magnitude;
  while (temporary != 0) {
    ++candidate_bits;
    temporary >>= 1;
  }
  const int candidate_top = candidate_exponent + candidate_bits - 1;
  if (value_top != candidate_top) {
    return value_top > candidate_top;
  }
  const int common = static_cast<int>(exponent) < candidate_exponent
      ? static_cast<int>(exponent)
      : candidate_exponent;
  const ap_uint<128> value =
      static_cast<ap_uint<128>>(magnitude32(mantissa)) <<
      (static_cast<int>(exponent) - common);
  const ap_uint<128> candidate =
      static_cast<ap_uint<128>>(candidate_magnitude) <<
      (candidate_exponent - common);
  return value > candidate;
}

}  // namespace

mantissa_t decode_e2m1(e2m1_t code) {
#pragma HLS INLINE
  static const int magnitude[8] = {0, 1, 2, 3, 4, 6, 8, 12};
#pragma HLS ARRAY_PARTITION variable=magnitude complete dim=1
  const unsigned raw = static_cast<unsigned>(code);
  const mantissa_t value = magnitude[raw & 7u];
  return (raw & 8u) != 0u && value != 0
      ? static_cast<mantissa_t>(-static_cast<ap_int<33>>(value))
      : value;
}

exponent_t decode_scale(scale_t scale) {
#pragma HLS INLINE
  return static_cast<exponent_t>(static_cast<int>(scale) - 128);
}

wide_mantissa_t product_e2m1(e2m1_t left, e2m1_t right) {
#pragma HLS INLINE
  return static_cast<wide_mantissa_t>(decode_e2m1(left)) *
         static_cast<wide_mantissa_t>(decode_e2m1(right));
}

int select_e2m1_scale_power(
    const mantissa_t mantissas[gdn::BLOCK_SIZE],
    const exponent_t exponents[gdn::BLOCK_SIZE],
    counters_t counters) {
#pragma HLS INLINE off
  ap_int<17> top_exponents[gdn::BLOCK_SIZE];
  ap_uint<32> normalized_magnitudes[gdn::BLOCK_SIZE];
select_e2m1_normalize:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    const ap_uint<32> magnitude = magnitude32(mantissas[lane]);
    const int bits = bit_length32(magnitude);
    top_exponents[lane] = bits == 0
        ? ap_int<17>(0)
        : ap_int<17>(static_cast<int>(exponents[lane]) + bits - 1);
    normalized_magnitudes[lane] = bits == 0
        ? ap_uint<32>(0)
        : ap_uint<32>(magnitude << (32 - bits));
  }

  mantissa_t maximum_mantissa = 0;
  exponent_t maximum_exponent = 0;
  ap_int<17> maximum_top = 0;
  ap_uint<32> maximum_normalized = 0;
  bool found = false;
select_e2m1_max:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    const ap_uint<32> normalized = normalized_magnitudes[lane];
    const ap_int<17> top = top_exponents[lane];
    if (normalized != 0 &&
        (!found || top > maximum_top ||
         (top == maximum_top && normalized > maximum_normalized))) {
      maximum_mantissa = mantissas[lane];
      maximum_exponent = exponents[lane];
      maximum_top = top;
      maximum_normalized = normalized;
      found = true;
    }
  }
  if (!found) {
    return 0;
  }
  int power = static_cast<int>(maximum_exponent) +
              bit_length32(magnitude32(maximum_mantissa)) - 3;
  if (exceeds_magnitude(maximum_mantissa, maximum_exponent, 12, power - 1)) {
    ++power;
  }
  if (power < -127) {
    ++counters[COUNTER_SCALE_CLAMPS];
    return -127;
  }
  if (power > 127) {
    ++counters[COUNTER_SCALE_CLAMPS];
    return 127;
  }
  return power;
}

e2m1_t quantize_e2m1(
    mantissa_t mantissa,
    exponent_t exponent,
    int scale_power,
    counters_t counters) {
#pragma HLS INLINE
  if (mantissa == 0) {
    return 0;
  }
  static const int candidates[8] = {0, 1, 2, 3, 4, 6, 8, 12};
#pragma HLS ARRAY_PARTITION variable=candidates complete dim=1
  unsigned best = 7;
quantize_e2m1_boundaries:
  for (unsigned lower = 0; lower < 7; ++lower) {
#pragma HLS UNROLL
    if (best == 7) {
      const ap_uint<33> doubled_source =
          static_cast<ap_uint<33>>(magnitude32(mantissa)) << 1;
      const ap_uint<33> boundary = candidates[lower] + candidates[lower + 1];
      const int comparison = compare_nonnegative_scaled(
          doubled_source, static_cast<int>(exponent),
          boundary, scale_power - 1);
      if (comparison < 0) {
        best = lower;
      } else if (comparison == 0) {
        best = ((lower + 1u) & 1u) == 0u ? lower + 1u : lower;
      }
    }
  }
  if (exceeds_magnitude(mantissa, exponent, 12, scale_power - 1)) {
    ++counters[COUNTER_ELEMENT_SATURATIONS];
    best = 7;
  }
  if (best == 0) {
    return 0;
  }
  return static_cast<e2m1_t>(best | (mantissa < 0 ? 8u : 0u));
}

}  // namespace gdn_rs2

void rs2_arithmetic_top(
    const gdn_rs2::mantissa_t mantissas[gdn::BLOCK_SIZE],
    const gdn_rs2::exponent_t exponents[gdn::BLOCK_SIZE],
    gdn_rs2::e2m1_t primary_codes[gdn::BLOCK_SIZE],
    gdn_rs2::e2m1_t residual_codes[gdn::BLOCK_SIZE],
    gdn_rs2::exponent_t scale_powers_out[2],
    gdn_rs2::mantissa_t aligned_mantissa_out[1],
    gdn_rs2::exponent_t aligned_exponent_out[1],
    gdn_rs2::counters_t counters_out) {
  using namespace gdn_rs2;
clear_arithmetic_counters:
  for (int index = 0; index < COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    counters_out[index] = 0;
  }

  wide_mantissa_t widened[gdn::BLOCK_SIZE];
#pragma HLS ARRAY_PARTITION variable=widened cyclic factor=gdn::P_K dim=1
widen_arithmetic_inputs:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    widened[lane] = mantissas[lane];
  }
  const aligned_t aligned = aligned_sum_guarded<gdn::BLOCK_SIZE>(
      widened, exponents, counters_out);
  aligned_mantissa_out[0] = aligned.mantissa;
  aligned_exponent_out[0] = aligned.exponent;

  const int primary_power = select_e2m1_scale_power(
      mantissas, exponents, counters_out);
  mantissa_t residual_m[gdn::BLOCK_SIZE];
  exponent_t residual_x[gdn::BLOCK_SIZE];
quantize_primary:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    const e2m1_t code = quantize_e2m1(
        mantissas[lane], exponents[lane], primary_power, counters_out);
    primary_codes[lane] = code;
    const wide_mantissa_t terms[2] = {
        mantissas[lane], -static_cast<wide_mantissa_t>(decode_e2m1(code))};
    const exponent_t term_x[2] = {
        exponents[lane], static_cast<exponent_t>(primary_power - 1)};
    const aligned_t residual = aligned_sum_guarded<2>(
        terms, term_x, counters_out);
    residual_m[lane] = residual.mantissa;
    residual_x[lane] = residual.exponent;
  }

  const int residual_power = select_e2m1_scale_power(
      residual_m, residual_x, counters_out);
quantize_residual:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    residual_codes[lane] = quantize_e2m1(
        residual_m[lane], residual_x[lane], residual_power, counters_out);
  }
  scale_powers_out[0] = primary_power;
  scale_powers_out[1] = residual_power;
}

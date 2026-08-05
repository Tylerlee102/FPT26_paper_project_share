#include "block_exp_align.hpp"

#include <climits>
#include <cstdint>

namespace gdn {

wide_mantissa_t round_shift_rne(wide_mantissa_t value, int shift) {
#pragma HLS INLINE
  if (shift <= 0 || value == 0) {
    return value;
  }
  const bool negative = value < 0;
  const std::uint64_t magnitude = negative
      ? static_cast<std::uint64_t>(-(value + 1)) + 1u
      : static_cast<std::uint64_t>(value);
  if (shift >= 64) {
    return 0;
  }
  std::uint64_t quotient = magnitude >> shift;
  const std::uint64_t mask = (static_cast<std::uint64_t>(1) << shift) - 1u;
  const std::uint64_t remainder = magnitude & mask;
  const std::uint64_t halfway = static_cast<std::uint64_t>(1) << (shift - 1);
  if (remainder > halfway ||
      (remainder == halfway && (quotient & 1u) != 0u)) {
    ++quotient;
  }
  const wide_mantissa_t rounded = static_cast<wide_mantissa_t>(quotient);
  return negative ? -rounded : rounded;
}

mantissa_t saturate_int32(
    wide_mantissa_t value,
    command_counter_t counters[COUNTER_COUNT]) {
#pragma HLS INLINE
  if (value > static_cast<wide_mantissa_t>(INT32_MAX)) {
    ++counters[COUNTER_ACCUMULATOR_SATURATIONS];
    return INT32_MAX;
  }
  if (value < static_cast<wide_mantissa_t>(INT32_MIN)) {
    ++counters[COUNTER_ACCUMULATOR_SATURATIONS];
    return INT32_MIN;
  }
  return static_cast<mantissa_t>(value);
}

mantissa_t multiply_q1_15(
    mantissa_t value,
    q1_15_t coefficient,
    command_counter_t counters[COUNTER_COUNT]) {
#pragma HLS INLINE
  const wide_mantissa_t product =
      static_cast<wide_mantissa_t>(value) *
      static_cast<wide_mantissa_t>(coefficient);
  return saturate_int32(round_shift_rne(product, 15), counters);
}

aligned_value_t aligned_sum(
    const wide_mantissa_t mantissas[KEY_DIM],
    const exponent_t exponents[KEY_DIM],
    int count,
    command_counter_t counters[COUNTER_COUNT]) {
#pragma HLS INLINE off
  bool found_nonzero = false;
  exponent_t dominant_exponent = 0;
find_dominant:
  for (int index = 0; index < count; ++index) {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=1 max=128
    if (mantissas[index] != 0 &&
        (!found_nonzero || exponents[index] > dominant_exponent)) {
      dominant_exponent = exponents[index];
      found_nonzero = true;
    }
  }
  if (!found_nonzero) {
    return {0, 0};
  }

  mantissa_t accumulator = 0;
align_and_sum:
  for (int index = 0; index < count; ++index) {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=1 max=128
    const wide_mantissa_t raw = mantissas[index];
    if (raw == 0) {
      continue;
    }
    const int shift = static_cast<int>(dominant_exponent) -
                      static_cast<int>(exponents[index]);
    const wide_mantissa_t aligned = round_shift_rne(raw, shift);
    if (aligned == 0 && shift > 0) {
      ++counters[COUNTER_ALIGNMENT_UNDERFLOWS];
    }
    accumulator = saturate_int32(
        static_cast<wide_mantissa_t>(accumulator) + aligned, counters);
  }
  return {accumulator, dominant_exponent};
}

aligned_value_t aligned_pair(
    wide_mantissa_t first_mantissa,
    exponent_t first_exponent,
    wide_mantissa_t second_mantissa,
    exponent_t second_exponent,
    bool& alignment_underflow,
    command_counter_t counters[COUNTER_COUNT]) {
#pragma HLS INLINE
  alignment_underflow = false;
  if (first_mantissa == 0 && second_mantissa == 0) {
    return {0, 0};
  }
  exponent_t dominant_exponent = first_mantissa != 0
      ? first_exponent
      : second_exponent;
  if (second_mantissa != 0 && second_exponent > dominant_exponent) {
    dominant_exponent = second_exponent;
  }

  mantissa_t accumulator = 0;
  if (first_mantissa != 0) {
    const int shift = static_cast<int>(dominant_exponent) -
                      static_cast<int>(first_exponent);
    const wide_mantissa_t aligned = round_shift_rne(first_mantissa, shift);
    if (aligned == 0 && shift > 0) {
      alignment_underflow = true;
    }
    accumulator = saturate_int32(aligned, counters);
  }
  if (second_mantissa != 0) {
    const int shift = static_cast<int>(dominant_exponent) -
                      static_cast<int>(second_exponent);
    const wide_mantissa_t aligned = round_shift_rne(second_mantissa, shift);
    if (aligned == 0 && shift > 0) {
      alignment_underflow = true;
    }
    accumulator = saturate_int32(
        static_cast<wide_mantissa_t>(accumulator) + aligned, counters);
  }
  return {accumulator, dominant_exponent};
}

}  // namespace gdn

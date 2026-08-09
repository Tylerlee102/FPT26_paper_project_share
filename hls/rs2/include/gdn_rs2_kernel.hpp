#pragma once

#include <ap_int.h>
#include <climits>
#include <cstdint>

#include "gdn_params.hpp"

namespace gdn_rs2 {

constexpr int STACK_DEPTH = 2;
constexpr int LOG_CAPACITY = 3;
constexpr int ACCUMULATOR_GUARD_BITS = 5;
constexpr int E8M0_BIAS = 127;
constexpr int COEFFICIENT_ONE = 32768;

using e2m1_t = ap_uint<4>;
using scale_t = ap_uint<8>;
using coefficient_t = ap_uint<16>;
using mantissa_t = ap_int<32>;
using wide_mantissa_t = ap_int<64>;
using exponent_t = ap_int<16>;
using counter_t = ap_uint<64>;
using generation_t = ap_uint<64>;

enum CounterIndex : int {
  COUNTER_ELEMENT_SATURATIONS = 0,
  COUNTER_ACCUMULATOR_SATURATIONS = 1,
  COUNTER_SCALE_CLAMPS = 2,
  COUNTER_ALIGNMENT_UNDERFLOWS = 3,
  COUNTER_STATE_SCALE_CHANGES = 4,
  COUNTER_FOLDS = 5,
  COUNTER_COMMITTED_GENERATIONS = 6,
  COUNTER_COUNT = 7,
};

struct aligned_t {
  mantissa_t mantissa;
  exponent_t exponent;
};

using qk_elements_t =
    e2m1_t[STACK_DEPTH][gdn::NUM_QK_HEADS][gdn::KEY_DIM];
using qk_scales_t =
    scale_t[STACK_DEPTH][gdn::NUM_QK_HEADS][gdn::QK_BLOCKS];
using value_elements_t =
    e2m1_t[STACK_DEPTH][gdn::NUM_VALUE_HEADS][gdn::VALUE_DIM];
using value_scales_t =
    scale_t[STACK_DEPTH][gdn::NUM_VALUE_HEADS][gdn::VALUE_BLOCKS];
using coefficient_heads_t = coefficient_t[gdn::NUM_VALUE_HEADS];
using output_mantissas_t = mantissa_t[gdn::NUM_VALUE_HEADS][gdn::VALUE_DIM];
using output_exponents_t = exponent_t[gdn::NUM_VALUE_HEADS][gdn::VALUE_DIM];
using counters_t = counter_t[COUNTER_COUNT];
using state_primary_elements_t =
    e2m1_t[gdn::NUM_VALUE_HEADS][gdn::KEY_DIM][gdn::VALUE_DIM];
using state_residual_elements_t =
    e2m1_t[gdn::NUM_VALUE_HEADS][gdn::KEY_DIM][gdn::VALUE_DIM];
using state_scales_t =
    scale_t[gdn::NUM_VALUE_HEADS][gdn::KEY_DIM][gdn::VALUE_BLOCKS];
using log_key_elements_t =
    e2m1_t[LOG_CAPACITY][STACK_DEPTH][gdn::NUM_QK_HEADS][gdn::KEY_DIM];
using log_key_scales_t =
    scale_t[LOG_CAPACITY][STACK_DEPTH][gdn::NUM_QK_HEADS][gdn::QK_BLOCKS];
using log_update_elements_t =
    e2m1_t[LOG_CAPACITY][STACK_DEPTH][gdn::NUM_VALUE_HEADS][gdn::VALUE_DIM];
using log_update_scales_t =
    scale_t[LOG_CAPACITY][STACK_DEPTH][gdn::NUM_VALUE_HEADS][gdn::VALUE_BLOCKS];
using lambda_t = coefficient_t[LOG_CAPACITY][gdn::NUM_VALUE_HEADS];
using live_entries_t = ap_uint<4>;

using state_primary_word_t = ap_uint<4 * gdn::BLOCK_SIZE>;
using state_residual_word_t = ap_uint<4 * gdn::BLOCK_SIZE>;
using scale_word_t = ap_uint<8 * gdn::VALUE_BLOCKS>;
using log_word_t = ap_uint<4 * gdn::BLOCK_SIZE>;

using resident_primary_slot_t =
    state_primary_word_t[gdn::NUM_VALUE_HEADS][gdn::KEY_DIM][gdn::VALUE_BLOCKS];
using resident_residual_slot_t =
    state_residual_word_t[gdn::NUM_VALUE_HEADS][gdn::KEY_DIM][gdn::VALUE_BLOCKS];
using resident_scale_slot_t =
    scale_word_t[gdn::NUM_VALUE_HEADS][gdn::KEY_DIM];
using resident_key_log_t =
    log_word_t[LOG_CAPACITY][STACK_DEPTH][gdn::NUM_QK_HEADS][gdn::QK_BLOCKS];
using resident_key_scale_log_t =
    scale_word_t[LOG_CAPACITY][STACK_DEPTH][gdn::NUM_QK_HEADS];
using resident_update_log_t =
    log_word_t[LOG_CAPACITY][STACK_DEPTH][gdn::NUM_VALUE_HEADS][gdn::VALUE_BLOCKS];
using resident_update_scale_log_t =
    scale_word_t[LOG_CAPACITY][STACK_DEPTH][gdn::NUM_VALUE_HEADS];

inline wide_mantissa_t round_shift_rne(wide_mantissa_t value, int shift) {
#pragma HLS INLINE
  if (shift <= 0 || value == 0) {
    return value;
  }
  if (shift >= 64) {
    return 0;
  }
  const bool negative = value < 0;
  ap_uint<64> magnitude = negative
      ? static_cast<ap_uint<64>>(-value)
      : static_cast<ap_uint<64>>(value);
  ap_uint<64> quotient = magnitude >> shift;
  const ap_uint<64> mask = (ap_uint<64>(1) << shift) - 1;
  const ap_uint<64> remainder = magnitude & mask;
  const ap_uint<64> halfway = ap_uint<64>(1) << (shift - 1);
  if (remainder > halfway ||
      (remainder == halfway && (quotient & 1) != 0)) {
    ++quotient;
  }
  const wide_mantissa_t rounded = static_cast<wide_mantissa_t>(quotient);
  return negative
      ? static_cast<wide_mantissa_t>(-static_cast<ap_int<65>>(rounded))
      : rounded;
}

inline mantissa_t saturate_int32(
    ap_int<65> value,
    counters_t counters) {
#pragma HLS INLINE
  if (value > INT32_MAX) {
    ++counters[COUNTER_ACCUMULATOR_SATURATIONS];
    return INT32_MAX;
  }
  if (value < INT32_MIN) {
    ++counters[COUNTER_ACCUMULATOR_SATURATIONS];
    return INT32_MIN;
  }
  return static_cast<mantissa_t>(value);
}

inline mantissa_t multiply_q1_15(
    mantissa_t value,
    coefficient_t coefficient,
    counters_t counters) {
#pragma HLS INLINE
  const wide_mantissa_t product =
      static_cast<wide_mantissa_t>(value) *
      static_cast<wide_mantissa_t>(coefficient);
  return saturate_int32(
      static_cast<ap_int<65>>(round_shift_rne(product, 15)), counters);
}

inline coefficient_t multiply_coefficients(
    coefficient_t left,
    coefficient_t right) {
#pragma HLS INLINE
  const ap_uint<32> product =
      static_cast<ap_uint<32>>(left) * static_cast<ap_uint<32>>(right);
  ap_uint<17> quotient = product >> 15;
  const ap_uint<15> remainder = product.range(14, 0);
  const ap_uint<15> halfway = ap_uint<15>(1) << 14;
  if (remainder > halfway ||
      (remainder == halfway && (quotient & 1) != 0)) {
    ++quotient;
  }
  return quotient > COEFFICIENT_ONE
      ? static_cast<coefficient_t>(COEFFICIENT_ONE)
      : static_cast<coefficient_t>(quotient);
}

template <int N>
aligned_t aligned_sum_guarded(
    const wide_mantissa_t mantissas[N],
    const exponent_t exponents[N],
    counters_t counters) {
#pragma HLS INLINE off
  bool found = false;
  exponent_t dominant = 0;
find_dominant:
  for (int index = 0; index < N; ++index) {
#pragma HLS PIPELINE II=1
    if (mantissas[index] != 0 &&
        (!found || exponents[index] > dominant)) {
      dominant = exponents[index];
      found = true;
    }
  }
  if (!found) {
    return {0, 0};
  }
  const exponent_t target = dominant - ACCUMULATOR_GUARD_BITS;
  mantissa_t accumulator = 0;
align_terms:
  for (int index = 0; index < N; ++index) {
#pragma HLS PIPELINE II=1
    const wide_mantissa_t raw = mantissas[index];
    if (raw == 0) {
      continue;
    }
    const int shift = static_cast<int>(target) -
                      static_cast<int>(exponents[index]);
    const wide_mantissa_t aligned = shift >= 0
        ? round_shift_rne(raw, shift)
        : static_cast<wide_mantissa_t>(raw << (-shift));
    if (aligned == 0 && shift > 0) {
      ++counters[COUNTER_ALIGNMENT_UNDERFLOWS];
    }
    const ap_int<65> sum =
        static_cast<ap_int<65>>(accumulator) +
        static_cast<ap_int<65>>(aligned);
    accumulator = saturate_int32(sum, counters);
  }
  return {accumulator, target};
}

mantissa_t decode_e2m1(e2m1_t code);
exponent_t decode_scale(scale_t scale);
wide_mantissa_t product_e2m1(e2m1_t left, e2m1_t right);
int select_e2m1_scale_power(
    const mantissa_t mantissas[gdn::BLOCK_SIZE],
    const exponent_t exponents[gdn::BLOCK_SIZE],
    counters_t counters);
e2m1_t quantize_e2m1(
    mantissa_t mantissa,
    exponent_t exponent,
    int scale_power,
    counters_t counters);

}  // namespace gdn_rs2

void rs2_arithmetic_top(
    const gdn_rs2::mantissa_t mantissas[gdn::BLOCK_SIZE],
    const gdn_rs2::exponent_t exponents[gdn::BLOCK_SIZE],
    gdn_rs2::e2m1_t primary_codes[gdn::BLOCK_SIZE],
    gdn_rs2::e2m1_t residual_codes[gdn::BLOCK_SIZE],
    gdn_rs2::exponent_t scale_powers_out[2],
    gdn_rs2::mantissa_t aligned_mantissa_out[1],
    gdn_rs2::exponent_t aligned_exponent_out[1],
    gdn_rs2::counters_t counters_out);

void gdn_rs2_top(
    std::uint8_t command,
    std::uint16_t sequence_id,
    std::uint8_t layer_id,
    std::uint8_t payload_flags,
    const gdn_rs2::qk_elements_t q_elements,
    const gdn_rs2::qk_scales_t q_scales,
    const gdn_rs2::qk_elements_t k_elements,
    const gdn_rs2::qk_scales_t k_scales,
    const gdn_rs2::value_elements_t v_elements,
    const gdn_rs2::value_scales_t v_scales,
    const gdn_rs2::coefficient_heads_t alpha,
    const gdn_rs2::coefficient_heads_t beta,
    const gdn_rs2::state_primary_elements_t state_primary_in,
    const gdn_rs2::state_scales_t state_primary_scales_in,
    const gdn_rs2::state_residual_elements_t state_residual_in,
    const gdn_rs2::state_scales_t state_residual_scales_in,
    const gdn_rs2::log_key_elements_t log_keys_in,
    const gdn_rs2::log_key_scales_t log_key_scales_in,
    const gdn_rs2::log_update_elements_t log_updates_in,
    const gdn_rs2::log_update_scales_t log_update_scales_in,
    const gdn_rs2::coefficient_heads_t gamma_in,
    const gdn_rs2::lambda_t lambda_in,
    gdn_rs2::live_entries_t live_entries_in,
    gdn_rs2::output_mantissas_t output_mantissas,
    gdn_rs2::output_exponents_t output_exponents,
    gdn_rs2::state_primary_elements_t state_primary_out,
    gdn_rs2::state_scales_t state_primary_scales_out,
    gdn_rs2::state_residual_elements_t state_residual_out,
    gdn_rs2::state_scales_t state_residual_scales_out,
    gdn_rs2::log_key_elements_t log_keys_out,
    gdn_rs2::log_key_scales_t log_key_scales_out,
    gdn_rs2::log_update_elements_t log_updates_out,
    gdn_rs2::log_update_scales_t log_update_scales_out,
    gdn_rs2::coefficient_heads_t gamma_out,
    gdn_rs2::lambda_t lambda_out,
    gdn_rs2::live_entries_t live_entries_out[1],
    std::uint8_t status_out[1],
    gdn_rs2::generation_t generation_out[1],
    gdn_rs2::counters_t command_counters_out,
    gdn_rs2::counters_t cumulative_counters_out);

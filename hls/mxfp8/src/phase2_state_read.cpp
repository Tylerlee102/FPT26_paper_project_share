#include "gdn_mxfp8_kernel.hpp"

#include "block_exp_align.hpp"
#include "e4m3_arithmetic.hpp"

namespace gdn_mxfp8 {

void phase2_decay_predict_tile(
    const qk_head_t k, const qk_head_scales_t k_scales, q1_15_t alpha,
    const state_block_tile_t state, const state_scale_tile_t state_scales,
    tile_mantissa_t decayed_mantissas, tile_exponent_t decayed_exponents,
    block_mantissa_t prediction_mantissas, block_exponent_t prediction_exponents,
    command_counter_array_t counters) {
decode_decay_mxfp8_rows:
  for (int row = 0; row < KEY_DIM; ++row) {
  decode_decay_mxfp8_lanes:
    for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
      decayed_mantissas[row][lane] = gdn::multiply_q1_15(
          decode_e4m3_mantissa(state[row][lane]), alpha, counters);
      decayed_exponents[row][lane] =
          decode_e4m3_exponent(state[row][lane], state_scales[row]);
    }
  }
predict_mxfp8_lanes:
  for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
    wide_mantissa_t terms[KEY_DIM];
    exponent_t exponents[KEY_DIM];
#pragma HLS ARRAY_PARTITION variable=terms cyclic factor=P_K dim=1
#pragma HLS ARRAY_PARTITION variable=exponents cyclic factor=P_K dim=1
  build_mxfp8_prediction_terms:
    for (int row = 0; row < KEY_DIM; ++row) {
#pragma HLS PIPELINE II=1
      terms[row] = scale_by_e4m3(k[row], decayed_mantissas[row][lane]);
      exponents[row] = static_cast<exponent_t>(
          static_cast<int>(decode_e4m3_exponent(k[row], k_scales[row / BLOCK_SIZE]))
          + static_cast<int>(decayed_exponents[row][lane]));
    }
    const gdn::aligned_value_t prediction = gdn::aligned_sum(terms, exponents, KEY_DIM, counters);
    prediction_mantissas[lane] = prediction.mantissa;
    prediction_exponents[lane] = prediction.exponent;
  }
}

}  // namespace gdn_mxfp8

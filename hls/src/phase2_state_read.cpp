#include "gdn_kernel.hpp"

#include "block_exp_align.hpp"
#include "mac_e2m1.hpp"

namespace gdn {

void phase2_decay_predict_tile(
    const qk_head_t k,
    const qk_head_scales_t k_scales,
    q1_15_t alpha,
    const state_block_tile_t state,
    const state_scale_tile_t state_scales,
    tile_mantissa_t decayed_mantissas,
    tile_exponent_t decayed_exponents,
    block_mantissa_t prediction_mantissas,
    block_exponent_t prediction_exponents,
    command_counter_array_t counters) {
decode_and_decay_rows:
  for (int row = 0; row < KEY_DIM; ++row) {
    const exponent_t state_exponent =
        decode_e2m1_exponent(state_scales[row]);
  decode_and_decay_lanes:
    for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
      const mantissa_t state_mantissa =
          decode_e2m1_mantissa(state[row][lane]);
      decayed_mantissas[row][lane] =
          multiply_q1_15(state_mantissa, alpha, counters);
      decayed_exponents[row][lane] = state_exponent;
    }
  }

predict_lanes:
  for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
    wide_mantissa_t terms[KEY_DIM];
    exponent_t term_exponents[KEY_DIM];
#pragma HLS ARRAY_PARTITION variable=terms cyclic factor=P_K dim=1
#pragma HLS ARRAY_PARTITION variable=term_exponents cyclic factor=P_K dim=1
  build_prediction_terms:
    for (int row = 0; row < KEY_DIM; ++row) {
#pragma HLS PIPELINE II=1
      terms[row] = scale_by_e2m1(k[row], decayed_mantissas[row][lane]);
      term_exponents[row] = static_cast<exponent_t>(
          static_cast<int>(decode_e2m1_exponent(k_scales[row / BLOCK_SIZE])) +
          static_cast<int>(decayed_exponents[row][lane]));
    }
    const aligned_value_t prediction =
        aligned_sum(terms, term_exponents, KEY_DIM, counters);
    prediction_mantissas[lane] = prediction.mantissa;
    prediction_exponents[lane] = prediction.exponent;
  }
}

}  // namespace gdn

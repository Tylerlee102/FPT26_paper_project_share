#include "gdn_kernel.hpp"

#include "block_exp_align.hpp"
#include "mac_e2m1.hpp"

namespace gdn {

void phase5_output_tile(
    const qk_head_t q,
    const qk_head_scales_t q_scales,
    int value_block,
    const tile_mantissa_t updated_mantissas,
    const tile_exponent_t updated_exponents,
    mantissa_t output_mantissas[VALUE_DIM],
    exponent_t output_exponents[VALUE_DIM],
    command_counter_array_t counters) {
output_lanes:
  for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
    wide_mantissa_t terms[KEY_DIM];
    exponent_t term_exponents[KEY_DIM];
#pragma HLS ARRAY_PARTITION variable=terms cyclic factor=P_K dim=1
#pragma HLS ARRAY_PARTITION variable=term_exponents cyclic factor=P_K dim=1
  build_output_terms:
    for (int row = 0; row < KEY_DIM; ++row) {
#pragma HLS PIPELINE II=1
      terms[row] = scale_by_e2m1(q[row], updated_mantissas[row][lane]);
      term_exponents[row] = static_cast<exponent_t>(
          static_cast<int>(decode_e2m1_exponent(q_scales[row / BLOCK_SIZE])) +
          static_cast<int>(updated_exponents[row][lane]));
    }
    const aligned_value_t output =
        aligned_sum(terms, term_exponents, KEY_DIM, counters);
    const int column = value_block * BLOCK_SIZE + lane;
    output_mantissas[column] = output.mantissa;
    output_exponents[column] = output.exponent;
  }
}

}  // namespace gdn

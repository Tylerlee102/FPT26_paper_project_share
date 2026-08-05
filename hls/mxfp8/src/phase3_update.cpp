#include "gdn_mxfp8_kernel.hpp"

#include <cstdint>

#include "block_exp_align.hpp"
#include "e4m3_arithmetic.hpp"

namespace gdn_mxfp8 {

void phase3_delta_tile(
    const value_head_t v, const value_head_scales_t v_scales, q1_15_t beta,
    int value_block, const block_mantissa_t prediction_mantissas,
    const block_exponent_t prediction_exponents, block_mantissa_t delta_mantissas,
    block_exponent_t delta_exponents, command_counter_array_t counters) {
  std::uint8_t underflows = 0;
delta_mxfp8_lanes:
  for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    const int column = value_block * BLOCK_SIZE + lane;
    bool underflow = false;
    const gdn::aligned_value_t residual = gdn::aligned_pair(
        decode_e4m3_mantissa(v[column]),
        decode_e4m3_exponent(v[column], v_scales[value_block]),
        -static_cast<wide_mantissa_t>(prediction_mantissas[lane]),
        prediction_exponents[lane], underflow, counters);
    underflows += static_cast<std::uint8_t>(underflow);
    delta_mantissas[lane] = gdn::multiply_q1_15(residual.mantissa, beta, counters);
    delta_exponents[lane] = residual.exponent;
  }
  counters[COUNTER_ALIGNMENT_UNDERFLOWS] += underflows;
}

}  // namespace gdn_mxfp8

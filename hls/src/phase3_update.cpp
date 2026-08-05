#include "gdn_kernel.hpp"

#include <cstdint>

#include "block_exp_align.hpp"
#include "mac_e2m1.hpp"

namespace gdn {

void phase3_delta_tile(
    const value_head_t v,
    const value_head_scales_t v_scales,
    q1_15_t beta,
    int value_block,
    const block_mantissa_t prediction_mantissas,
    const block_exponent_t prediction_exponents,
    block_mantissa_t delta_mantissas,
    block_exponent_t delta_exponents,
    command_counter_array_t counters) {
  const exponent_t value_exponent =
      decode_e2m1_exponent(v_scales[value_block]);
  std::uint8_t alignment_underflows = 0;
delta_lanes:
  for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    const int column = value_block * BLOCK_SIZE + lane;
    const mantissa_t value_mantissa = decode_e2m1_mantissa(v[column]);
    bool alignment_underflow = false;
    const aligned_value_t residual = aligned_pair(
        value_mantissa,
        value_exponent,
        -static_cast<wide_mantissa_t>(prediction_mantissas[lane]),
        prediction_exponents[lane],
        alignment_underflow,
        counters);
    alignment_underflows += static_cast<std::uint8_t>(alignment_underflow);
    delta_mantissas[lane] =
        multiply_q1_15(residual.mantissa, beta, counters);
    delta_exponents[lane] = residual.exponent;
  }
  counters[COUNTER_ALIGNMENT_UNDERFLOWS] += alignment_underflows;
}

}  // namespace gdn

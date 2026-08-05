#include "gdn_mxfp8_kernel.hpp"

#include <cstdint>

#include "block_exp_align.hpp"
#include "e4m3_arithmetic.hpp"

namespace gdn_mxfp8 {

void phase4_update_state_tile(
    const qk_head_t k, const qk_head_scales_t k_scales,
    const block_mantissa_t delta_mantissas, const block_exponent_t delta_exponents,
    const tile_mantissa_t decayed_mantissas, const tile_exponent_t decayed_exponents,
    state_block_tile_t state, state_scale_tile_t state_scales,
    tile_mantissa_t updated_mantissas, tile_exponent_t updated_exponents,
    command_counter_array_t counters) {
update_mxfp8_rows:
  for (int row = 0; row < KEY_DIM; ++row) {
    mantissa_t row_mantissas[BLOCK_SIZE];
    exponent_t row_exponents[BLOCK_SIZE];
    std::uint8_t underflows = 0;
#pragma HLS ARRAY_PARTITION variable=row_mantissas cyclic factor=P_V dim=1
#pragma HLS ARRAY_PARTITION variable=row_exponents cyclic factor=P_V dim=1
  update_mxfp8_lanes:
    for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
      const wide_mantissa_t write_mantissa = scale_by_e4m3(k[row], delta_mantissas[lane]);
      const exponent_t write_exponent = static_cast<exponent_t>(
          static_cast<int>(decode_e4m3_exponent(k[row], k_scales[row / BLOCK_SIZE]))
          + static_cast<int>(delta_exponents[lane]));
      bool underflow = false;
      const gdn::aligned_value_t updated = gdn::aligned_pair(
          decayed_mantissas[row][lane], decayed_exponents[row][lane],
          write_mantissa, write_exponent, underflow, counters);
      underflows += static_cast<std::uint8_t>(underflow);
      row_mantissas[lane] = updated.mantissa;
      row_exponents[lane] = updated.exponent;
      updated_mantissas[row][lane] = updated.mantissa;
      updated_exponents[row][lane] = updated.exponent;
    }
    counters[COUNTER_ALIGNMENT_UNDERFLOWS] += underflows;
    const int scale_power = select_scale_power_e4m3(row_mantissas, row_exponents, counters);
    const unsigned scale_code = static_cast<unsigned>(scale_power + E8M0_BIAS);
    if (gdn::to_u8(state_scales[row]) != scale_code) {
      ++counters[COUNTER_STATE_SCALE_CHANGES];
    }
    state_scales[row] = static_cast<mx_scale_t>(scale_code);
  requantize_mxfp8_lanes:
    for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
      state[row][lane] = quantize_exact_e4m3(
          row_mantissas[lane], row_exponents[lane], scale_power, counters);
    }
  }
}

}  // namespace gdn_mxfp8

#include "block_exp_align.hpp"

#include "gdn_params.hpp"

namespace gdn {

std::int16_t effective_block_exp(mx_scale_t exp_a, mx_scale_t exp_b) {
#pragma HLS INLINE
  return static_cast<std::int16_t>(
      static_cast<int>(to_u8(exp_a)) + static_cast<int>(to_u8(exp_b)) - 2 * E8M0_BIAS);
}

block_accum_t block_exp_align_accumulate(const mx_partial_t partials[], int count) {
#pragma HLS INLINE off
  block_accum_t out{};
  if (count <= 0) {
    out.accum_q3 = 0;
    out.exponent = 0;
    return out;
  }

  std::int16_t dominant_exp = effective_block_exp(partials[0].exp_a, partials[0].exp_b);
  find_dominant:
  for (int i = 1; i < count; ++i) {
#pragma HLS LOOP_TRIPCOUNT min=1 max=32
    const std::int16_t exp = effective_block_exp(partials[i].exp_a, partials[i].exp_b);
    if (exp > dominant_exp) {
      dominant_exp = exp;
    }
  }

  acc32_t acc = 0;
  align_and_sum:
  for (int i = 0; i < count; ++i) {
#pragma HLS PIPELINE II=1
#pragma HLS LOOP_TRIPCOUNT min=1 max=32
    const std::int16_t exp = effective_block_exp(partials[i].exp_a, partials[i].exp_b);
    const int shift = static_cast<int>(dominant_exp - exp);
    acc32_t value = static_cast<acc32_t>(partials[i].partial_q3);
    if (shift > 0) {
      value = (shift >= 24) ? static_cast<acc32_t>(0) : static_cast<acc32_t>(value >> shift);
    }
    acc += value;
    acc = static_cast<acc32_t>(saturate_int24(acc));
  }

  out.accum_q3 = saturate_int24(acc);
  out.exponent = dominant_exp;
  return out;
}

}  // namespace gdn


#include "gdn_kernel.hpp"

namespace gdn {

q4_3_t phase3_delta_update(
    q4_3_t state_q3,
    q4_3_t predicted_q3,
    q4_3_t value_q3,
    q4_3_t key_q3,
    std::uint8_t beta_u8) {
#pragma HLS INLINE
  const acc32_t residual_q3 = static_cast<acc32_t>(predicted_q3) - static_cast<acc32_t>(value_q3);
  const acc32_t beta = static_cast<acc32_t>(beta_u8);
  const acc32_t delta_q3 = (residual_q3 * static_cast<acc32_t>(key_q3) * beta) / (127 * 8);
  const acc32_t updated = static_cast<acc32_t>(state_q3) - delta_q3;
  if (updated > 32767) {
    return static_cast<q4_3_t>(32767);
  }
  if (updated < -32768) {
    return static_cast<q4_3_t>(-32768);
  }
  return static_cast<q4_3_t>(updated);
}

}  // namespace gdn


#include "gdn_kernel.hpp"

namespace gdn {

q4_3_t phase5_apply_gate(q4_3_t value_q3, q4_3_t gate_q3) {
#pragma HLS INLINE
  const acc32_t product_q6 = static_cast<acc32_t>(value_q3) * static_cast<acc32_t>(gate_q3);
  acc32_t rounded_q3 = 0;
  if (product_q6 >= 0) {
    rounded_q3 = static_cast<acc32_t>((product_q6 + 4) >> 3);
  } else {
    const acc32_t abs_product = static_cast<acc32_t>(-product_q6);
    rounded_q3 = static_cast<acc32_t>(-static_cast<acc32_t>((abs_product + 4) >> 3));
  }
  if (rounded_q3 > 32767) {
    return static_cast<q4_3_t>(32767);
  }
  if (rounded_q3 < -32768) {
    return static_cast<q4_3_t>(-32768);
  }
  return static_cast<q4_3_t>(rounded_q3);
}

}  // namespace gdn

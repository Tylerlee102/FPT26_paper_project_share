#include "mac_e2m1.hpp"

namespace gdn {

q4_3_t decode_e2m1_q3(mx_e2m1_t x) {
#pragma HLS INLINE
  const unsigned code = to_u4(x);
  const unsigned mag = code & 0x07u;
  q4_3_t mag_q3 = 0;
  switch (mag) {
    case 0: mag_q3 = 0; break;   // 0.0
    case 1: mag_q3 = 4; break;   // 0.5
    case 2: mag_q3 = 8; break;   // 1.0
    case 3: mag_q3 = 12; break;  // 1.5
    case 4: mag_q3 = 16; break;  // 2.0
    case 5: mag_q3 = 24; break;  // 3.0
    case 6: mag_q3 = 32; break;  // 4.0
    default: mag_q3 = 48; break; // 6.0
  }
  return (code & 0x08u) ? static_cast<q4_3_t>(-mag_q3) : mag_q3;
}

mx_e2m1_t encode_e2m1_q3(q4_3_t x_q3) {
#pragma HLS INLINE
  const bool neg = x_q3 < 0;
  const q4_3_t abs_q3 = neg ? static_cast<q4_3_t>(-x_q3) : x_q3;
  static const q4_3_t mag_q3[8] = {0, 4, 8, 12, 16, 24, 32, 48};
#pragma HLS ARRAY_PARTITION variable=mag_q3 complete dim=0

  unsigned best = 0;
  q4_3_t best_dist = 32767;
  for (unsigned i = 0; i < 8; ++i) {
#pragma HLS UNROLL
    q4_3_t dist = static_cast<q4_3_t>(abs_q3 - mag_q3[i]);
    if (dist < 0) {
      dist = static_cast<q4_3_t>(-dist);
    }
    const bool closer = dist < best_dist;
    const bool tie_even = (dist == best_dist) && ((i & 1u) == 0u) && ((best & 1u) != 0u);
    if (closer || tie_even) {
      best = i;
      best_dist = dist;
    }
  }
  return static_cast<mx_e2m1_t>((neg ? 0x08u : 0x00u) | best);
}

q4_3_t e2m1_mul_q4_3(mx_e2m1_t a, mx_e2m1_t b) {
#pragma HLS INLINE
  const unsigned a_code = to_u4(a);
  const unsigned b_code = to_u4(b);
  const unsigned a_mag = a_code & 0x07u;
  const unsigned b_mag = b_code & 0x07u;
  const bool neg = ((a_code ^ b_code) & 0x08u) != 0u;

  static const q4_3_t product_mag_q3[8][8] = {
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 2, 4, 6, 8, 12, 16, 24},
      {0, 4, 8, 12, 16, 24, 32, 48},
      {0, 6, 12, 18, 24, 36, 48, 72},
      {0, 8, 16, 24, 32, 48, 64, 96},
      {0, 12, 24, 36, 48, 72, 96, 144},
      {0, 16, 32, 48, 64, 96, 128, 192},
      {0, 24, 48, 72, 96, 144, 192, 288},
  };
#pragma HLS ARRAY_PARTITION variable=product_mag_q3 complete dim=0

  const q4_3_t mag_q3 = product_mag_q3[a_mag][b_mag];
  if (mag_q3 == 0) {
    return 0;
  }
  return neg ? static_cast<q4_3_t>(-mag_q3) : mag_q3;
}

}  // namespace gdn

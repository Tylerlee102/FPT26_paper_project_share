#include "mac_e2m1.hpp"

namespace gdn {

mantissa_t decode_e2m1_mantissa(mx_e2m1_t value) {
#pragma HLS INLINE
  static const mantissa_t magnitude[8] = {0, 1, 2, 3, 4, 6, 8, 12};
#pragma HLS ARRAY_PARTITION variable=magnitude complete dim=1
  const unsigned code = to_u4(value);
  const mantissa_t decoded = magnitude[code & 0x07u];
  return ((code & 0x08u) != 0u && decoded != 0) ? -decoded : decoded;
}

exponent_t decode_e2m1_exponent(mx_scale_t scale) {
#pragma HLS INLINE
  // Integer magnitude r represents r/2, so E8M0 code 127 maps to power -1.
  return static_cast<exponent_t>(static_cast<int>(to_u8(scale)) - 128);
}

wide_mantissa_t e2m1_product_mantissa(mx_e2m1_t a, mx_e2m1_t b) {
#pragma HLS INLINE
  const unsigned a_code = to_u4(a);
  const unsigned b_code = to_u4(b);
  const unsigned a_mag = a_code & 0x07u;
  const unsigned b_mag = b_code & 0x07u;
  const bool negative = ((a_code ^ b_code) & 0x08u) != 0u;

  static const std::uint8_t product_mag[8][8] = {
      {0, 0, 0, 0, 0, 0, 0, 0},
      {0, 1, 2, 3, 4, 6, 8, 12},
      {0, 2, 4, 6, 8, 12, 16, 24},
      {0, 3, 6, 9, 12, 18, 24, 36},
      {0, 4, 8, 12, 16, 24, 32, 48},
      {0, 6, 12, 18, 24, 36, 48, 72},
      {0, 8, 16, 24, 32, 48, 64, 96},
      {0, 12, 24, 36, 48, 72, 96, 144},
  };
#pragma HLS ARRAY_PARTITION variable=product_mag complete dim=0

  const wide_mantissa_t magnitude = product_mag[a_mag][b_mag];
  if (magnitude == 0) {
    return 0;
  }
  return negative ? -magnitude : magnitude;
}

wide_mantissa_t scale_by_e2m1(mx_e2m1_t coefficient, mantissa_t value) {
#pragma HLS INLINE
  const unsigned code = to_u4(coefficient);
  const unsigned magnitude_code = code & 0x07u;
  const wide_mantissa_t x = static_cast<wide_mantissa_t>(value);
  wide_mantissa_t magnitude = 0;
  switch (magnitude_code) {
    case 0: magnitude = 0; break;
    case 1: magnitude = x; break;
    case 2: magnitude = x + x; break;
    case 3: magnitude = x + x + x; break;
    case 4: magnitude = x + x + x + x; break;
    case 5: magnitude = x + x + x + x + x + x; break;
    case 6: magnitude = x + x + x + x + x + x + x + x; break;
    default:
      magnitude = x + x + x + x + x + x + x + x + x + x + x + x;
      break;
  }
  return ((code & 0x08u) != 0u) ? -magnitude : magnitude;
}

}  // namespace gdn

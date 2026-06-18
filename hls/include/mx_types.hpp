#pragma once

#include <cstdint>

#if defined(__has_include)
#if __has_include(<ap_int.h>)
#include <ap_int.h>
#define GDN_HAS_AP_INT 1
#endif
#endif

#ifndef GDN_HAS_AP_INT
#define GDN_HAS_AP_INT 0
#endif

namespace gdn {

#if GDN_HAS_AP_INT
using mx_e2m1_t = ap_uint<4>;
using mx_e4m3_t = ap_uint<8>;
using mx_scale_t = ap_uint<8>;
using q4_3_t = ap_int<16>;
using acc24_t = ap_int<24>;
using acc32_t = ap_int<32>;
#else
using mx_e2m1_t = std::uint8_t;
using mx_e4m3_t = std::uint8_t;
using mx_scale_t = std::uint8_t;
using q4_3_t = std::int16_t;
using acc24_t = std::int32_t;
using acc32_t = std::int32_t;
#endif

struct mx_partial_t {
  q4_3_t partial_q3;
  mx_scale_t exp_a;
  mx_scale_t exp_b;
  bool last;
};

struct block_accum_t {
  acc24_t accum_q3;
  std::int16_t exponent;
};

inline unsigned to_u8(mx_scale_t value) {
  return static_cast<unsigned>(value) & 0xffu;
}

inline unsigned to_u4(mx_e2m1_t value) {
  return static_cast<unsigned>(value) & 0x0fu;
}

inline acc24_t saturate_int24(acc32_t value) {
  if (value > static_cast<acc32_t>((1 << 23) - 1)) {
    return static_cast<acc24_t>((1 << 23) - 1);
  }
  if (value < static_cast<acc32_t>(-(1 << 23))) {
    return static_cast<acc24_t>(-(1 << 23));
  }
  return static_cast<acc24_t>(value);
}

}  // namespace gdn


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
using command_counter_t = ap_uint<24>;
#else
using mx_e2m1_t = std::uint8_t;
using mx_e4m3_t = std::uint8_t;
using mx_scale_t = std::uint8_t;
using command_counter_t = std::uint32_t;
#endif

using q1_15_t = std::uint16_t;
using mantissa_t = std::int32_t;
using wide_mantissa_t = std::int64_t;
using exponent_t = std::int16_t;
using counter_t = std::uint64_t;
using generation_t = std::uint64_t;
using status_t = std::uint8_t;

struct aligned_value_t {
  mantissa_t mantissa;
  exponent_t exponent;
};

inline unsigned raw_e2m1(mx_e2m1_t value) {
  return static_cast<unsigned>(value);
}

inline unsigned to_u4(mx_e2m1_t value) {
  return raw_e2m1(value) & 0x0fu;
}

inline unsigned to_u8(mx_scale_t value) {
  return static_cast<unsigned>(value) & 0xffu;
}

}  // namespace gdn

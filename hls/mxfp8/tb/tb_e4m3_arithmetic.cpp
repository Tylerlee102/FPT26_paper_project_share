#include <cstdint>
#include <iostream>

#include "e4m3_arithmetic.hpp"

namespace {

int expected_mantissa(unsigned code) {
  const unsigned exponent = (code >> 3) & 0x0fu;
  const int magnitude = exponent == 0u ? static_cast<int>(code & 7u)
                                        : static_cast<int>(8u + (code & 7u));
  return ((code & 0x80u) != 0u && magnitude != 0) ? -magnitude : magnitude;
}

int expected_exponent(unsigned code, unsigned scale) {
  const unsigned exponent = (code >> 3) & 0x0fu;
  return static_cast<int>(scale) - 127 + (exponent == 0u ? -9 : static_cast<int>(exponent) - 10);
}

}  // namespace

int main() {
  for (unsigned code = 0; code < 256; ++code) {
    const bool valid = code != 0x7fu && code != 0x80u && code != 0xffu;
    if (gdn_mxfp8::valid_e4m3(code) != valid) {
      std::cerr << "validity mismatch for code " << code << "\n";
      return 1;
    }
    if (!valid) continue;
    if (gdn_mxfp8::decode_e4m3_mantissa(code) != expected_mantissa(code)) {
      std::cerr << "mantissa mismatch for code " << code << "\n";
      return 1;
    }
    if (gdn_mxfp8::decode_e4m3_exponent(code, 127) != expected_exponent(code, 127)) {
      std::cerr << "exponent mismatch for code " << code << "\n";
      return 1;
    }
    const std::int64_t scaled = gdn_mxfp8::scale_by_e4m3(code, -17);
    if (scaled != static_cast<std::int64_t>(expected_mantissa(code)) * -17) {
      std::cerr << "coefficient product mismatch for code " << code << "\n";
      return 1;
    }
  }

  gdn_mxfp8::command_counter_t counters[gdn_mxfp8::COUNTER_COUNT] = {};
  for (unsigned code = 0; code < 256; ++code) {
    if (!gdn_mxfp8::valid_e4m3(code)) continue;
    const int mantissa = gdn_mxfp8::decode_e4m3_mantissa(code);
    if (mantissa == 0) continue;
    const int exponent = gdn_mxfp8::decode_e4m3_exponent(code, 127);
    const unsigned roundtrip = gdn_mxfp8::raw_e4m3(
        gdn_mxfp8::quantize_exact_e4m3(mantissa, exponent, 0, counters));
    if (roundtrip != code) {
      std::cerr << "roundtrip mismatch code=" << code << " got=" << roundtrip << "\n";
      return 1;
    }
  }
  if (gdn_mxfp8::raw_e4m3(gdn_mxfp8::quantize_exact_e4m3(17, -4, 0, counters)) != 0x38u ||
      gdn_mxfp8::raw_e4m3(gdn_mxfp8::quantize_exact_e4m3(19, -4, 0, counters)) != 0x3au) {
    std::cerr << "RNE midpoint mismatch\n";
    return 1;
  }
  std::cout << "tb_e4m3_arithmetic PASS\n";
  return 0;
}

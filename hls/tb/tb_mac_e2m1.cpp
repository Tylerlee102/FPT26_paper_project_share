#include <cstdint>
#include <iostream>

#include "mac_e2m1.hpp"

namespace {

int expected_mantissa(unsigned code) {
  static const int magnitude[8] = {0, 1, 2, 3, 4, 6, 8, 12};
  const int value = magnitude[code & 0x07u];
  return ((code & 0x08u) != 0u && value != 0) ? -value : value;
}

}  // namespace

int main() {
  for (unsigned a = 0; a < 16; ++a) {
    for (unsigned b = 0; b < 16; ++b) {
      const std::int64_t got = gdn::e2m1_product_mantissa(a, b);
      const std::int64_t expected =
          static_cast<std::int64_t>(expected_mantissa(a)) *
          static_cast<std::int64_t>(expected_mantissa(b));
      if (got != expected) {
        std::cerr << "E2M1 product mismatch a=" << a << " b=" << b << "\n";
        return 1;
      }
    }
  }
  for (unsigned code = 0; code < 16; ++code) {
    const std::int64_t got = gdn::scale_by_e2m1(code, -17);
    const std::int64_t expected =
        static_cast<std::int64_t>(expected_mantissa(code)) * -17;
    if (got != expected) {
      std::cerr << "E2M1 scale mismatch code=" << code << "\n";
      return 1;
    }
  }
  std::cout << "tb_mac_e2m1 PASS\n";
  return 0;
}

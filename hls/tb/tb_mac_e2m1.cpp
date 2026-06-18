#include <cstdint>
#include <iostream>

#include "mac_e2m1.hpp"

namespace {

int expected_decode_q3(unsigned code) {
  static const int mag_q3[8] = {0, 4, 8, 12, 16, 24, 32, 48};
  const int mag = mag_q3[code & 0x07u];
  return (code & 0x08u) ? -mag : mag;
}

int expected_product_q3(unsigned a, unsigned b) {
  const int product_q6 = expected_decode_q3(a) * expected_decode_q3(b);
  return product_q6 / 8;
}

}  // namespace

int main() {
  for (unsigned a = 0; a < 16; ++a) {
    for (unsigned b = 0; b < 16; ++b) {
      const int got = static_cast<int>(gdn::e2m1_mul_q4_3(a, b));
      const int expected = expected_product_q3(a, b);
      if (got != expected) {
        std::cerr << "E2M1 product mismatch a=" << a << " b=" << b
                  << " got=" << got << " expected=" << expected << "\n";
        return 1;
      }
    }
  }

  std::uint32_t lfsr = 0x00fb72u;
  for (int i = 0; i < 100000; ++i) {
    lfsr = (lfsr >> 1) ^ (-(static_cast<int>(lfsr) & 1) & 0xd0000001u);
    const unsigned a = lfsr & 0x0fu;
    const unsigned b = (lfsr >> 8) & 0x0fu;
    const int got = static_cast<int>(gdn::e2m1_mul_q4_3(a, b));
    const int expected = expected_product_q3(a, b);
    if (got != expected) {
      std::cerr << "Random E2M1 product mismatch at " << i << "\n";
      return 1;
    }
  }

  std::cout << "tb_mac_e2m1 PASS\n";
  return 0;
}


#include "gdn_rs2_kernel.hpp"

#include <iostream>

namespace {

bool test_decode_and_product() {
  const int magnitude[8] = {0, 1, 2, 3, 4, 6, 8, 12};
  for (int code = 0; code < 16; ++code) {
    const int expected = (code & 8) != 0 && (code & 7) != 0
        ? -magnitude[code & 7]
        : magnitude[code & 7];
    if (gdn_rs2::decode_e2m1(code).to_int() != expected) {
      std::cerr << "decode mismatch code " << code << "\n";
      return false;
    }
  }
  for (int left = 0; left < 16; ++left) {
    for (int right = 0; right < 16; ++right) {
      const int expected = gdn_rs2::decode_e2m1(left).to_int() *
                           gdn_rs2::decode_e2m1(right).to_int();
      if (gdn_rs2::product_e2m1(left, right).to_int64() != expected) {
        std::cerr << "product mismatch " << left << "," << right << "\n";
        return false;
      }
    }
  }
  return true;
}

bool test_exact_two_term_quantizer() {
  gdn_rs2::mantissa_t mantissas[gdn::BLOCK_SIZE]{};
  gdn_rs2::exponent_t exponents[gdn::BLOCK_SIZE]{};
  const int magnitude[8] = {0, 1, 2, 3, 4, 6, 8, 12};
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
    const int index = lane & 7;
    const bool negative = (lane & 8) != 0;
    mantissas[lane] = negative ? -magnitude[index] : magnitude[index];
    exponents[lane] = -1;
  }
  gdn_rs2::e2m1_t primary[gdn::BLOCK_SIZE]{};
  gdn_rs2::e2m1_t residual[gdn::BLOCK_SIZE]{};
  gdn_rs2::exponent_t powers[2]{};
  gdn_rs2::mantissa_t aligned_m[1]{};
  gdn_rs2::exponent_t aligned_x[1]{};
  gdn_rs2::counters_t counters{};
  rs2_arithmetic_top(
      mantissas,
      exponents,
      primary,
      residual,
      powers,
      aligned_m,
      aligned_x,
      counters);
  if (powers[0].to_int() != 0 || powers[1].to_int() != 0) {
    std::cerr << "unexpected exact quantizer powers\n";
    return false;
  }
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
    const unsigned expected = (lane & 7) == 0
        ? 0u
        : static_cast<unsigned>((lane & 7) | ((lane & 8) ? 8 : 0));
    if (primary[lane].to_uint() != expected || residual[lane] != 0) {
      std::cerr << "two-term exact mismatch lane " << lane << "\n";
      return false;
    }
  }
  return counters[gdn_rs2::COUNTER_ELEMENT_SATURATIONS] == 0 &&
         counters[gdn_rs2::COUNTER_ACCUMULATOR_SATURATIONS] == 0 &&
         counters[gdn_rs2::COUNTER_SCALE_CLAMPS] == 0;
}

bool test_round_to_nearest_even() {
  return gdn_rs2::round_shift_rne(5, 1).to_int64() == 2 &&
         gdn_rs2::round_shift_rne(7, 1).to_int64() == 4 &&
         gdn_rs2::round_shift_rne(-5, 1).to_int64() == -2 &&
         gdn_rs2::round_shift_rne(-7, 1).to_int64() == -4;
}

}  // namespace

int main() {
  if (!test_decode_and_product() ||
      !test_exact_two_term_quantizer() ||
      !test_round_to_nearest_even()) {
    return 1;
  }
  std::cout << "PASS: native E2M1 multiply and two-term RS2 quantization\n";
  return 0;
}

#include <iostream>

#include "block_exp_align.hpp"

int main() {
  gdn::command_counter_t counters[gdn::COUNTER_COUNT]{};
  if (gdn::round_shift_rne(5, 1) != 2 ||
      gdn::round_shift_rne(7, 1) != 4 ||
      gdn::round_shift_rne(-5, 1) != -2 ||
      gdn::round_shift_rne(-7, 1) != -4) {
    std::cerr << "RNE mismatch\n";
    return 1;
  }
  bool alignment_underflow = false;
  const gdn::aligned_value_t pair = gdn::aligned_pair(
      16, 0, 16, -1, alignment_underflow, counters);
  if (pair.mantissa != 24 || pair.exponent != 0) {
    std::cerr << "aligned pair mismatch\n";
    return 1;
  }
  gdn::wide_mantissa_t mantissas[gdn::KEY_DIM]{};
  gdn::exponent_t exponents[gdn::KEY_DIM]{};
  mantissas[0] = 16;
  mantissas[1] = 16;
  exponents[0] = 0;
  exponents[1] = -1;
  const gdn::aligned_value_t sum =
      gdn::aligned_sum(mantissas, exponents, 2, counters);
  if (sum.mantissa != 24 || sum.exponent != 0) {
    std::cerr << "aligned sum mismatch\n";
    return 1;
  }
  std::cout << "tb_block_exp PASS\n";
  return 0;
}

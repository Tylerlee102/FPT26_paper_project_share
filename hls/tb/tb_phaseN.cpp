#include <iostream>

#include "block_exp_align.hpp"

int main() {
  gdn::command_counter_t counters[gdn::COUNTER_COUNT]{};
  if (gdn::multiply_q1_15(7, 16384, counters) != 4 ||
      gdn::multiply_q1_15(-7, 16384, counters) != -4 ||
      gdn::multiply_q1_15(12, 32768, counters) != 12) {
    std::cerr << "Q1.15 mismatch\n";
    return 1;
  }
  std::cout << "tb_phaseN PASS\n";
  return 0;
}

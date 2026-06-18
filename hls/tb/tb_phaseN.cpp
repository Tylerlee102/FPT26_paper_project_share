#include <iostream>

#include "gdn_kernel.hpp"

int main() {
  const gdn::q4_3_t state = 16;
  const gdn::q4_3_t predicted = 24;
  const gdn::q4_3_t value = 8;
  const gdn::q4_3_t key = 8;
  const gdn::q4_3_t updated = gdn::phase3_delta_update(state, predicted, value, key, 127);
  if (static_cast<int>(updated) != 0) {
    std::cerr << "phase3 update mismatch got=" << static_cast<int>(updated) << "\n";
    return 1;
  }

  const gdn::q4_3_t gated = gdn::phase5_apply_gate(16, 4);
  if (static_cast<int>(gated) != 8) {
    std::cerr << "phase5 gate mismatch got=" << static_cast<int>(gated) << "\n";
    return 1;
  }

  std::cout << "tb_phaseN PASS\n";
  return 0;
}


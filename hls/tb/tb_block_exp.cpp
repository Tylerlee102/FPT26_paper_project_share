#include <iostream>

#include "block_exp_align.hpp"

int main() {
  {
    gdn::block_accum_t got = gdn::block_exp_align_accumulate(nullptr, 0);
    if (static_cast<int>(got.accum_q3) != 0 || got.exponent != 0) {
      std::cerr << "empty block mismatch\n";
      return 1;
    }
  }

  {
    gdn::mx_partial_t partials[2] = {
        {16, 127, 127, false},
        {8, 127, 127, true},
    };
    gdn::block_accum_t got = gdn::block_exp_align_accumulate(partials, 2);
    if (static_cast<int>(got.accum_q3) != 24 || got.exponent != 0) {
      std::cerr << "same exponent accumulation mismatch\n";
      return 1;
    }
  }

  {
    gdn::mx_partial_t partials[2] = {
        {16, 127, 127, false},
        {16, 127, 126, true},
    };
    gdn::block_accum_t got = gdn::block_exp_align_accumulate(partials, 2);
    if (static_cast<int>(got.accum_q3) != 24 || got.exponent != 0) {
      std::cerr << "shifted exponent accumulation mismatch got="
                << static_cast<int>(got.accum_q3) << " exp=" << got.exponent << "\n";
      return 1;
    }
  }

  std::cout << "tb_block_exp PASS\n";
  return 0;
}


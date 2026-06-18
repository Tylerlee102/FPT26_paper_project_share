#include "gdn_kernel.hpp"

namespace gdn {

void phase4_state_write(
    const state_tensor_t state_in,
    state_tensor_t state_out) {
  heads:
  for (int h = 0; h < NUM_HEADS; ++h) {
    rows:
    for (int r = 0; r < HEAD_DIM; ++r) {
      cols:
      for (int c = 0; c < HEAD_DIM; ++c) {
#pragma HLS PIPELINE II=1
        state_out[h][r][c] = state_in[h][r][c];
      }
    }
  }
}

}  // namespace gdn


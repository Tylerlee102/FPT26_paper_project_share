#include "gdn_kernel.hpp"

namespace gdn {

void phase2_state_read(
    const state_scale_t state_scales,
    mx_scale_t row_exp[NUM_HEADS][HEAD_DIM][STATE_BLOCKS]) {
  heads:
  for (int h = 0; h < NUM_HEADS; ++h) {
    rows:
    for (int r = 0; r < HEAD_DIM; ++r) {
      blocks:
      for (int b = 0; b < STATE_BLOCKS; ++b) {
#pragma HLS PIPELINE II=1
        row_exp[h][r][b] = state_scales[h][r][b];
      }
    }
  }
}

}  // namespace gdn


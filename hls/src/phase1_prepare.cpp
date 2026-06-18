#include "gdn_kernel.hpp"

namespace gdn {

void phase1_prepare(
    const head_scale_t q_scales,
    const head_scale_t k_scales,
    const head_scale_t v_scales,
    const head_scale_t gate_scales,
    mx_scale_t activation_exp[NUM_HEADS][4][NUM_BLOCKS]) {
  heads:
  for (int h = 0; h < NUM_HEADS; ++h) {
    blocks:
    for (int b = 0; b < NUM_BLOCKS; ++b) {
#pragma HLS PIPELINE II=1
      activation_exp[h][0][b] = q_scales[h][b];
      activation_exp[h][1][b] = k_scales[h][b];
      activation_exp[h][2][b] = v_scales[h][b];
      activation_exp[h][3][b] = gate_scales[h][b];
    }
  }
}

}  // namespace gdn


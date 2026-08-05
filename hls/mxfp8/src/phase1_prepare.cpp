#include "gdn_mxfp8_kernel.hpp"

#include "e4m3_arithmetic.hpp"

namespace gdn_mxfp8 {

bool phase1_validate_token(
    const qk_tensor_t q, const qk_scale_tensor_t q_scales,
    const qk_tensor_t k, const qk_scale_tensor_t k_scales,
    const value_tensor_t v, const value_scale_tensor_t v_scales,
    const q1_15_head_t alpha, const q1_15_head_t beta,
    qk_tensor_t q_local, qk_scale_tensor_t q_scales_local,
    qk_tensor_t k_local, qk_scale_tensor_t k_scales_local,
    value_tensor_t v_local, value_scale_tensor_t v_scales_local,
    q1_15_head_t alpha_local, q1_15_head_t beta_local) {
validate_mxfp8_q_heads:
  for (int head = 0; head < NUM_QK_HEADS; ++head) {
  validate_mxfp8_q_blocks:
    for (int block = 0; block < QK_BLOCKS; ++block) {
      const mx_scale_t scale = q_scales[head][block];
      q_scales_local[head][block] = scale;
      if (gdn::to_u8(scale) == 255u) return false;
      bool zero = true;
    validate_mxfp8_q_elements:
      for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
        const int index = block * BLOCK_SIZE + lane;
        const mx_element_t value = q[head][index];
        q_local[head][index] = value;
        if (!valid_e4m3(value)) return false;
        zero = zero && (raw_e4m3(value) & 0x7fu) == 0u;
      }
      if (zero && gdn::to_u8(scale) != E8M0_BIAS) return false;
    }
  }
validate_mxfp8_k_heads:
  for (int head = 0; head < NUM_QK_HEADS; ++head) {
  validate_mxfp8_k_blocks:
    for (int block = 0; block < QK_BLOCKS; ++block) {
      const mx_scale_t scale = k_scales[head][block];
      k_scales_local[head][block] = scale;
      if (gdn::to_u8(scale) == 255u) return false;
      bool zero = true;
    validate_mxfp8_k_elements:
      for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
        const int index = block * BLOCK_SIZE + lane;
        const mx_element_t value = k[head][index];
        k_local[head][index] = value;
        if (!valid_e4m3(value)) return false;
        zero = zero && (raw_e4m3(value) & 0x7fu) == 0u;
      }
      if (zero && gdn::to_u8(scale) != E8M0_BIAS) return false;
    }
  }
validate_mxfp8_gates:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
    alpha_local[head] = alpha[head];
    beta_local[head] = beta[head];
    if (alpha[head] > 32768u || beta[head] > 32768u) return false;
  }
validate_mxfp8_value_heads:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
  validate_mxfp8_value_blocks:
    for (int block = 0; block < VALUE_BLOCKS; ++block) {
      const mx_scale_t scale = v_scales[head][block];
      v_scales_local[head][block] = scale;
      if (gdn::to_u8(scale) == 255u) return false;
      bool zero = true;
    validate_mxfp8_value_elements:
      for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
        const int index = block * BLOCK_SIZE + lane;
        const mx_element_t value = v[head][index];
        v_local[head][index] = value;
        if (!valid_e4m3(value)) return false;
        zero = zero && (raw_e4m3(value) & 0x7fu) == 0u;
      }
      if (zero && gdn::to_u8(scale) != E8M0_BIAS) return false;
    }
  }
  return true;
}

bool phase1_validate_state(const state_tensor_t state, const state_scale_t state_scales) {
validate_mxfp8_state_heads:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
  validate_mxfp8_state_rows:
    for (int row = 0; row < KEY_DIM; ++row) {
    validate_mxfp8_state_blocks:
      for (int block = 0; block < VALUE_BLOCKS; ++block) {
        if (gdn::to_u8(state_scales[head][row][block]) == 255u) return false;
        bool zero = true;
      validate_mxfp8_state_elements:
        for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
          const mx_element_t value = state[head][row][block * BLOCK_SIZE + lane];
          if (!valid_e4m3(value)) return false;
          zero = zero && (raw_e4m3(value) & 0x7fu) == 0u;
        }
        if (zero && gdn::to_u8(state_scales[head][row][block]) != E8M0_BIAS) return false;
      }
    }
  }
  return true;
}

}  // namespace gdn_mxfp8

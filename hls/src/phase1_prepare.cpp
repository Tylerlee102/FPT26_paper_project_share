#include "gdn_kernel.hpp"

namespace gdn {

namespace {

bool valid_element(mx_e2m1_t value) {
#pragma HLS INLINE
  const unsigned raw = raw_e2m1(value);
  return raw <= 15u && raw != 8u;
}

}  // namespace

bool phase1_validate_token(
    const qk_tensor_t q,
    const qk_scale_tensor_t q_scales,
    const qk_tensor_t k,
    const qk_scale_tensor_t k_scales,
    const value_tensor_t v,
    const value_scale_tensor_t v_scales,
    const q1_15_head_t alpha,
    const q1_15_head_t beta,
    qk_tensor_t q_local,
    qk_scale_tensor_t q_scales_local,
    qk_tensor_t k_local,
    qk_scale_tensor_t k_scales_local,
    value_tensor_t v_local,
    value_scale_tensor_t v_scales_local,
    q1_15_head_t alpha_local,
    q1_15_head_t beta_local) {
validate_q_heads:
  for (int head = 0; head < NUM_QK_HEADS; ++head) {
  validate_q_blocks:
    for (int block = 0; block < QK_BLOCKS; ++block) {
      const mx_scale_t scale = q_scales[head][block];
      q_scales_local[head][block] = scale;
      if (to_u8(scale) == 255u) {
        return false;
      }
      bool q_zero = true;
    validate_q_elements:
      for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
        const int index = block * BLOCK_SIZE + lane;
        const mx_e2m1_t value = q[head][index];
        q_local[head][index] = value;
        if (!valid_element(value)) {
          return false;
        }
        q_zero = q_zero && to_u4(value) == 0u;
      }
      if (q_zero && to_u8(scale) != E8M0_BIAS) {
        return false;
      }
    }
  }

validate_k_heads:
  for (int head = 0; head < NUM_QK_HEADS; ++head) {
  validate_k_blocks:
    for (int block = 0; block < QK_BLOCKS; ++block) {
      const mx_scale_t scale = k_scales[head][block];
      k_scales_local[head][block] = scale;
      if (to_u8(scale) == 255u) {
        return false;
      }
      bool k_zero = true;
    validate_k_elements:
      for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
        const int index = block * BLOCK_SIZE + lane;
        const mx_e2m1_t value = k[head][index];
        k_local[head][index] = value;
        if (!valid_element(value)) {
          return false;
        }
        k_zero = k_zero && to_u4(value) == 0u;
      }
      if (k_zero && to_u8(scale) != E8M0_BIAS) {
        return false;
      }
    }
  }

validate_alpha_heads:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
    const q1_15_t value = alpha[head];
    alpha_local[head] = value;
    if (value > 32768u) {
      return false;
    }
  }

validate_beta_heads:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
    const q1_15_t value = beta[head];
    beta_local[head] = value;
    if (value > 32768u) {
      return false;
    }
  }

validate_value_heads:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
  validate_value_blocks:
    for (int block = 0; block < VALUE_BLOCKS; ++block) {
      const mx_scale_t scale = v_scales[head][block];
      v_scales_local[head][block] = scale;
      if (to_u8(scale) == 255u) {
        return false;
      }
      bool v_zero = true;
    validate_value_elements:
      for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
        const int index = block * BLOCK_SIZE + lane;
        const mx_e2m1_t value = v[head][index];
        v_local[head][index] = value;
        if (!valid_element(value)) {
          return false;
        }
        v_zero = v_zero && to_u4(value) == 0u;
      }
      if (v_zero && to_u8(scale) != E8M0_BIAS) {
        return false;
      }
    }
  }
  return true;
}

bool phase1_validate_state(
    const state_tensor_t state,
    const state_scale_t state_scales) {
validate_state_heads:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
  validate_state_rows:
    for (int row = 0; row < KEY_DIM; ++row) {
    validate_state_blocks:
      for (int block = 0; block < VALUE_BLOCKS; ++block) {
        if (to_u8(state_scales[head][row][block]) == 255u) {
          return false;
        }
        bool zero_block = true;
      validate_state_elements:
        for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
          const int column = block * BLOCK_SIZE + lane;
          if (!valid_element(state[head][row][column])) {
            return false;
          }
          zero_block = zero_block && to_u4(state[head][row][column]) == 0u;
        }
        if (zero_block &&
            to_u8(state_scales[head][row][block]) != E8M0_BIAS) {
          return false;
        }
      }
    }
  }
  return true;
}

}  // namespace gdn

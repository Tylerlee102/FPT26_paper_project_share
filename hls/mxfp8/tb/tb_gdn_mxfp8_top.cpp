#include <cstdint>
#include <iostream>

#include "gdn_mxfp8_kernel.hpp"

namespace {

static gdn_mxfp8::qk_tensor_t q = {};
static gdn_mxfp8::qk_scale_tensor_t q_scales = {};
static gdn_mxfp8::qk_tensor_t k = {};
static gdn_mxfp8::qk_scale_tensor_t k_scales = {};
static gdn_mxfp8::value_tensor_t v = {};
static gdn_mxfp8::value_scale_tensor_t v_scales = {};
static gdn_mxfp8::q1_15_head_t alpha = {};
static gdn_mxfp8::q1_15_head_t beta = {};
static gdn_mxfp8::state_tensor_t state_in = {};
static gdn_mxfp8::state_scale_t state_scales_in = {};
static gdn_mxfp8::output_mantissa_t output_mantissas = {};
static gdn_mxfp8::output_exponent_t output_exponents = {};
static gdn_mxfp8::state_tensor_t state_out = {};
static gdn_mxfp8::state_scale_t state_scales_out = {};
static gdn_mxfp8::status_t status_out[1] = {};
static gdn_mxfp8::generation_t generation_out[1] = {};
static gdn_mxfp8::counter_array_t command_counters = {};
static gdn_mxfp8::counter_array_t cumulative_counters = {};

void invoke(std::uint8_t command, std::uint8_t flags) {
  gdn_mxfp8_top(
      command, 0, 0, flags, q, q_scales, k, k_scales, v, v_scales,
      alpha, beta, state_in, state_scales_in, output_mantissas,
      output_exponents, state_out, state_scales_out, status_out,
      generation_out, command_counters, cumulative_counters);
}

}  // namespace

int main() {
  for (int head = 0; head < gdn_mxfp8::NUM_QK_HEADS; ++head) {
    for (int block = 0; block < gdn_mxfp8::QK_BLOCKS; ++block) {
      q_scales[head][block] = 127;
      k_scales[head][block] = 127;
    }
  }
  for (int head = 0; head < gdn_mxfp8::NUM_VALUE_HEADS; ++head) {
    alpha[head] = 32768;
    beta[head] = 32768;
    for (int block = 0; block < gdn_mxfp8::VALUE_BLOCKS; ++block) {
      v_scales[head][block] = 127;
    }
    for (int row = 0; row < gdn_mxfp8::KEY_DIM; ++row) {
      for (int block = 0; block < gdn_mxfp8::VALUE_BLOCKS; ++block) {
        state_scales_in[head][row][block] = 127;
      }
    }
  }

  invoke(gdn_mxfp8::COMMAND_RESET, gdn_mxfp8::PAYLOAD_NONE);
  if (status_out[0] != gdn_mxfp8::STATUS_OK || generation_out[0] != 0) {
    std::cerr << "RESET failed\n";
    return 1;
  }

  q[0][0] = 0x38;
  k[0][0] = 0x38;
  v[0][0] = 0x38;
  invoke(gdn_mxfp8::COMMAND_STEP, gdn_mxfp8::PAYLOAD_TOKEN);
  if (status_out[0] != gdn_mxfp8::STATUS_OK || generation_out[0] != 1) {
    std::cerr << "STEP failed\n";
    return 1;
  }
  if (output_mantissas[0][0] != 512 || output_exponents[0][0] != -9) {
    std::cerr << "nonzero output mismatch: " << output_mantissas[0][0]
              << " * 2^" << output_exponents[0][0] << "\n";
    return 1;
  }

  invoke(gdn_mxfp8::COMMAND_READBACK, gdn_mxfp8::PAYLOAD_NONE);
  if (status_out[0] != gdn_mxfp8::STATUS_OK || state_out[0][0][0] != 0x78 ||
      state_scales_out[0][0][0] != 119) {
    std::cerr << "resident state mismatch code=" << static_cast<unsigned>(state_out[0][0][0])
              << " scale=" << static_cast<unsigned>(state_scales_out[0][0][0]) << "\n";
    return 1;
  }
  std::cout << "tb_gdn_mxfp8_top PASS\n";
  return 0;
}

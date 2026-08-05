#include "gdn_bf16_kernel.hpp"

#include <cstdint>
#include <iostream>

namespace {

static gdn_bf16::qk_tensor_t q = {};
static gdn_bf16::qk_tensor_t k = {};
static gdn_bf16::value_tensor_t v = {};
static gdn_bf16::head_tensor_t alpha = {};
static gdn_bf16::head_tensor_t beta = {};
static gdn_bf16::state_tensor_t state_in = {};
static gdn_bf16::output_tensor_t output = {};
static gdn_bf16::state_tensor_t state_out = {};
static gdn::status_t status_out[1] = {};
static gdn::generation_t generation_out[1] = {};
static gdn_bf16::counter_array_t command_counters = {};
static gdn_bf16::counter_array_t cumulative_counters = {};

constexpr std::uint16_t BF16_ZERO = 0x0000u;
constexpr std::uint16_t BF16_ONE = 0x3f80u;

bool run_command(
    std::uint8_t command,
    std::uint8_t layer,
    std::uint8_t flags,
    gdn::status_t expected_status,
    gdn::generation_t expected_generation) {
  gdn_bf16_top(
      command,
      0,
      layer,
      flags,
      q,
      k,
      v,
      alpha,
      beta,
      state_in,
      output,
      state_out,
      status_out,
      generation_out,
      command_counters,
      cumulative_counters);
  if (status_out[0] != expected_status ||
      generation_out[0] != expected_generation) {
    std::cerr << "command mismatch command=" << static_cast<int>(command)
              << " status=" << static_cast<int>(status_out[0])
              << " generation=" << generation_out[0] << '\n';
    return false;
  }
  return true;
}

}  // namespace

int main() {
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    alpha[head] = BF16_ONE;
    beta[head] = BF16_ZERO;
  }
  if (!run_command(
          gdn::COMMAND_RESET,
          2,
          gdn::PAYLOAD_NONE,
          gdn::STATUS_OK,
          0)) {
    return 1;
  }

  q[0][0] = BF16_ONE;
  k[0][0] = BF16_ONE;
  v[0][0] = BF16_ONE;
  beta[0] = BF16_ONE;
  if (!run_command(
          gdn::COMMAND_STEP,
          2,
          gdn::PAYLOAD_TOKEN,
          gdn::STATUS_OK,
          1)) {
    return 1;
  }
  if (output[0][0].to_uint() != BF16_ONE) {
    std::cerr << "first BF16 output mismatch: 0x" << std::hex
              << output[0][0].to_uint() << '\n';
    return 1;
  }

  beta[0] = BF16_ZERO;
  v[0][0] = BF16_ZERO;
  if (!run_command(
          gdn::COMMAND_STEP,
          2,
          gdn::PAYLOAD_TOKEN,
          gdn::STATUS_OK,
          2)) {
    return 1;
  }
  if (output[0][0].to_uint() != BF16_ONE) {
    std::cerr << "persistent BF16 output mismatch\n";
    return 1;
  }

  if (!run_command(
          gdn::COMMAND_READBACK,
          2,
          gdn::PAYLOAD_NONE,
          gdn::STATUS_OK,
          2)) {
    return 1;
  }
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
      for (int column = 0; column < gdn::VALUE_DIM; ++column) {
        const unsigned expected =
            head == 0 && row == 0 && column == 0 ? BF16_ONE : BF16_ZERO;
        if (state_out[head][row][column].to_uint() != expected) {
          std::cerr << "BF16 state mismatch at " << head << ',' << row << ','
                    << column << '\n';
          return 1;
        }
      }
    }
  }
  if (cumulative_counters[gdn::COUNTER_COMMITTED_STATE_GENERATIONS] != 2) {
    std::cerr << "BF16 generation counter mismatch\n";
    return 1;
  }
  std::cout << "BF16_HLS_CSIM PASS reset_steps_readback=4 generation=2\n";
  return 0;
}

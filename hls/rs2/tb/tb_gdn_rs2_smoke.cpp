#include "gdn_rs2_kernel.hpp"

#include <iostream>

namespace {

static gdn_rs2::qk_elements_t q_elements{};
static gdn_rs2::qk_scales_t q_scales{};
static gdn_rs2::qk_elements_t k_elements{};
static gdn_rs2::qk_scales_t k_scales{};
static gdn_rs2::value_elements_t v_elements{};
static gdn_rs2::value_scales_t v_scales{};
static gdn_rs2::coefficient_heads_t alpha{};
static gdn_rs2::coefficient_heads_t beta{};
static gdn_rs2::state_primary_elements_t state_primary_in{};
static gdn_rs2::state_scales_t state_primary_scales_in{};
static gdn_rs2::state_residual_elements_t state_residual_in{};
static gdn_rs2::state_scales_t state_residual_scales_in{};
static gdn_rs2::log_key_elements_t log_keys_in{};
static gdn_rs2::log_key_scales_t log_key_scales_in{};
static gdn_rs2::log_update_elements_t log_updates_in{};
static gdn_rs2::log_update_scales_t log_update_scales_in{};
static gdn_rs2::coefficient_heads_t gamma_in{};
static gdn_rs2::lambda_t lambda_in{};
static gdn_rs2::output_mantissas_t output_mantissas{};
static gdn_rs2::output_exponents_t output_exponents{};
static gdn_rs2::state_primary_elements_t state_primary_out{};
static gdn_rs2::state_scales_t state_primary_scales_out{};
static gdn_rs2::state_residual_elements_t state_residual_out{};
static gdn_rs2::state_scales_t state_residual_scales_out{};
static gdn_rs2::log_key_elements_t log_keys_out{};
static gdn_rs2::log_key_scales_t log_key_scales_out{};
static gdn_rs2::log_update_elements_t log_updates_out{};
static gdn_rs2::log_update_scales_t log_update_scales_out{};
static gdn_rs2::coefficient_heads_t gamma_out{};
static gdn_rs2::lambda_t lambda_out{};
static gdn_rs2::live_entries_t live_entries_out[1]{};
static std::uint8_t status_out[1]{};
static gdn_rs2::generation_t generation_out[1]{};
static gdn_rs2::counters_t command_counters{};
static gdn_rs2::counters_t cumulative_counters{};

void initialize_payloads() {
  for (int term = 0; term < gdn_rs2::STACK_DEPTH; ++term) {
    for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
      for (int block = 0; block < gdn::QK_BLOCKS; ++block) {
        q_scales[term][head][block] = gdn_rs2::E8M0_BIAS;
        k_scales[term][head][block] = gdn_rs2::E8M0_BIAS;
      }
    }
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        v_scales[term][head][block] = gdn_rs2::E8M0_BIAS;
      }
    }
  }
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    alpha[head] = gdn_rs2::COEFFICIENT_ONE;
    beta[head] = gdn_rs2::COEFFICIENT_ONE;
    gamma_in[head] = gdn_rs2::COEFFICIENT_ONE;
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        state_primary_scales_in[head][row][block] = gdn_rs2::E8M0_BIAS;
        state_residual_scales_in[head][row][block] = gdn_rs2::E8M0_BIAS;
      }
    }
  }
  for (int entry = 0; entry < gdn_rs2::LOG_CAPACITY; ++entry) {
    for (int term = 0; term < gdn_rs2::STACK_DEPTH; ++term) {
      for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
        for (int block = 0; block < gdn::QK_BLOCKS; ++block) {
          log_key_scales_in[entry][term][head][block] = gdn_rs2::E8M0_BIAS;
        }
      }
      for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
        for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
          log_update_scales_in[entry][term][head][block] = gdn_rs2::E8M0_BIAS;
        }
      }
    }
  }
}

void invoke(
    std::uint8_t command,
    std::uint8_t layer,
    std::uint8_t payload,
    gdn_rs2::live_entries_t live = 0) {
  gdn_rs2_top(
      command,
      0,
      layer,
      payload,
      q_elements,
      q_scales,
      k_elements,
      k_scales,
      v_elements,
      v_scales,
      alpha,
      beta,
      state_primary_in,
      state_primary_scales_in,
      state_residual_in,
      state_residual_scales_in,
      log_keys_in,
      log_key_scales_in,
      log_updates_in,
      log_update_scales_in,
      gamma_in,
      lambda_in,
      live,
      output_mantissas,
      output_exponents,
      state_primary_out,
      state_primary_scales_out,
      state_residual_out,
      state_residual_scales_out,
      log_keys_out,
      log_key_scales_out,
      log_updates_out,
      log_update_scales_out,
      gamma_out,
      lambda_out,
      live_entries_out,
      status_out,
      generation_out,
      command_counters,
      cumulative_counters);
}

bool expect_status(std::uint8_t expected, const char *label) {
  if (status_out[0] != expected) {
    std::cerr << label << " status=" << static_cast<unsigned>(status_out[0])
              << " expected=" << static_cast<unsigned>(expected) << "\n";
    return false;
  }
  return true;
}

}  // namespace

int main() {
  initialize_payloads();
  invoke(gdn::COMMAND_STEP, 0, gdn::PAYLOAD_TOKEN);
  if (!expect_status(gdn::STATUS_UNINITIALIZED_STATE, "uninitialized step")) {
    return 1;
  }
  invoke(gdn::COMMAND_RESET, 0, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_OK, "reset") || generation_out[0] != 0) {
    return 1;
  }
  for (int token = 0; token < gdn_rs2::LOG_CAPACITY; ++token) {
    invoke(gdn::COMMAND_STEP, 0, gdn::PAYLOAD_TOKEN);
    if (!expect_status(gdn::STATUS_OK, "zero step") ||
        generation_out[0] != static_cast<unsigned>(token + 1)) {
      return 1;
    }
    const unsigned expected_live = token + 1 == gdn_rs2::LOG_CAPACITY
        ? 0u
        : static_cast<unsigned>(token + 1);
    if (live_entries_out[0].to_uint() != expected_live) {
      std::cerr << "live-entry mismatch at token " << token + 1 << "\n";
      return 1;
    }
  }
  if (cumulative_counters[gdn_rs2::COUNTER_FOLDS].to_uint64() != 1 ||
      cumulative_counters[gdn_rs2::COUNTER_COMMITTED_GENERATIONS].to_uint64() !=
          gdn_rs2::LOG_CAPACITY) {
    std::cerr << "fold/generation counters mismatch\n";
    return 1;
  }
  invoke(gdn::COMMAND_READBACK, 0, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_OK, "readback") ||
      live_entries_out[0] != 0 || gamma_out[0] != gdn_rs2::COEFFICIENT_ONE ||
      state_primary_out[0][0][0] != 0 || state_residual_out[0][0][0] != 0 ||
      state_primary_scales_out[0][0][0] != gdn_rs2::E8M0_BIAS ||
      state_residual_scales_out[0][0][0] != gdn_rs2::E8M0_BIAS) {
    return 1;
  }

  state_primary_in[0][0][0] = 2;
  invoke(gdn::COMMAND_LOAD, 1, gdn::PAYLOAD_STATE);
  if (!expect_status(gdn::STATUS_OK, "load") || generation_out[0] != 1) {
    return 1;
  }
  invoke(gdn::COMMAND_READBACK, 1, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_OK, "loaded readback") ||
      state_primary_out[0][0][0] != 2 || live_entries_out[0] != 0) {
    return 1;
  }

  q_elements[0][0][0] = 8;
  invoke(gdn::COMMAND_STEP, 1, gdn::PAYLOAD_TOKEN);
  if (!expect_status(gdn::STATUS_INVALID_ENCODING, "invalid token") ||
      generation_out[0] != 1) {
    return 1;
  }
  q_elements[0][0][0] = 0;

  invoke(gdn::COMMAND_RESET, gdn::NUM_LAYERS - 1, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_OK, "last-layer reset")) {
    return 1;
  }
  invoke(gdn::COMMAND_RESET, gdn::NUM_LAYERS, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_INVALID_LAYER_ID, "invalid layer")) {
    return 1;
  }

  std::cout << "PASS: RS2 resident smoke commands, three-token fold, snapshot, and layer bounds\n";
  return 0;
}

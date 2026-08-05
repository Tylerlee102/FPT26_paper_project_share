#include "gdn_e2m0_kernel.hpp"

#include <iostream>

namespace {

static gdn_e2m0::qk_elements_t q_elements{};
static gdn_e2m0::qk_scales_t q_scales{};
static gdn_e2m0::qk_elements_t k_elements{};
static gdn_e2m0::qk_scales_t k_scales{};
static gdn_e2m0::value_elements_t v_elements{};
static gdn_e2m0::value_scales_t v_scales{};
static gdn_e2m0::coefficient_heads_t alpha{};
static gdn_e2m0::coefficient_heads_t beta{};
static gdn_e2m0::state_primary_elements_t state_primary_in{};
static gdn_e2m0::state_scales_t state_primary_scales_in{};
static gdn_e2m0::state_residual_elements_t state_residual_in{};
static gdn_e2m0::state_scales_t state_residual_scales_in{};
static gdn_e2m0::log_key_elements_t log_keys_in{};
static gdn_e2m0::log_key_scales_t log_key_scales_in{};
static gdn_e2m0::log_update_elements_t log_updates_in{};
static gdn_e2m0::log_update_scales_t log_update_scales_in{};
static gdn_e2m0::coefficient_heads_t gamma_in{};
static gdn_e2m0::lambda_t lambda_in{};
static gdn_e2m0::output_mantissas_t output_mantissas{};
static gdn_e2m0::output_exponents_t output_exponents{};
static gdn_e2m0::state_primary_elements_t state_primary_out{};
static gdn_e2m0::state_scales_t state_primary_scales_out{};
static gdn_e2m0::state_residual_elements_t state_residual_out{};
static gdn_e2m0::state_scales_t state_residual_scales_out{};
static gdn_e2m0::log_key_elements_t log_keys_out{};
static gdn_e2m0::log_key_scales_t log_key_scales_out{};
static gdn_e2m0::log_update_elements_t log_updates_out{};
static gdn_e2m0::log_update_scales_t log_update_scales_out{};
static gdn_e2m0::coefficient_heads_t gamma_out{};
static gdn_e2m0::lambda_t lambda_out{};
static gdn_e2m0::live_entries_t live_entries_out[1]{};
static std::uint8_t status_out[1]{};
static gdn_e2m0::generation_t generation_out[1]{};
static gdn_e2m0::counters_t command_counters{};
static gdn_e2m0::counters_t cumulative_counters{};

void invoke(std::uint8_t command, std::uint8_t layer, std::uint8_t payload) {
  gdn_e2m0_top(
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
      0,
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

bool counters_are_zero() {
  for (int index = 0; index < gdn_e2m0::COUNTER_COUNT; ++index) {
    if (command_counters[index] != 0 || cumulative_counters[index] != 0) {
      return false;
    }
  }
  return true;
}

}  // namespace

int main() {
  invoke(gdn::COMMAND_RESET, gdn::NUM_LAYERS, gdn::PAYLOAD_NONE);
  if (status_out[0] != gdn::STATUS_INVALID_LAYER_ID || generation_out[0] != 0 ||
      !counters_are_zero()) {
    std::cerr << "invalid-layer RTL control result mismatch\n";
    return 1;
  }

  invoke(gdn::COMMAND_STEP, 0, gdn::PAYLOAD_TOKEN);
  if (status_out[0] != gdn::STATUS_UNINITIALIZED_STATE ||
      generation_out[0] != 0 || !counters_are_zero() ||
      output_mantissas[0][0] != 0 || output_exponents[0][0] != 0) {
    std::cerr << "uninitialized-step RTL control result mismatch\n";
    return 1;
  }

  std::cout
      << "PASS: corrected E2M0 generated-RTL control smoke, two exact commands\n";
  return 0;
}

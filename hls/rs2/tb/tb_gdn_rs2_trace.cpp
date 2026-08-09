#include "gdn_rs2_kernel.hpp"

#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <vector>

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

template <typename T>
bool read_scalar(std::ifstream &input, T &value) {
  input.read(reinterpret_cast<char *>(&value), sizeof(value));
  return static_cast<bool>(input);
}

template <typename T>
bool read_native(std::ifstream &input, T *values, std::size_t count) {
  input.read(reinterpret_cast<char *>(values), sizeof(T) * count);
  return static_cast<bool>(input);
}

template <typename T>
bool read_u8(std::ifstream &input, T *values, std::size_t count) {
  std::vector<std::uint8_t> bytes(count);
  input.read(reinterpret_cast<char *>(bytes.data()), bytes.size());
  if (!input) {
    return false;
  }
  for (std::size_t index = 0; index < count; ++index) {
    values[index] = bytes[index];
  }
  return true;
}

template <typename T>
bool read_u16(std::ifstream &input, T *values, std::size_t count) {
  std::vector<std::uint16_t> words(count);
  if (!read_native(input, words.data(), count)) {
    return false;
  }
  for (std::size_t index = 0; index < count; ++index) {
    values[index] = words[index];
  }
  return true;
}

bool read_snapshot_input(std::ifstream &input, std::uint8_t &live) {
  return read_u8(
             input,
             &state_primary_in[0][0][0],
             gdn::NUM_VALUE_HEADS * gdn::KEY_DIM * gdn::VALUE_DIM) &&
         read_u8(
             input,
             &state_primary_scales_in[0][0][0],
             gdn::NUM_VALUE_HEADS * gdn::KEY_DIM * gdn::VALUE_BLOCKS) &&
         read_u8(
             input,
             &state_residual_in[0][0][0],
             gdn::NUM_VALUE_HEADS * gdn::KEY_DIM * gdn::VALUE_DIM) &&
         read_u8(
             input,
             &state_residual_scales_in[0][0][0],
             gdn::NUM_VALUE_HEADS * gdn::KEY_DIM * gdn::VALUE_BLOCKS) &&
         read_u8(
             input,
             &log_keys_in[0][0][0][0],
             gdn_rs2::LOG_CAPACITY * gdn_rs2::STACK_DEPTH *
                 gdn::NUM_QK_HEADS * gdn::KEY_DIM) &&
         read_u8(
             input,
             &log_key_scales_in[0][0][0][0],
             gdn_rs2::LOG_CAPACITY * gdn_rs2::STACK_DEPTH *
                 gdn::NUM_QK_HEADS * gdn::QK_BLOCKS) &&
         read_u8(
             input,
             &log_updates_in[0][0][0][0],
             gdn_rs2::LOG_CAPACITY * gdn_rs2::STACK_DEPTH *
                 gdn::NUM_VALUE_HEADS * gdn::VALUE_DIM) &&
         read_u8(
             input,
             &log_update_scales_in[0][0][0][0],
             gdn_rs2::LOG_CAPACITY * gdn_rs2::STACK_DEPTH *
                 gdn::NUM_VALUE_HEADS * gdn::VALUE_BLOCKS) &&
         read_u16(input, &gamma_in[0], gdn::NUM_VALUE_HEADS) &&
         read_u16(
             input,
             &lambda_in[0][0],
             gdn_rs2::LOG_CAPACITY * gdn::NUM_VALUE_HEADS) &&
         read_scalar(input, live);
}

bool read_token(std::ifstream &input) {
  return read_u8(
             input,
             &q_elements[0][0][0],
             gdn_rs2::STACK_DEPTH * gdn::NUM_QK_HEADS * gdn::KEY_DIM) &&
         read_u8(
             input,
             &q_scales[0][0][0],
             gdn_rs2::STACK_DEPTH * gdn::NUM_QK_HEADS * gdn::QK_BLOCKS) &&
         read_u8(
             input,
             &k_elements[0][0][0],
             gdn_rs2::STACK_DEPTH * gdn::NUM_QK_HEADS * gdn::KEY_DIM) &&
         read_u8(
             input,
             &k_scales[0][0][0],
             gdn_rs2::STACK_DEPTH * gdn::NUM_QK_HEADS * gdn::QK_BLOCKS) &&
         read_u8(
             input,
             &v_elements[0][0][0],
             gdn_rs2::STACK_DEPTH * gdn::NUM_VALUE_HEADS * gdn::VALUE_DIM) &&
         read_u8(
             input,
             &v_scales[0][0][0],
             gdn_rs2::STACK_DEPTH * gdn::NUM_VALUE_HEADS * gdn::VALUE_BLOCKS) &&
         read_u16(input, &alpha[0], gdn::NUM_VALUE_HEADS) &&
         read_u16(input, &beta[0], gdn::NUM_VALUE_HEADS);
}

void invoke(
    std::uint8_t command,
    std::uint8_t payload,
    gdn_rs2::live_entries_t live = 0) {
  gdn_rs2_top(
      command,
      0,
      4,
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

template <typename T>
bool compare_u8_snapshot(
    std::ifstream &input,
    const T *actual,
    std::size_t count,
    const char *label) {
  std::vector<std::uint8_t> expected(count);
  input.read(reinterpret_cast<char *>(expected.data()), expected.size());
  if (!input) {
    return false;
  }
  for (std::size_t index = 0; index < count; ++index) {
    if (actual[index].to_uint() != expected[index]) {
      std::cerr << label << " mismatch at flat index " << index << "\n";
      return false;
    }
  }
  return true;
}

template <typename T>
bool compare_u16_snapshot(
    std::ifstream &input,
    const T *actual,
    std::size_t count,
    const char *label) {
  std::vector<std::uint16_t> expected(count);
  if (!read_native(input, expected.data(), count)) {
    return false;
  }
  for (std::size_t index = 0; index < count; ++index) {
    if (actual[index].to_uint() != expected[index]) {
      std::cerr << label << " mismatch at flat index " << index << "\n";
      return false;
    }
  }
  return true;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "expected encoded trace path\n";
    return 2;
  }
  std::ifstream input(argv[1], std::ios::binary);
  if (!input) {
    std::cerr << "cannot open " << argv[1] << "\n";
    return 2;
  }
  char magic[8]{};
  std::uint32_t header[10]{};
  input.read(magic, sizeof(magic));
  if (!read_native(input, header, 10) || std::memcmp(magic, "RS2T001", 7) != 0 ||
      (header[0] != 1 && header[0] != 2) || header[1] != 0x01020304u ||
      header[3] != gdn::NUM_QK_HEADS || header[4] != gdn::NUM_VALUE_HEADS ||
      header[5] != gdn::KEY_DIM || header[6] != gdn::VALUE_DIM ||
      header[7] != gdn::BLOCK_SIZE || header[8] != gdn_rs2::STACK_DEPTH ||
      header[9] != gdn_rs2::LOG_CAPACITY) {
    std::cerr << "trace header mismatch\n";
    return 2;
  }
  const std::uint32_t tokens = header[2];
  const bool reset_initialized = header[0] == 2;
  std::uint8_t initial_live = 0;
  if (!read_snapshot_input(input, initial_live)) {
    std::cerr << "short initial snapshot\n";
    return 2;
  }
  invoke(
      reset_initialized ? gdn::COMMAND_RESET : gdn::COMMAND_LOAD,
      reset_initialized ? gdn::PAYLOAD_NONE : gdn::PAYLOAD_STATE,
      initial_live);
  const std::uint64_t initial_generation = reset_initialized ? 0 : 1;
  if (status_out[0] != gdn::STATUS_OK ||
      generation_out[0].to_uint64() != initial_generation ||
      live_entries_out[0] != 0) {
    std::cerr << "initial " << (reset_initialized ? "RESET" : "LOAD")
              << " failed\n";
    return 1;
  }

  std::vector<std::int32_t> expected_m(
      gdn::NUM_VALUE_HEADS * gdn::VALUE_DIM);
  std::vector<std::int16_t> expected_x(
      gdn::NUM_VALUE_HEADS * gdn::VALUE_DIM);
  for (std::uint32_t token = 0; token < tokens; ++token) {
    if (!read_token(input)) {
      std::cerr << "short token input " << token + 1 << "\n";
      return 2;
    }
    std::uint8_t expected_status = 0;
    std::uint64_t expected_generation = 0;
    std::uint8_t expected_live = 0;
    std::uint64_t expected_command[gdn_rs2::COUNTER_COUNT]{};
    std::uint64_t expected_cumulative[gdn_rs2::COUNTER_COUNT]{};
    if (!read_scalar(input, expected_status) ||
        !read_scalar(input, expected_generation) ||
        !read_scalar(input, expected_live) ||
        !read_native(input, expected_command, gdn_rs2::COUNTER_COUNT) ||
        !read_native(input, expected_cumulative, gdn_rs2::COUNTER_COUNT) ||
        !read_native(input, expected_m.data(), expected_m.size()) ||
        !read_native(input, expected_x.data(), expected_x.size())) {
      std::cerr << "short expected record " << token + 1 << "\n";
      return 2;
    }
    invoke(gdn::COMMAND_STEP, gdn::PAYLOAD_TOKEN);
    if (status_out[0] != expected_status ||
        generation_out[0].to_uint64() != expected_generation ||
        live_entries_out[0].to_uint() != expected_live) {
      std::cerr << "metadata mismatch token " << token + 1 << "\n";
      return 1;
    }
    for (int counter = 0; counter < gdn_rs2::COUNTER_COUNT; ++counter) {
      if (command_counters[counter].to_uint64() != expected_command[counter] ||
          cumulative_counters[counter].to_uint64() != expected_cumulative[counter]) {
        std::cerr << "counter mismatch token " << token + 1
                  << " counter " << counter << " actual command "
                  << command_counters[counter].to_uint64() << " expected "
                  << expected_command[counter] << "\n";
        return 1;
      }
    }
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
      for (int column = 0; column < gdn::VALUE_DIM; ++column) {
        const std::size_t index = head * gdn::VALUE_DIM + column;
        if (output_mantissas[head][column].to_int() != expected_m[index] ||
            output_exponents[head][column].to_int() != expected_x[index]) {
          std::cerr << "output mismatch token " << token + 1
                    << " head " << head << " column " << column
                    << " actual (" << output_mantissas[head][column].to_int()
                    << "," << output_exponents[head][column].to_int()
                    << ") expected (" << expected_m[index] << ","
                    << expected_x[index] << ")\n";
          return 1;
        }
      }
    }
  }

  invoke(gdn::COMMAND_READBACK, gdn::PAYLOAD_NONE);
  const std::size_t state_elements =
      gdn::NUM_VALUE_HEADS * gdn::KEY_DIM * gdn::VALUE_DIM;
  const std::size_t state_scales =
      gdn::NUM_VALUE_HEADS * gdn::KEY_DIM * gdn::VALUE_BLOCKS;
  const std::size_t key_elements =
      gdn_rs2::LOG_CAPACITY * gdn_rs2::STACK_DEPTH *
      gdn::NUM_QK_HEADS * gdn::KEY_DIM;
  const std::size_t key_scales =
      gdn_rs2::LOG_CAPACITY * gdn_rs2::STACK_DEPTH *
      gdn::NUM_QK_HEADS * gdn::QK_BLOCKS;
  const std::size_t update_elements =
      gdn_rs2::LOG_CAPACITY * gdn_rs2::STACK_DEPTH *
      gdn::NUM_VALUE_HEADS * gdn::VALUE_DIM;
  const std::size_t update_scales =
      gdn_rs2::LOG_CAPACITY * gdn_rs2::STACK_DEPTH *
      gdn::NUM_VALUE_HEADS * gdn::VALUE_BLOCKS;
  if (!compare_u8_snapshot(input, &state_primary_out[0][0][0], state_elements, "primary") ||
      !compare_u8_snapshot(input, &state_primary_scales_out[0][0][0], state_scales, "primary scales") ||
      !compare_u8_snapshot(input, &state_residual_out[0][0][0], state_elements, "residual") ||
      !compare_u8_snapshot(input, &state_residual_scales_out[0][0][0], state_scales, "residual scales") ||
      !compare_u8_snapshot(input, &log_keys_out[0][0][0][0], key_elements, "keys") ||
      !compare_u8_snapshot(input, &log_key_scales_out[0][0][0][0], key_scales, "key scales") ||
      !compare_u8_snapshot(input, &log_updates_out[0][0][0][0], update_elements, "updates") ||
      !compare_u8_snapshot(input, &log_update_scales_out[0][0][0][0], update_scales, "update scales") ||
      !compare_u16_snapshot(input, &gamma_out[0], gdn::NUM_VALUE_HEADS, "gamma") ||
      !compare_u16_snapshot(
          input,
          &lambda_out[0][0],
          gdn_rs2::LOG_CAPACITY * gdn::NUM_VALUE_HEADS,
          "lambda")) {
    return 1;
  }
  std::uint8_t expected_live = 0;
  std::uint8_t expected_status = 0;
  std::uint64_t expected_generation = 0;
  std::uint64_t expected_cumulative[gdn_rs2::COUNTER_COUNT]{};
  if (!read_scalar(input, expected_live) ||
      !read_scalar(input, expected_status) ||
      !read_scalar(input, expected_generation) ||
      !read_native(input, expected_cumulative, gdn_rs2::COUNTER_COUNT)) {
    std::cerr << "short final metadata\n";
    return 2;
  }
  if (live_entries_out[0].to_uint() != expected_live ||
      status_out[0] != expected_status ||
      generation_out[0].to_uint64() != expected_generation) {
    std::cerr << "final readback metadata mismatch\n";
    return 1;
  }
  for (int counter = 0; counter < gdn_rs2::COUNTER_COUNT; ++counter) {
    if (cumulative_counters[counter].to_uint64() != expected_cumulative[counter]) {
      std::cerr << "final cumulative counter mismatch " << counter << "\n";
      return 1;
    }
  }
  char trailing = 0;
  if (input.read(&trailing, 1)) {
    std::cerr << "trailing trace bytes\n";
    return 2;
  }
  std::cout << "PASS: " << tokens
            << " encoded " << (reset_initialized ? "reset-state" : "random-state")
            << " tokens, exact outputs/counters, and final snapshot\n";
  return 0;
}

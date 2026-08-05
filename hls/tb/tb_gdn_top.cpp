#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "gdn_kernel.hpp"

#ifndef GDN_TB_VECTORS
#define GDN_TB_VECTORS 64
#endif

namespace {

static gdn::qk_tensor_t q{};
static gdn::qk_scale_tensor_t q_scales{};
static gdn::qk_tensor_t k{};
static gdn::qk_scale_tensor_t k_scales{};
static gdn::value_tensor_t v{};
static gdn::value_scale_tensor_t v_scales{};
static gdn::q1_15_head_t alpha{};
static gdn::q1_15_head_t beta{};
static gdn::state_tensor_t state_in{};
static gdn::state_scale_t state_scales_in{};
static gdn::output_mantissa_t output_mantissas{};
static gdn::output_exponent_t output_exponents{};
static gdn::state_tensor_t state_out{};
static gdn::state_scale_t state_scales_out{};
static gdn::status_t status_out[1]{};
static gdn::generation_t generation_out[1]{};
static gdn::counter_array_t command_counters{};
static gdn::counter_array_t cumulative_counters{};
static gdn::output_mantissa_t expected_output_mantissas{};
static gdn::output_exponent_t expected_output_exponents{};
static gdn::counter_array_t expected_command_counters{};
static gdn::counter_array_t expected_cumulative_counters{};

void clear_payloads() {
  for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
    for (int block = 0; block < gdn::QK_BLOCKS; ++block) {
      q_scales[head][block] = 127;
      k_scales[head][block] = 127;
    }
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
      q[head][row] = 0;
      k[head][row] = 0;
    }
  }
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    alpha[head] = 32768;
    beta[head] = 32768;
    for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
      v_scales[head][block] = 127;
    }
    for (int column = 0; column < gdn::VALUE_DIM; ++column) {
      v[head][column] = 0;
    }
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        state_scales_in[head][row][block] = 127;
      }
      for (int column = 0; column < gdn::VALUE_DIM; ++column) {
        state_in[head][row][column] = 0;
      }
    }
  }
}

void invoke(
    std::uint8_t command,
    std::uint16_t sequence,
    std::uint8_t layer,
    std::uint8_t flags) {
  gdn_top(
      command,
      sequence,
      layer,
      flags,
      q,
      q_scales,
      k,
      k_scales,
      v,
      v_scales,
      alpha,
      beta,
      state_in,
      state_scales_in,
      output_mantissas,
      output_exponents,
      state_out,
      state_scales_out,
      status_out,
      generation_out,
      command_counters,
      cumulative_counters);
}

bool expect_status(gdn::ResidentStatus expected, const char *label) {
  if (status_out[0] != expected) {
    std::cerr << label << " status=" << static_cast<int>(status_out[0])
              << " expected=" << static_cast<int>(expected) << "\n";
    return false;
  }
  return true;
}

template <typename T>
bool read_scalar(std::ifstream &input, T &value) {
  input.read(reinterpret_cast<char *>(&value), sizeof(T));
  return static_cast<bool>(input);
}

template <typename T>
bool read_native_array(std::ifstream &input, T *values, std::size_t count) {
  input.read(reinterpret_cast<char *>(values), sizeof(T) * count);
  return static_cast<bool>(input);
}

template <typename T>
bool read_u8_array(std::ifstream &input, T *values, std::size_t count) {
  std::vector<std::uint8_t> bytes(count);
  input.read(reinterpret_cast<char *>(bytes.data()), bytes.size());
  if (!input) {
    return false;
  }
  for (std::size_t index = 0; index < count; ++index) {
    values[index] = static_cast<T>(bytes[index]);
  }
  return true;
}

bool read_trace_inputs(std::ifstream &input) {
  return read_u8_array(input, &q[0][0], gdn::NUM_QK_HEADS * gdn::KEY_DIM) &&
         read_u8_array(
             input, &q_scales[0][0], gdn::NUM_QK_HEADS * gdn::QK_BLOCKS) &&
         read_u8_array(input, &k[0][0], gdn::NUM_QK_HEADS * gdn::KEY_DIM) &&
         read_u8_array(
             input, &k_scales[0][0], gdn::NUM_QK_HEADS * gdn::QK_BLOCKS) &&
         read_u8_array(
             input, &v[0][0], gdn::NUM_VALUE_HEADS * gdn::VALUE_DIM) &&
         read_u8_array(
             input,
             &v_scales[0][0],
             gdn::NUM_VALUE_HEADS * gdn::VALUE_BLOCKS) &&
         read_native_array(input, &alpha[0], gdn::NUM_VALUE_HEADS) &&
         read_native_array(input, &beta[0], gdn::NUM_VALUE_HEADS);
}

bool compare_trace_output(int token) {
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    for (int column = 0; column < gdn::VALUE_DIM; ++column) {
      if (output_mantissas[head][column] !=
              expected_output_mantissas[head][column] ||
          output_exponents[head][column] !=
              expected_output_exponents[head][column]) {
        std::cerr << "oracle output mismatch token=" << token
                  << " head=" << head << " column=" << column << " got=("
                  << output_mantissas[head][column] << ","
                  << output_exponents[head][column] << ") expected=("
                  << expected_output_mantissas[head][column] << ","
                  << expected_output_exponents[head][column] << ")\n";
        return false;
      }
    }
  }
  return true;
}

}  // namespace

int main(int argc, char **argv) {
  clear_payloads();

  invoke(gdn::COMMAND_STEP, 0, 0, gdn::PAYLOAD_TOKEN);
  if (!expect_status(gdn::STATUS_UNINITIALIZED_STATE, "uninitialized STEP") ||
      command_counters[gdn::COUNTER_REJECTED_COMMANDS] != 1 ||
      generation_out[0] != 0) {
    return 1;
  }

  invoke(gdn::COMMAND_RESET, 0, 0, gdn::PAYLOAD_TOKEN);
  if (!expect_status(gdn::STATUS_UNEXPECTED_PAYLOAD, "RESET payload")) {
    return 1;
  }

  invoke(gdn::COMMAND_RESET, 0, 0, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_OK, "RESET") || generation_out[0] != 0) {
    return 1;
  }
  for (int counter = 0; counter < gdn::COUNTER_COUNT; ++counter) {
    if (cumulative_counters[counter] != 0) {
      std::cerr << "RESET did not clear counter " << counter << "\n";
      return 1;
    }
  }

  const int pivot = 0;
  for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
    q[head][pivot] = 2;
    k[head][pivot] = 2;
  }
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    for (int column = 0; column < gdn::VALUE_DIM; ++column) {
      v[head][column] = 2;
    }
  }

  for (int token = 0; token < GDN_TB_VECTORS; ++token) {
    invoke(gdn::COMMAND_STEP, 0, 0, gdn::PAYLOAD_TOKEN);
    if (!expect_status(gdn::STATUS_OK, "STEP") ||
        generation_out[0] != static_cast<gdn::generation_t>(token + 1) ||
        command_counters[gdn::COUNTER_COMMITTED_STATE_GENERATIONS] != 1) {
      return 1;
    }
    const gdn::mantissa_t expected_mantissa = token == 0 ? 8 : 16;
    const gdn::exponent_t expected_exponent = token == 0 ? -3 : -4;
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
      for (int column = 0; column < gdn::VALUE_DIM; ++column) {
        if (output_mantissas[head][column] != expected_mantissa ||
            output_exponents[head][column] != expected_exponent) {
          std::cerr << "STEP output mismatch token=" << token
                    << " head=" << head << " column=" << column
                    << " got=(" << output_mantissas[head][column] << ","
                    << output_exponents[head][column] << ") expected=("
                    << expected_mantissa << "," << expected_exponent << ")\n";
          return 1;
        }
      }
    }
  }

  q[0][0] = 8;
  invoke(gdn::COMMAND_STEP, 0, 0, gdn::PAYLOAD_TOKEN);
  if (!expect_status(gdn::STATUS_INVALID_ENCODING, "invalid STEP") ||
      generation_out[0] != GDN_TB_VECTORS ||
      command_counters[gdn::COUNTER_INVALID_ENCODINGS] != 1 ||
      command_counters[gdn::COUNTER_REJECTED_COMMANDS] != 1) {
    return 1;
  }
  q[0][0] = 2;

  invoke(gdn::COMMAND_READBACK, 0, 0, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_OK, "READBACK") ||
      generation_out[0] != GDN_TB_VECTORS) {
    return 1;
  }
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        const unsigned expected_scale = row == pivot ? 125u : 127u;
        if (gdn::to_u8(state_scales_out[head][row][block]) != expected_scale) {
          std::cerr << "READBACK scale mismatch\n";
          return 1;
        }
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
          const int column = block * gdn::BLOCK_SIZE + lane;
          const unsigned expected_code = row == pivot ? 6u : 0u;
          if (gdn::to_u4(state_out[head][row][column]) != expected_code) {
            std::cerr << "READBACK state mismatch\n";
            return 1;
          }
        }
      }
    }
  }
  if (cumulative_counters[gdn::COUNTER_COMMITTED_STATE_GENERATIONS] !=
          GDN_TB_VECTORS ||
      cumulative_counters[gdn::COUNTER_INVALID_ENCODINGS] != 1 ||
      cumulative_counters[gdn::COUNTER_REJECTED_COMMANDS] != 1) {
    std::cerr << "cumulative counters mismatch\n";
    return 1;
  }

  invoke(gdn::COMMAND_RESET, 0, 1, gdn::PAYLOAD_NONE);
  invoke(gdn::COMMAND_READBACK, 0, 1, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_OK, "isolated READBACK") ||
      generation_out[0] != 0 || gdn::to_u4(state_out[0][0][0]) != 0u ||
      gdn::to_u8(state_scales_out[0][0][0]) != 127u) {
    return 1;
  }

  invoke(gdn::COMMAND_LOAD, 0, 2, gdn::PAYLOAD_STATE);
  if (!expect_status(gdn::STATUS_OK, "LOAD") || generation_out[0] != 1) {
    return 1;
  }
  state_in[0][0][0] = 8;
  invoke(gdn::COMMAND_LOAD, 0, 2, gdn::PAYLOAD_STATE);
  if (!expect_status(gdn::STATUS_INVALID_ENCODING, "invalid LOAD") ||
      generation_out[0] != 1) {
    return 1;
  }
  state_in[0][0][0] = 0;
  invoke(gdn::COMMAND_READBACK, 0, 2, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_OK, "atomic LOAD READBACK") ||
      gdn::to_u4(state_out[0][0][0]) != 0u || generation_out[0] != 1) {
    return 1;
  }

  invoke(gdn::COMMAND_RESET, 0, gdn::NUM_LAYERS, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_INVALID_LAYER_ID, "invalid layer") ||
      cumulative_counters[gdn::COUNTER_REJECTED_COMMANDS] != 0) {
    return 1;
  }

  if (argc != 2) {
    std::cerr << "expected corrected oracle trace path\n";
    return 1;
  }
  std::ifstream trace(argv[1], std::ios::binary);
  if (!trace) {
    std::cerr << "cannot open oracle trace: " << argv[1] << "\n";
    return 1;
  }

  char magic[8]{};
  std::uint32_t version = 0;
  std::uint32_t endian_marker = 0;
  std::uint32_t trace_tokens = 0;
  std::uint32_t num_qk_heads = 0;
  std::uint32_t num_value_heads = 0;
  std::uint32_t key_dim = 0;
  std::uint32_t value_dim = 0;
  std::uint32_t block_size = 0;
  trace.read(magic, sizeof(magic));
  if (!read_scalar(trace, version) || !read_scalar(trace, endian_marker) ||
      !read_scalar(trace, trace_tokens) || !read_scalar(trace, num_qk_heads) ||
      !read_scalar(trace, num_value_heads) || !read_scalar(trace, key_dim) ||
      !read_scalar(trace, value_dim) || !read_scalar(trace, block_size)) {
    std::cerr << "short oracle trace header\n";
    return 1;
  }
  if (std::memcmp(magic, "GDNTRC01", 8) != 0 || version != 1 ||
      endian_marker != 0x01020304u || trace_tokens != GDN_TB_VECTORS ||
      num_qk_heads != gdn::NUM_QK_HEADS ||
      num_value_heads != gdn::NUM_VALUE_HEADS || key_dim != gdn::KEY_DIM ||
      value_dim != gdn::VALUE_DIM || block_size != gdn::BLOCK_SIZE) {
    std::cerr << "oracle trace header mismatch\n";
    return 1;
  }

  invoke(gdn::COMMAND_RESET, 0, 3, gdn::PAYLOAD_NONE);
  if (!expect_status(gdn::STATUS_OK, "oracle RESET")) {
    return 1;
  }
  for (std::uint32_t token = 0; token < trace_tokens; ++token) {
    if (!read_trace_inputs(trace)) {
      std::cerr << "short oracle input record token=" << token + 1 << "\n";
      return 1;
    }
    std::uint8_t expected_status = 0;
    std::uint64_t expected_generation = 0;
    if (!read_scalar(trace, expected_status) ||
        !read_scalar(trace, expected_generation) ||
        !read_native_array(
            trace, &expected_command_counters[0], gdn::COUNTER_COUNT) ||
        !read_native_array(
            trace, &expected_cumulative_counters[0], gdn::COUNTER_COUNT) ||
        !read_native_array(
            trace,
            &expected_output_mantissas[0][0],
            gdn::NUM_VALUE_HEADS * gdn::VALUE_DIM) ||
        !read_native_array(
            trace,
            &expected_output_exponents[0][0],
            gdn::NUM_VALUE_HEADS * gdn::VALUE_DIM)) {
      std::cerr << "short oracle expected record token=" << token + 1 << "\n";
      return 1;
    }

    invoke(gdn::COMMAND_STEP, 0, 3, gdn::PAYLOAD_TOKEN);
    if (status_out[0] != expected_status ||
        generation_out[0] != expected_generation ||
        !compare_trace_output(token + 1)) {
      return 1;
    }
    for (int counter = 0; counter < gdn::COUNTER_COUNT; ++counter) {
      if (command_counters[counter] != expected_command_counters[counter] ||
          cumulative_counters[counter] != expected_cumulative_counters[counter]) {
        std::cerr << "oracle counter mismatch token=" << token + 1
                  << " counter=" << counter << " command="
                  << command_counters[counter] << " expected_command="
                  << expected_command_counters[counter] << " cumulative="
                  << cumulative_counters[counter] << " expected_cumulative="
                  << expected_cumulative_counters[counter] << "\n";
        return 1;
      }
    }
  }

  std::vector<std::uint8_t> expected_state(
      gdn::NUM_VALUE_HEADS * gdn::KEY_DIM * gdn::VALUE_DIM);
  std::vector<std::uint8_t> expected_scales(
      gdn::NUM_VALUE_HEADS * gdn::KEY_DIM * gdn::VALUE_BLOCKS);
  trace.read(
      reinterpret_cast<char *>(expected_state.data()), expected_state.size());
  trace.read(
      reinterpret_cast<char *>(expected_scales.data()), expected_scales.size());
  std::uint8_t expected_readback_status = 0;
  std::uint64_t expected_readback_generation = 0;
  if (!trace || !read_scalar(trace, expected_readback_status) ||
      !read_scalar(trace, expected_readback_generation) ||
      !read_native_array(
          trace, &expected_cumulative_counters[0], gdn::COUNTER_COUNT)) {
    std::cerr << "short final oracle readback record\n";
    return 1;
  }

  invoke(gdn::COMMAND_READBACK, 0, 3, gdn::PAYLOAD_NONE);
  if (status_out[0] != expected_readback_status ||
      generation_out[0] != expected_readback_generation) {
    std::cerr << "oracle final readback metadata mismatch\n";
    return 1;
  }
  std::size_t state_index = 0;
  std::size_t scale_index = 0;
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
      for (int column = 0; column < gdn::VALUE_DIM; ++column) {
        if (gdn::to_u4(state_out[head][row][column]) !=
            expected_state[state_index++]) {
          std::cerr << "oracle final state mismatch head=" << head
                    << " row=" << row << " column=" << column << "\n";
          return 1;
        }
      }
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        if (gdn::to_u8(state_scales_out[head][row][block]) !=
            expected_scales[scale_index++]) {
          std::cerr << "oracle final scale mismatch head=" << head
                    << " row=" << row << " block=" << block << "\n";
          return 1;
        }
      }
    }
  }
  for (int counter = 0; counter < gdn::COUNTER_COUNT; ++counter) {
    if (cumulative_counters[counter] != expected_cumulative_counters[counter]) {
      std::cerr << "oracle final counter mismatch counter=" << counter << "\n";
      return 1;
    }
  }
  char trailing = 0;
  if (trace.read(&trailing, 1)) {
    std::cerr << "oracle trace has trailing bytes\n";
    return 1;
  }

  std::cout << "tb_gdn_top PASS hand_commands=" << (GDN_TB_VECTORS + 11)
            << " oracle_steps=" << trace_tokens << "\n";
  return 0;
}

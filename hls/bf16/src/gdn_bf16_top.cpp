#include "gdn_bf16_kernel.hpp"

namespace gdn_bf16 {

namespace {

using state_block_word_t = ap_uint<16 * gdn::BLOCK_SIZE>;
using state_half_word_t = ap_uint<8 * gdn::BLOCK_SIZE>;

// A 512-bit inferred RAM falls back to BRAM in Vivado 2025.2. Split each
// logical BF16 word into parallel 256-bit banks, then use both memory classes
// so the full 36-layer state fits on U55C without changing its layout.
constexpr int URAM_LAYER_COUNT = 29;
constexpr int BRAM_LAYER_COUNT = gdn::NUM_LAYERS - URAM_LAYER_COUNT;
constexpr int STATE_HALF_BITS = 8 * gdn::BLOCK_SIZE;

static_assert(URAM_LAYER_COUNT > 0, "BF16 URAM bank must be non-empty");
static_assert(BRAM_LAYER_COUNT > 0, "BF16 BRAM bank must be non-empty");

state_half_word_t lower_state_half(state_block_word_t word) {
#pragma HLS INLINE
  return word.range(STATE_HALF_BITS - 1, 0);
}

state_half_word_t upper_state_half(state_block_word_t word) {
#pragma HLS INLINE
  return word.range(2 * STATE_HALF_BITS - 1, STATE_HALF_BITS);
}

state_block_word_t join_state_halves(
    state_half_word_t lower,
    state_half_word_t upper) {
#pragma HLS INLINE
  state_block_word_t word = 0;
  word.range(STATE_HALF_BITS - 1, 0) = lower;
  word.range(2 * STATE_HALF_BITS - 1, STATE_HALF_BITS) = upper;
  return word;
}

bf16_t decode_bf16(bf16_bits_t bits) {
#pragma HLS INLINE
  bf16_t value;
  value.bits_ref() = static_cast<ap_int<16>>(bits);
  return value;
}

accum_t decode_accum(bf16_bits_t bits) {
#pragma HLS INLINE
  return accum_t(decode_bf16(bits));
}

bf16_bits_t encode_bf16(const accum_t &value) {
#pragma HLS INLINE
  const bf16_t rounded(value);
  return static_cast<bf16_bits_t>(rounded.bits_ref());
}

bool finite_bf16(bf16_bits_t value) {
#pragma HLS INLINE
  return ((value >> 7) & 0xffu) != 0xffu;
}

bool unit_interval_bf16(bf16_bits_t value) {
#pragma HLS INLINE
  const unsigned raw = value.to_uint();
  return raw == 0x8000u || (raw < 0x8000u && raw <= 0x3f80u);
}

bf16_bits_t unpack_state_element(state_block_word_t word, int lane) {
#pragma HLS INLINE
  return word.range(16 * lane + 15, 16 * lane);
}

void pack_state_element(
    state_block_word_t &word,
    int lane,
    bf16_bits_t value) {
#pragma HLS INLINE
  word.range(16 * lane + 15, 16 * lane) = value;
}

void clear_counters(counter_array_t counters) {
#pragma HLS INLINE
clear_bf16_counters:
  for (int index = 0; index < gdn::COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    counters[index] = 0;
  }
}

void clear_command_counters(command_counter_array_t counters) {
#pragma HLS INLINE
clear_bf16_command_counters:
  for (int index = 0; index < gdn::COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    counters[index] = 0;
  }
}

void copy_counters(const counter_array_t source, counter_array_t destination) {
#pragma HLS INLINE
copy_bf16_counters:
  for (int index = 0; index < gdn::COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    destination[index] = source[index];
  }
}

void copy_command_counters(
    const command_counter_array_t source,
    counter_array_t destination) {
#pragma HLS INLINE
copy_bf16_command_counters:
  for (int index = 0; index < gdn::COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    destination[index] = static_cast<gdn::counter_t>(source[index]);
  }
}

void accumulate_counters(
    const command_counter_array_t command_counters,
    counter_array_t cumulative_counters) {
#pragma HLS INLINE
accumulate_bf16_counters:
  for (int index = 0; index < gdn::COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    cumulative_counters[index] += command_counters[index];
  }
}

void publish_result(
    gdn::status_t status,
    gdn::generation_t generation,
    const command_counter_array_t command_counters,
    const counter_array_t cumulative_counters,
    gdn::status_t status_out[1],
    gdn::generation_t generation_out[1],
    counter_array_t command_counters_out,
    counter_array_t cumulative_counters_out) {
#pragma HLS INLINE
  status_out[0] = status;
  generation_out[0] = generation;
  copy_command_counters(command_counters, command_counters_out);
  copy_counters(cumulative_counters, cumulative_counters_out);
}

gdn::status_t payload_status(std::uint8_t command, std::uint8_t flags) {
#pragma HLS INLINE
  if (command == gdn::COMMAND_RESET || command == gdn::COMMAND_READBACK) {
    return flags == gdn::PAYLOAD_NONE ? gdn::STATUS_OK
                                      : gdn::STATUS_UNEXPECTED_PAYLOAD;
  }
  if (command == gdn::COMMAND_LOAD) {
    if ((flags & gdn::PAYLOAD_STATE) == 0u) {
      return gdn::STATUS_MISSING_PAYLOAD;
    }
    return flags == gdn::PAYLOAD_STATE ? gdn::STATUS_OK
                                       : gdn::STATUS_UNEXPECTED_PAYLOAD;
  }
  if ((flags & gdn::PAYLOAD_TOKEN) == 0u) {
    return gdn::STATUS_MISSING_PAYLOAD;
  }
  return flags == gdn::PAYLOAD_TOKEN ? gdn::STATUS_OK
                                     : gdn::STATUS_UNEXPECTED_PAYLOAD;
}

accum_t reduce_128(const accum_t terms[gdn::KEY_DIM]) {
#pragma HLS INLINE off
  static_assert(gdn::KEY_DIM == 128, "BF16 reduction tree assumes K=128");
  accum_t level64[64];
  accum_t level32[32];
  accum_t level16[16];
  accum_t level8[8];
  accum_t level4[4];
  accum_t level2[2];
#pragma HLS ARRAY_PARTITION variable=terms cyclic factor=gdn::P_K dim=1
#pragma HLS ARRAY_PARTITION variable=level64 cyclic factor=gdn::P_K dim=1
#pragma HLS ARRAY_PARTITION variable=level32 cyclic factor=gdn::P_K dim=1
#pragma HLS ARRAY_PARTITION variable=level16 complete dim=1
#pragma HLS ARRAY_PARTITION variable=level8 complete dim=1
#pragma HLS ARRAY_PARTITION variable=level4 complete dim=1
#pragma HLS ARRAY_PARTITION variable=level2 complete dim=1
reduce_bf16_64:
  for (int index = 0; index < 64; ++index) {
#pragma HLS PIPELINE II=1
    level64[index] = terms[2 * index] + terms[2 * index + 1];
  }
reduce_bf16_32:
  for (int index = 0; index < 32; ++index) {
#pragma HLS PIPELINE II=1
    level32[index] = level64[2 * index] + level64[2 * index + 1];
  }
reduce_bf16_16:
  for (int index = 0; index < 16; ++index) {
#pragma HLS PIPELINE II=1
    level16[index] = level32[2 * index] + level32[2 * index + 1];
  }
reduce_bf16_8:
  for (int index = 0; index < 8; ++index) {
#pragma HLS PIPELINE II=1
    level8[index] = level16[2 * index] + level16[2 * index + 1];
  }
reduce_bf16_4:
  for (int index = 0; index < 4; ++index) {
#pragma HLS PIPELINE II=1
    level4[index] = level8[2 * index] + level8[2 * index + 1];
  }
reduce_bf16_2:
  for (int index = 0; index < 2; ++index) {
#pragma HLS PIPELINE II=1
    level2[index] = level4[2 * index] + level4[2 * index + 1];
  }
  return level2[0] + level2[1];
}

bool phase1_validate_token(
    const qk_tensor_t q,
    const qk_tensor_t k,
    const value_tensor_t v,
    const head_tensor_t alpha,
    const head_tensor_t beta,
    qk_tensor_t q_local,
    qk_tensor_t k_local,
    value_tensor_t v_local,
    head_tensor_t alpha_local,
    head_tensor_t beta_local) {
#pragma HLS INLINE off
  bool valid = true;
phase1_bf16_qk_heads:
  for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
  phase1_bf16_qk_values:
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
#pragma HLS PIPELINE II=1
      q_local[head][row] = q[head][row];
      k_local[head][row] = k[head][row];
      valid = valid && finite_bf16(q[head][row]) && finite_bf16(k[head][row]);
    }
  }
phase1_bf16_value_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    alpha_local[head] = alpha[head];
    beta_local[head] = beta[head];
    valid = valid && unit_interval_bf16(alpha[head]) &&
            unit_interval_bf16(beta[head]);
  phase1_bf16_value_lanes:
    for (int column = 0; column < gdn::VALUE_DIM; ++column) {
#pragma HLS PIPELINE II=1
      v_local[head][column] = v[head][column];
      valid = valid && finite_bf16(v[head][column]);
    }
  }
  return valid;
}

bool phase1_validate_state(const state_tensor_t state) {
#pragma HLS INLINE off
  bool valid = true;
validate_bf16_state_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
  validate_bf16_state_rows:
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
    validate_bf16_state_columns:
      for (int column = 0; column < gdn::VALUE_DIM; ++column) {
        const bf16_bits_t value = state[head][row][column];
        valid = valid && finite_bf16(value);
      }
    }
  }
  return valid;
}

void phase2_decay_predict_tile(
    const qk_head_t k,
    bf16_bits_t alpha,
    const state_tile_t state,
    accum_tile_t decayed,
    accum_block_t prediction) {
#pragma HLS INLINE off
  const accum_t alpha_value = decode_accum(alpha);
phase2_bf16_decay_rows:
  for (int row = 0; row < gdn::KEY_DIM; ++row) {
  phase2_bf16_decay_lanes:
    for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
      decayed[row][lane] = decode_accum(state[row][lane]) * alpha_value;
    }
  }
phase2_bf16_predict_lanes:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
    accum_t terms[gdn::KEY_DIM];
#pragma HLS ARRAY_PARTITION variable=terms cyclic factor=gdn::P_K dim=1
  phase2_bf16_prediction_terms:
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
#pragma HLS PIPELINE II=1
      terms[row] = decode_accum(k[row]) * decayed[row][lane];
    }
    prediction[lane] = reduce_128(terms);
  }
}

void phase3_delta_tile(
    const value_head_t v,
    bf16_bits_t beta,
    int value_block,
    const accum_block_t prediction,
    accum_block_t delta) {
#pragma HLS INLINE off
  const accum_t beta_value = decode_accum(beta);
phase3_bf16_delta_lanes:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    const int column = value_block * gdn::BLOCK_SIZE + lane;
    delta[lane] = (decode_accum(v[column]) - prediction[lane]) * beta_value;
  }
}

void phase4_update_state_tile(
    const qk_head_t k,
    const accum_block_t delta,
    const accum_tile_t decayed,
    state_tile_t state,
    accum_tile_t updated) {
#pragma HLS INLINE off
phase4_bf16_update_rows:
  for (int row = 0; row < gdn::KEY_DIM; ++row) {
    const accum_t key = decode_accum(k[row]);
  phase4_bf16_update_lanes:
    for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
      const accum_t value = decayed[row][lane] + key * delta[lane];
      updated[row][lane] = value;
      state[row][lane] = encode_bf16(value);
    }
  }
}

void phase5_output_tile(
    const qk_head_t q,
    int value_block,
    const accum_tile_t updated,
    bf16_bits_t output[gdn::VALUE_DIM]) {
#pragma HLS INLINE off
phase5_bf16_output_lanes:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
    accum_t terms[gdn::KEY_DIM];
#pragma HLS ARRAY_PARTITION variable=terms cyclic factor=gdn::P_K dim=1
  phase5_bf16_output_terms:
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
#pragma HLS PIPELINE II=1
      terms[row] = decode_accum(q[row]) * updated[row][lane];
    }
    const int column = value_block * gdn::BLOCK_SIZE + lane;
    output[column] = encode_bf16(reduce_128(terms));
  }
}

}  // namespace

void gdn_bf16_top_impl(
    std::uint8_t command,
    std::uint16_t sequence_id,
    std::uint8_t layer_id,
    std::uint8_t payload_flags,
    const qk_tensor_t q,
    const qk_tensor_t k,
    const value_tensor_t v,
    const head_tensor_t alpha,
    const head_tensor_t beta,
    const state_tensor_t state_in,
    output_tensor_t output,
    state_tensor_t state_out,
    gdn::status_t status_out[1],
    gdn::generation_t generation_out[1],
    counter_array_t command_counters_out,
    counter_array_t cumulative_counters_out) {
  static state_half_word_t resident_state_uram_lower[gdn::NUM_SEQUENCES]
      [URAM_LAYER_COUNT][gdn::NUM_VALUE_HEADS][gdn::KEY_DIM]
      [gdn::VALUE_BLOCKS];
  static state_half_word_t resident_state_uram_upper[gdn::NUM_SEQUENCES]
      [URAM_LAYER_COUNT][gdn::NUM_VALUE_HEADS][gdn::KEY_DIM]
      [gdn::VALUE_BLOCKS];
  static state_half_word_t resident_state_bram_lower[gdn::NUM_SEQUENCES]
      [BRAM_LAYER_COUNT][gdn::NUM_VALUE_HEADS][gdn::KEY_DIM]
      [gdn::VALUE_BLOCKS];
  static state_half_word_t resident_state_bram_upper[gdn::NUM_SEQUENCES]
      [BRAM_LAYER_COUNT][gdn::NUM_VALUE_HEADS][gdn::KEY_DIM]
      [gdn::VALUE_BLOCKS];
  static bool initialized[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS] = {};
  static gdn::generation_t generations[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS] = {};
  static gdn::counter_t cumulative_counters[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS]
      [gdn::COUNTER_COUNT] = {};
#pragma HLS BIND_STORAGE variable=resident_state_uram_lower type=ram_t2p impl=uram
#pragma HLS BIND_STORAGE variable=resident_state_uram_upper type=ram_t2p impl=uram
#pragma HLS BIND_STORAGE variable=resident_state_bram_lower type=ram_t2p impl=bram
#pragma HLS BIND_STORAGE variable=resident_state_bram_upper type=ram_t2p impl=bram
#pragma HLS ARRAY_PARTITION variable=cumulative_counters complete dim=3

  command_counter_array_t command_counters;
  counter_array_t empty_counters;
#pragma HLS ARRAY_PARTITION variable=command_counters complete dim=1
#pragma HLS ARRAY_PARTITION variable=empty_counters complete dim=1
  clear_command_counters(command_counters);
  clear_counters(empty_counters);

clear_bf16_output_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
  clear_bf16_output_lanes:
    for (int column = 0; column < gdn::VALUE_DIM; ++column) {
#pragma HLS PIPELINE II=1
      output[head][column] = 0;
    }
  }

  if (sequence_id >= gdn::NUM_SEQUENCES) {
    command_counters[gdn::COUNTER_REJECTED_COMMANDS] = 1;
    publish_result(
        gdn::STATUS_INVALID_SEQUENCE_ID,
        0,
        command_counters,
        empty_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }
  if (layer_id >= gdn::NUM_LAYERS) {
    command_counters[gdn::COUNTER_REJECTED_COMMANDS] = 1;
    publish_result(
        gdn::STATUS_INVALID_LAYER_ID,
        0,
        command_counters,
        empty_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  gdn::counter_t *slot_counters = cumulative_counters[sequence_id][layer_id];
  if (command > gdn::COMMAND_READBACK) {
    command_counters[gdn::COUNTER_REJECTED_COMMANDS] = 1;
    accumulate_counters(command_counters, slot_counters);
    publish_result(
        gdn::STATUS_INVALID_COMMAND,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }
  const gdn::status_t payload_error = payload_status(command, payload_flags);
  if (payload_error != gdn::STATUS_OK) {
    command_counters[gdn::COUNTER_REJECTED_COMMANDS] = 1;
    accumulate_counters(command_counters, slot_counters);
    publish_result(
        payload_error,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  if (command == gdn::COMMAND_RESET) {
  reset_bf16_heads:
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    reset_bf16_rows:
      for (int row = 0; row < gdn::KEY_DIM; ++row) {
      reset_bf16_blocks:
        for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
#pragma HLS PIPELINE II=1
          if (layer_id < URAM_LAYER_COUNT) {
            resident_state_uram_lower[sequence_id][layer_id][head][row][block] = 0;
            resident_state_uram_upper[sequence_id][layer_id][head][row][block] = 0;
          } else {
            const int bram_layer = layer_id - URAM_LAYER_COUNT;
            resident_state_bram_lower[sequence_id][bram_layer][head][row][block] = 0;
            resident_state_bram_upper[sequence_id][bram_layer][head][row][block] = 0;
          }
        }
      }
    }
    initialized[sequence_id][layer_id] = true;
    generations[sequence_id][layer_id] = 0;
    clear_counters(slot_counters);
    publish_result(
        gdn::STATUS_OK,
        0,
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  if (command == gdn::COMMAND_LOAD) {
    if (!phase1_validate_state(state_in)) {
      command_counters[gdn::COUNTER_INVALID_ENCODINGS] = 1;
      command_counters[gdn::COUNTER_REJECTED_COMMANDS] = 1;
      accumulate_counters(command_counters, slot_counters);
      publish_result(
          gdn::STATUS_INVALID_ENCODING,
          generations[sequence_id][layer_id],
          command_counters,
          slot_counters,
          status_out,
          generation_out,
          command_counters_out,
          cumulative_counters_out);
      return;
    }
  load_bf16_heads:
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    load_bf16_rows:
      for (int row = 0; row < gdn::KEY_DIM; ++row) {
      load_bf16_blocks:
        for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
          state_block_word_t packed = 0;
        load_bf16_lanes:
          for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
            const int column = block * gdn::BLOCK_SIZE + lane;
            pack_state_element(packed, lane, state_in[head][row][column]);
          }
          if (layer_id < URAM_LAYER_COUNT) {
            resident_state_uram_lower[sequence_id][layer_id][head][row][block] =
                lower_state_half(packed);
            resident_state_uram_upper[sequence_id][layer_id][head][row][block] =
                upper_state_half(packed);
          } else {
            const int bram_layer = layer_id - URAM_LAYER_COUNT;
            resident_state_bram_lower[sequence_id][bram_layer][head][row][block] =
                lower_state_half(packed);
            resident_state_bram_upper[sequence_id][bram_layer][head][row][block] =
                upper_state_half(packed);
          }
        }
      }
    }
    initialized[sequence_id][layer_id] = true;
    ++generations[sequence_id][layer_id];
    command_counters[gdn::COUNTER_COMMITTED_STATE_GENERATIONS] = 1;
    accumulate_counters(command_counters, slot_counters);
    publish_result(
        gdn::STATUS_OK,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  if (!initialized[sequence_id][layer_id]) {
    command_counters[gdn::COUNTER_REJECTED_COMMANDS] = 1;
    accumulate_counters(command_counters, slot_counters);
    publish_result(
        gdn::STATUS_UNINITIALIZED_STATE,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  if (command == gdn::COMMAND_READBACK) {
  readback_bf16_heads:
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    readback_bf16_rows:
      for (int row = 0; row < gdn::KEY_DIM; ++row) {
      readback_bf16_blocks:
        for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
          state_block_word_t packed;
          if (layer_id < URAM_LAYER_COUNT) {
            packed = join_state_halves(
                resident_state_uram_lower[sequence_id][layer_id][head][row][block],
                resident_state_uram_upper[sequence_id][layer_id][head][row][block]);
          } else {
            const int bram_layer = layer_id - URAM_LAYER_COUNT;
            packed = join_state_halves(
                resident_state_bram_lower[sequence_id][bram_layer][head][row][block],
                resident_state_bram_upper[sequence_id][bram_layer][head][row][block]);
          }
        readback_bf16_lanes:
          for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
            const int column = block * gdn::BLOCK_SIZE + lane;
            state_out[head][row][column] = unpack_state_element(packed, lane);
          }
        }
      }
    }
    publish_result(
        gdn::STATUS_OK,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  static bf16_bits_t q_local[gdn::NUM_QK_HEADS][gdn::KEY_DIM];
  static bf16_bits_t k_local[gdn::NUM_QK_HEADS][gdn::KEY_DIM];
  static bf16_bits_t v_local[gdn::NUM_VALUE_HEADS][gdn::VALUE_DIM];
  static bf16_bits_t alpha_local[gdn::NUM_VALUE_HEADS];
  static bf16_bits_t beta_local[gdn::NUM_VALUE_HEADS];
  if (!phase1_validate_token(
          q,
          k,
          v,
          alpha,
          beta,
          q_local,
          k_local,
          v_local,
          alpha_local,
          beta_local)) {
    command_counters[gdn::COUNTER_INVALID_ENCODINGS] = 1;
    command_counters[gdn::COUNTER_REJECTED_COMMANDS] = 1;
    accumulate_counters(command_counters, slot_counters);
    publish_result(
        gdn::STATUS_INVALID_ENCODING,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  static bf16_bits_t state_tile[gdn::KEY_DIM][gdn::BLOCK_SIZE];
  static accum_t decayed[gdn::KEY_DIM][gdn::BLOCK_SIZE];
  static accum_t updated[gdn::KEY_DIM][gdn::BLOCK_SIZE];
  accum_t prediction[gdn::BLOCK_SIZE];
  accum_t delta[gdn::BLOCK_SIZE];
#pragma HLS ARRAY_PARTITION variable=state_tile cyclic factor=gdn::P_K dim=1
#pragma HLS ARRAY_PARTITION variable=state_tile cyclic factor=gdn::P_V dim=2
#pragma HLS ARRAY_PARTITION variable=decayed cyclic factor=gdn::P_K dim=1
#pragma HLS ARRAY_PARTITION variable=decayed cyclic factor=gdn::P_V dim=2
#pragma HLS ARRAY_PARTITION variable=updated cyclic factor=gdn::P_K dim=1
#pragma HLS ARRAY_PARTITION variable=updated cyclic factor=gdn::P_V dim=2
#pragma HLS ARRAY_PARTITION variable=prediction cyclic factor=gdn::P_V dim=1
#pragma HLS ARRAY_PARTITION variable=delta cyclic factor=gdn::P_V dim=1

step_bf16_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    const int qk_head = head / (gdn::NUM_VALUE_HEADS / gdn::NUM_QK_HEADS);
  step_bf16_value_blocks:
    for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
    load_bf16_resident_rows:
      for (int row = 0; row < gdn::KEY_DIM; ++row) {
        state_block_word_t packed;
        if (layer_id < URAM_LAYER_COUNT) {
          packed = join_state_halves(
              resident_state_uram_lower[sequence_id][layer_id][head][row][block],
              resident_state_uram_upper[sequence_id][layer_id][head][row][block]);
        } else {
          const int bram_layer = layer_id - URAM_LAYER_COUNT;
          packed = join_state_halves(
              resident_state_bram_lower[sequence_id][bram_layer][head][row][block],
              resident_state_bram_upper[sequence_id][bram_layer][head][row][block]);
        }
      unpack_bf16_resident_lanes:
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          state_tile[row][lane] = unpack_state_element(packed, lane);
        }
      }
      phase2_decay_predict_tile(
          k_local[qk_head],
          alpha_local[head],
          state_tile,
          decayed,
          prediction);
      phase3_delta_tile(
          v_local[head], beta_local[head], block, prediction, delta);
      phase4_update_state_tile(
          k_local[qk_head], delta, decayed, state_tile, updated);
      phase5_output_tile(q_local[qk_head], block, updated, output[head]);
    store_bf16_resident_rows:
      for (int row = 0; row < gdn::KEY_DIM; ++row) {
        state_block_word_t packed = 0;
      pack_bf16_resident_lanes:
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          pack_state_element(packed, lane, state_tile[row][lane]);
        }
        if (layer_id < URAM_LAYER_COUNT) {
          resident_state_uram_lower[sequence_id][layer_id][head][row][block] =
              lower_state_half(packed);
          resident_state_uram_upper[sequence_id][layer_id][head][row][block] =
              upper_state_half(packed);
        } else {
          const int bram_layer = layer_id - URAM_LAYER_COUNT;
          resident_state_bram_lower[sequence_id][bram_layer][head][row][block] =
              lower_state_half(packed);
          resident_state_bram_upper[sequence_id][bram_layer][head][row][block] =
              upper_state_half(packed);
        }
      }
    }
  }

  ++generations[sequence_id][layer_id];
  command_counters[gdn::COUNTER_COMMITTED_STATE_GENERATIONS] = 1;
  accumulate_counters(command_counters, slot_counters);
  publish_result(
      gdn::STATUS_OK,
      generations[sequence_id][layer_id],
      command_counters,
      slot_counters,
      status_out,
      generation_out,
      command_counters_out,
      cumulative_counters_out);
}

}  // namespace gdn_bf16

void gdn_bf16_top(
    std::uint8_t command,
    std::uint16_t sequence_id,
    std::uint8_t layer_id,
    std::uint8_t payload_flags,
    const gdn_bf16::qk_tensor_t q,
    const gdn_bf16::qk_tensor_t k,
    const gdn_bf16::value_tensor_t v,
    const gdn_bf16::head_tensor_t alpha,
    const gdn_bf16::head_tensor_t beta,
    const gdn_bf16::state_tensor_t state_in,
    gdn_bf16::output_tensor_t output,
    gdn_bf16::state_tensor_t state_out,
    gdn::status_t status_out[1],
    gdn::generation_t generation_out[1],
    gdn_bf16::counter_array_t command_counters_out,
    gdn_bf16::counter_array_t cumulative_counters_out) {
#pragma HLS INTERFACE s_axilite port=command bundle=control
#pragma HLS INTERFACE s_axilite port=sequence_id bundle=control
#pragma HLS INTERFACE s_axilite port=layer_id bundle=control
#pragma HLS INTERFACE s_axilite port=payload_flags bundle=control
#pragma HLS INTERFACE m_axi port=q offset=slave bundle=gmem0
#pragma HLS INTERFACE m_axi port=k offset=slave bundle=gmem1
#pragma HLS INTERFACE m_axi port=v offset=slave bundle=gmem2
#pragma HLS INTERFACE m_axi port=alpha offset=slave bundle=gmem3
#pragma HLS INTERFACE m_axi port=beta offset=slave bundle=gmem3
#pragma HLS INTERFACE m_axi port=state_in offset=slave bundle=gmem4
#pragma HLS INTERFACE m_axi port=output offset=slave bundle=gmem5
#pragma HLS INTERFACE m_axi port=state_out offset=slave bundle=gmem6
#pragma HLS INTERFACE m_axi port=status_out offset=slave bundle=gmem7
#pragma HLS INTERFACE m_axi port=generation_out offset=slave bundle=gmem7
#pragma HLS INTERFACE m_axi port=command_counters_out offset=slave bundle=gmem7
#pragma HLS INTERFACE m_axi port=cumulative_counters_out offset=slave bundle=gmem7
#pragma HLS INTERFACE s_axilite port=return bundle=control
  gdn_bf16::gdn_bf16_top_impl(
      command,
      sequence_id,
      layer_id,
      payload_flags,
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
      command_counters_out,
      cumulative_counters_out);
}

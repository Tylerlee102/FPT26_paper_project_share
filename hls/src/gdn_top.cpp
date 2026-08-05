#ifndef GDN_KERNEL_HEADER
#define GDN_KERNEL_HEADER "gdn_kernel.hpp"
#endif
#ifndef GDN_NAMESPACE
#define GDN_NAMESPACE gdn
#endif
#ifndef GDN_TOP_NAME
#define GDN_TOP_NAME gdn_top
#endif
#ifndef GDN_TOP_IMPL_NAME
#define GDN_TOP_IMPL_NAME gdn_top_impl
#endif

#include GDN_KERNEL_HEADER

namespace GDN_NAMESPACE {

namespace {

#if GDN_HAS_AP_INT
using state_block_word_t = ap_uint<MX_ELEMENT_BITS * BLOCK_SIZE>;
using state_scale_word_t = ap_uint<8 * VALUE_BLOCKS>;

mx_element_t unpack_state_element(state_block_word_t word, int lane) {
#pragma HLS INLINE
  return word.range(
      MX_ELEMENT_BITS * lane + MX_ELEMENT_BITS - 1,
      MX_ELEMENT_BITS * lane);
}

void pack_state_element(
    state_block_word_t &word,
    int lane,
    mx_element_t value) {
#pragma HLS INLINE
  word.range(
      MX_ELEMENT_BITS * lane + MX_ELEMENT_BITS - 1,
      MX_ELEMENT_BITS * lane) = value;
}

mx_scale_t unpack_state_scale(state_scale_word_t word, int block) {
#pragma HLS INLINE
  return word.range(8 * block + 7, 8 * block);
}

void pack_state_scale(
    state_scale_word_t &word,
    int block,
    mx_scale_t value) {
#pragma HLS INLINE
  word.range(8 * block + 7, 8 * block) = value;
}
#else
struct state_block_word_t {
  mx_element_t lanes[BLOCK_SIZE];
};

struct state_scale_word_t {
  mx_scale_t blocks[VALUE_BLOCKS];
};

mx_element_t unpack_state_element(const state_block_word_t &word, int lane) {
  return word.lanes[lane];
}

void pack_state_element(
    state_block_word_t &word,
    int lane,
    mx_element_t value) {
  word.lanes[lane] = value;
}

mx_scale_t unpack_state_scale(const state_scale_word_t &word, int block) {
  return word.blocks[block];
}

void pack_state_scale(
    state_scale_word_t &word,
    int block,
    mx_scale_t value) {
  word.blocks[block] = value;
}
#endif

state_scale_word_t canonical_scale_word() {
#pragma HLS INLINE
  state_scale_word_t word{};
canonical_scale_blocks:
  for (int block = 0; block < VALUE_BLOCKS; ++block) {
#pragma HLS UNROLL
    pack_state_scale(word, block, static_cast<mx_scale_t>(E8M0_BIAS));
  }
  return word;
}

void clear_counters(counter_array_t counters) {
#pragma HLS INLINE
clear_counter_loop:
  for (int index = 0; index < COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    counters[index] = 0;
  }
}

void clear_command_counters(command_counter_array_t counters) {
#pragma HLS INLINE
clear_command_counter_loop:
  for (int index = 0; index < COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    counters[index] = 0;
  }
}

void copy_counters(const counter_array_t source, counter_array_t destination) {
#pragma HLS INLINE
copy_counter_loop:
  for (int index = 0; index < COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    destination[index] = source[index];
  }
}

void copy_command_counters(
    const command_counter_array_t source,
    counter_array_t destination) {
#pragma HLS INLINE
copy_command_counter_loop:
  for (int index = 0; index < COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    destination[index] = static_cast<counter_t>(source[index]);
  }
}

void accumulate_counters(
    const command_counter_array_t command_counters,
    counter_array_t cumulative_counters) {
#pragma HLS INLINE
accumulate_counter_loop:
  for (int index = 0; index < COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    cumulative_counters[index] += command_counters[index];
  }
}

void publish_result(
    status_t status,
    generation_t generation,
    const command_counter_array_t command_counters,
    const counter_array_t cumulative_counters,
    status_t status_out[1],
    generation_t generation_out[1],
    counter_array_t command_counters_out,
    counter_array_t cumulative_counters_out) {
#pragma HLS INLINE
  status_out[0] = status;
  generation_out[0] = generation;
  copy_command_counters(command_counters, command_counters_out);
  copy_counters(cumulative_counters, cumulative_counters_out);
}

status_t payload_status(std::uint8_t command, std::uint8_t flags) {
#pragma HLS INLINE
  if (command == COMMAND_RESET || command == COMMAND_READBACK) {
    return flags == PAYLOAD_NONE ? STATUS_OK : STATUS_UNEXPECTED_PAYLOAD;
  }
  if (command == COMMAND_LOAD) {
    if ((flags & PAYLOAD_STATE) == 0u) {
      return STATUS_MISSING_PAYLOAD;
    }
    return flags == PAYLOAD_STATE ? STATUS_OK : STATUS_UNEXPECTED_PAYLOAD;
  }
  if ((flags & PAYLOAD_TOKEN) == 0u) {
    return STATUS_MISSING_PAYLOAD;
  }
  return flags == PAYLOAD_TOKEN ? STATUS_OK : STATUS_UNEXPECTED_PAYLOAD;
}

}  // namespace

void GDN_TOP_IMPL_NAME(
    std::uint8_t command,
    std::uint16_t sequence_id,
    std::uint8_t layer_id,
    std::uint8_t payload_flags,
    const qk_tensor_t q,
    const qk_scale_tensor_t q_scales,
    const qk_tensor_t k,
    const qk_scale_tensor_t k_scales,
    const value_tensor_t v,
    const value_scale_tensor_t v_scales,
    const q1_15_head_t alpha,
    const q1_15_head_t beta,
    const state_tensor_t state_in,
    const state_scale_t state_scales_in,
    output_mantissa_t output_mantissas,
    output_exponent_t output_exponents,
    state_tensor_t state_out,
    state_scale_t state_scales_out,
    status_t status_out[1],
    generation_t generation_out[1],
    counter_array_t command_counters_out,
    counter_array_t cumulative_counters_out) {
  static state_block_word_t resident_state
      [NUM_SEQUENCES][NUM_LAYERS][NUM_VALUE_HEADS][KEY_DIM][VALUE_BLOCKS];
  static state_scale_word_t resident_scales
      [NUM_SEQUENCES][NUM_LAYERS][NUM_VALUE_HEADS][KEY_DIM];
  static bool initialized[NUM_SEQUENCES][NUM_LAYERS] = {};
  static generation_t generations[NUM_SEQUENCES][NUM_LAYERS] = {};
  static counter_t cumulative_counters
      [NUM_SEQUENCES][NUM_LAYERS][COUNTER_COUNT] = {};
#pragma HLS BIND_STORAGE variable=resident_state type=ram_t2p impl=uram
#pragma HLS BIND_STORAGE variable=resident_scales type=ram_t2p impl=bram
#pragma HLS ARRAY_PARTITION variable=cumulative_counters complete dim=3

  command_counter_t command_counters[COUNTER_COUNT];
  counter_t empty_counters[COUNTER_COUNT];
#pragma HLS ARRAY_PARTITION variable=command_counters complete dim=1
#pragma HLS ARRAY_PARTITION variable=empty_counters complete dim=1
  clear_command_counters(command_counters);
  clear_counters(empty_counters);

clear_output_mantissa_heads:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
  clear_output_mantissa_values:
    for (int column = 0; column < VALUE_DIM; ++column) {
#pragma HLS PIPELINE II=1
      output_mantissas[head][column] = 0;
    }
  }
clear_output_exponent_heads:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
  clear_output_exponent_values:
    for (int column = 0; column < VALUE_DIM; ++column) {
#pragma HLS PIPELINE II=1
      output_exponents[head][column] = 0;
    }
  }

  if (sequence_id >= NUM_SEQUENCES) {
    command_counters[COUNTER_REJECTED_COMMANDS] = 1;
    publish_result(
        STATUS_INVALID_SEQUENCE_ID,
        0,
        command_counters,
        empty_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }
  if (layer_id >= NUM_LAYERS) {
    command_counters[COUNTER_REJECTED_COMMANDS] = 1;
    publish_result(
        STATUS_INVALID_LAYER_ID,
        0,
        command_counters,
        empty_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  counter_t *slot_counters = cumulative_counters[sequence_id][layer_id];
  if (command > COMMAND_READBACK) {
    command_counters[COUNTER_REJECTED_COMMANDS] = 1;
    accumulate_counters(command_counters, slot_counters);
    publish_result(
        STATUS_INVALID_COMMAND,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  const status_t payload_error = payload_status(command, payload_flags);
  if (payload_error != STATUS_OK) {
    command_counters[COUNTER_REJECTED_COMMANDS] = 1;
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

  if (command == COMMAND_RESET) {
  reset_heads:
    for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
    reset_rows:
      for (int row = 0; row < KEY_DIM; ++row) {
        resident_scales[sequence_id][layer_id][head][row] =
            canonical_scale_word();
      reset_blocks:
        for (int block = 0; block < VALUE_BLOCKS; ++block) {
#pragma HLS PIPELINE II=1
          resident_state[sequence_id][layer_id][head][row][block] =
              state_block_word_t{};
        }
      }
    }
    initialized[sequence_id][layer_id] = true;
    generations[sequence_id][layer_id] = 0;
    clear_counters(slot_counters);
    publish_result(
        STATUS_OK,
        0,
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  if (command == COMMAND_LOAD) {
    if (!phase1_validate_state(state_in, state_scales_in)) {
      command_counters[COUNTER_INVALID_ENCODINGS] = 1;
      command_counters[COUNTER_REJECTED_COMMANDS] = 1;
      accumulate_counters(command_counters, slot_counters);
      publish_result(
          STATUS_INVALID_ENCODING,
          generations[sequence_id][layer_id],
          command_counters,
          slot_counters,
          status_out,
          generation_out,
          command_counters_out,
          cumulative_counters_out);
      return;
    }
  load_heads:
    for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
    load_rows:
      for (int row = 0; row < KEY_DIM; ++row) {
        state_scale_word_t packed_scales{};
      load_blocks:
        for (int block = 0; block < VALUE_BLOCKS; ++block) {
          pack_state_scale(
              packed_scales, block, state_scales_in[head][row][block]);
          state_block_word_t packed_state{};
        load_lanes:
          for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
            const int column = block * BLOCK_SIZE + lane;
            pack_state_element(
                packed_state, lane, state_in[head][row][column]);
          }
          resident_state[sequence_id][layer_id][head][row][block] =
              packed_state;
        }
        resident_scales[sequence_id][layer_id][head][row] = packed_scales;
      }
    }
    initialized[sequence_id][layer_id] = true;
    ++generations[sequence_id][layer_id];
    command_counters[COUNTER_COMMITTED_STATE_GENERATIONS] = 1;
    accumulate_counters(command_counters, slot_counters);
    publish_result(
        STATUS_OK,
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
    command_counters[COUNTER_REJECTED_COMMANDS] = 1;
    accumulate_counters(command_counters, slot_counters);
    publish_result(
        STATUS_UNINITIALIZED_STATE,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  if (command == COMMAND_READBACK) {
  readback_heads:
    for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
    readback_rows:
      for (int row = 0; row < KEY_DIM; ++row) {
        const state_scale_word_t packed_scales =
            resident_scales[sequence_id][layer_id][head][row];
      readback_blocks:
        for (int block = 0; block < VALUE_BLOCKS; ++block) {
          state_scales_out[head][row][block] =
              unpack_state_scale(packed_scales, block);
          const state_block_word_t packed_state =
              resident_state[sequence_id][layer_id][head][row][block];
        readback_lanes:
          for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
            const int column = block * BLOCK_SIZE + lane;
            state_out[head][row][column] =
                unpack_state_element(packed_state, lane);
          }
        }
      }
    }
    publish_result(
        STATUS_OK,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  static mx_element_t q_local[NUM_QK_HEADS][KEY_DIM];
  static mx_scale_t q_scales_local[NUM_QK_HEADS][QK_BLOCKS];
  static mx_element_t k_local[NUM_QK_HEADS][KEY_DIM];
  static mx_scale_t k_scales_local[NUM_QK_HEADS][QK_BLOCKS];
  static mx_element_t v_local[NUM_VALUE_HEADS][VALUE_DIM];
  static mx_scale_t v_scales_local[NUM_VALUE_HEADS][VALUE_BLOCKS];
  static q1_15_t alpha_local[NUM_VALUE_HEADS];
  static q1_15_t beta_local[NUM_VALUE_HEADS];

  if (!phase1_validate_token(
          q,
          q_scales,
          k,
          k_scales,
          v,
          v_scales,
          alpha,
          beta,
          q_local,
          q_scales_local,
          k_local,
          k_scales_local,
          v_local,
          v_scales_local,
          alpha_local,
          beta_local)) {
    command_counters[COUNTER_INVALID_ENCODINGS] = 1;
    command_counters[COUNTER_REJECTED_COMMANDS] = 1;
    accumulate_counters(command_counters, slot_counters);
    publish_result(
        STATUS_INVALID_ENCODING,
        generations[sequence_id][layer_id],
        command_counters,
        slot_counters,
        status_out,
        generation_out,
        command_counters_out,
        cumulative_counters_out);
    return;
  }

  static mantissa_t decayed_mantissas[KEY_DIM][BLOCK_SIZE];
  static exponent_t decayed_exponents[KEY_DIM][BLOCK_SIZE];
  static mantissa_t updated_mantissas[KEY_DIM][BLOCK_SIZE];
  static exponent_t updated_exponents[KEY_DIM][BLOCK_SIZE];
  static mx_element_t state_tile[KEY_DIM][BLOCK_SIZE];
  static mx_scale_t state_scale_tile[KEY_DIM];
  mantissa_t prediction_mantissas[BLOCK_SIZE];
  exponent_t prediction_exponents[BLOCK_SIZE];
  mantissa_t delta_mantissas[BLOCK_SIZE];
  exponent_t delta_exponents[BLOCK_SIZE];
#pragma HLS ARRAY_PARTITION variable=decayed_mantissas cyclic factor=P_K dim=1
#pragma HLS ARRAY_PARTITION variable=decayed_mantissas cyclic factor=P_V dim=2
#pragma HLS ARRAY_PARTITION variable=decayed_exponents cyclic factor=P_K dim=1
#pragma HLS ARRAY_PARTITION variable=decayed_exponents cyclic factor=P_V dim=2
#pragma HLS ARRAY_PARTITION variable=updated_mantissas cyclic factor=P_K dim=1
#pragma HLS ARRAY_PARTITION variable=updated_mantissas cyclic factor=P_V dim=2
#pragma HLS ARRAY_PARTITION variable=updated_exponents cyclic factor=P_K dim=1
#pragma HLS ARRAY_PARTITION variable=updated_exponents cyclic factor=P_V dim=2
#pragma HLS ARRAY_PARTITION variable=state_tile cyclic factor=P_K dim=1
#pragma HLS ARRAY_PARTITION variable=state_tile cyclic factor=P_V dim=2
#pragma HLS ARRAY_PARTITION variable=state_scale_tile cyclic factor=P_K dim=1
#pragma HLS ARRAY_PARTITION variable=prediction_mantissas cyclic factor=P_V dim=1
#pragma HLS ARRAY_PARTITION variable=prediction_exponents cyclic factor=P_V dim=1
#pragma HLS ARRAY_PARTITION variable=delta_mantissas cyclic factor=P_V dim=1
#pragma HLS ARRAY_PARTITION variable=delta_exponents cyclic factor=P_V dim=1

step_heads:
  for (int head = 0; head < NUM_VALUE_HEADS; ++head) {
    const int qk_head = head / (NUM_VALUE_HEADS / NUM_QK_HEADS);
  step_value_blocks:
    for (int block = 0; block < VALUE_BLOCKS; ++block) {
    load_resident_tile:
      for (int row = 0; row < KEY_DIM; ++row) {
        const state_block_word_t packed_state =
            resident_state[sequence_id][layer_id][head][row][block];
        const state_scale_word_t packed_scales =
            resident_scales[sequence_id][layer_id][head][row];
        state_scale_tile[row] = unpack_state_scale(packed_scales, block);
      unpack_resident_lanes:
        for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          state_tile[row][lane] = unpack_state_element(packed_state, lane);
        }
      }
      phase2_decay_predict_tile(
          k_local[qk_head],
          k_scales_local[qk_head],
          alpha_local[head],
          state_tile,
          state_scale_tile,
          decayed_mantissas,
          decayed_exponents,
          prediction_mantissas,
          prediction_exponents,
          command_counters);
      phase3_delta_tile(
          v_local[head],
          v_scales_local[head],
          beta_local[head],
          block,
          prediction_mantissas,
          prediction_exponents,
          delta_mantissas,
          delta_exponents,
          command_counters);
      phase4_update_state_tile(
          k_local[qk_head],
          k_scales_local[qk_head],
          delta_mantissas,
          delta_exponents,
          decayed_mantissas,
          decayed_exponents,
          state_tile,
          state_scale_tile,
          updated_mantissas,
          updated_exponents,
          command_counters);
      phase5_output_tile(
          q_local[qk_head],
          q_scales_local[qk_head],
          block,
          updated_mantissas,
          updated_exponents,
          output_mantissas[head],
          output_exponents[head],
          command_counters);
    store_resident_tile:
      for (int row = 0; row < KEY_DIM; ++row) {
        state_block_word_t packed_state{};
      pack_resident_lanes:
        for (int lane = 0; lane < BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          pack_state_element(packed_state, lane, state_tile[row][lane]);
        }
        resident_state[sequence_id][layer_id][head][row][block] =
            packed_state;
        state_scale_word_t packed_scales =
            resident_scales[sequence_id][layer_id][head][row];
        pack_state_scale(packed_scales, block, state_scale_tile[row]);
        resident_scales[sequence_id][layer_id][head][row] = packed_scales;
      }
    }
  }

  ++generations[sequence_id][layer_id];
  command_counters[COUNTER_COMMITTED_STATE_GENERATIONS] = 1;
  accumulate_counters(command_counters, slot_counters);
  publish_result(
      STATUS_OK,
      generations[sequence_id][layer_id],
      command_counters,
      slot_counters,
      status_out,
      generation_out,
      command_counters_out,
      cumulative_counters_out);
}

}  // namespace GDN_NAMESPACE

void GDN_TOP_NAME(
    std::uint8_t command,
    std::uint16_t sequence_id,
    std::uint8_t layer_id,
    std::uint8_t payload_flags,
    const GDN_NAMESPACE::qk_tensor_t q,
    const GDN_NAMESPACE::qk_scale_tensor_t q_scales,
    const GDN_NAMESPACE::qk_tensor_t k,
    const GDN_NAMESPACE::qk_scale_tensor_t k_scales,
    const GDN_NAMESPACE::value_tensor_t v,
    const GDN_NAMESPACE::value_scale_tensor_t v_scales,
    const GDN_NAMESPACE::q1_15_head_t alpha,
    const GDN_NAMESPACE::q1_15_head_t beta,
    const GDN_NAMESPACE::state_tensor_t state_in,
    const GDN_NAMESPACE::state_scale_t state_scales_in,
    GDN_NAMESPACE::output_mantissa_t output_mantissas,
    GDN_NAMESPACE::output_exponent_t output_exponents,
    GDN_NAMESPACE::state_tensor_t state_out,
    GDN_NAMESPACE::state_scale_t state_scales_out,
    GDN_NAMESPACE::status_t status_out[1],
    GDN_NAMESPACE::generation_t generation_out[1],
    GDN_NAMESPACE::counter_array_t command_counters_out,
    GDN_NAMESPACE::counter_array_t cumulative_counters_out) {
#pragma HLS INTERFACE s_axilite port=command bundle=control
#pragma HLS INTERFACE s_axilite port=sequence_id bundle=control
#pragma HLS INTERFACE s_axilite port=layer_id bundle=control
#pragma HLS INTERFACE s_axilite port=payload_flags bundle=control
#pragma HLS INTERFACE m_axi port=q offset=slave bundle=gmem0
#pragma HLS INTERFACE m_axi port=q_scales offset=slave bundle=gmem0
#pragma HLS INTERFACE m_axi port=k offset=slave bundle=gmem1
#pragma HLS INTERFACE m_axi port=k_scales offset=slave bundle=gmem1
#pragma HLS INTERFACE m_axi port=v offset=slave bundle=gmem2
#pragma HLS INTERFACE m_axi port=v_scales offset=slave bundle=gmem2
#pragma HLS INTERFACE m_axi port=alpha offset=slave bundle=gmem3
#pragma HLS INTERFACE m_axi port=beta offset=slave bundle=gmem3
#pragma HLS INTERFACE m_axi port=state_in offset=slave bundle=gmem4
#pragma HLS INTERFACE m_axi port=state_scales_in offset=slave bundle=gmem4
#pragma HLS INTERFACE m_axi port=output_mantissas offset=slave bundle=gmem5
#pragma HLS INTERFACE m_axi port=output_exponents offset=slave bundle=gmem5
#pragma HLS INTERFACE m_axi port=state_out offset=slave bundle=gmem6
#pragma HLS INTERFACE m_axi port=state_scales_out offset=slave bundle=gmem6
#pragma HLS INTERFACE m_axi port=status_out offset=slave bundle=gmem7
#pragma HLS INTERFACE m_axi port=generation_out offset=slave bundle=gmem7
#pragma HLS INTERFACE m_axi port=command_counters_out offset=slave bundle=gmem7
#pragma HLS INTERFACE m_axi port=cumulative_counters_out offset=slave bundle=gmem7
#pragma HLS INTERFACE s_axilite port=return bundle=control

  GDN_NAMESPACE::GDN_TOP_IMPL_NAME(
      command,
      sequence_id,
      layer_id,
      payload_flags,
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
      command_counters_out,
      cumulative_counters_out);
}

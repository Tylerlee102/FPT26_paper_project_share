#include "gdn_rs2_kernel.hpp"

namespace gdn_rs2 {

namespace {

constexpr int HEADS_PER_QK = gdn::NUM_VALUE_HEADS / gdn::NUM_QK_HEADS;
constexpr int BASE_DOT_TERMS = STACK_DEPTH * 2 * gdn::KEY_DIM;
constexpr int LOG_DOT_TERMS = STACK_DEPTH * STACK_DEPTH * gdn::KEY_DIM;
constexpr int ACTION_TERMS = 1 + STACK_DEPTH * LOG_CAPACITY;
constexpr int FOLD_TERMS = 1 + LOG_CAPACITY;

e2m1_t unpack_e2m1(log_word_t word, int lane) {
#pragma HLS INLINE
  return word.range(4 * lane + 3, 4 * lane);
}

void pack_e2m1(log_word_t &word, int lane, e2m1_t value) {
#pragma HLS INLINE
  word.range(4 * lane + 3, 4 * lane) = value;
}

e2m1_t unpack_residual(state_residual_word_t word, int lane) {
#pragma HLS INLINE
  return word.range(4 * lane + 3, 4 * lane);
}

void pack_residual(state_residual_word_t &word, int lane, e2m1_t value) {
#pragma HLS INLINE
  word.range(4 * lane + 3, 4 * lane) = value;
}

scale_t unpack_scale(scale_word_t word, int block) {
#pragma HLS INLINE
  return word.range(8 * block + 7, 8 * block);
}

void pack_scale(scale_word_t &word, int block, scale_t value) {
#pragma HLS INLINE
  word.range(8 * block + 7, 8 * block) = value;
}

scale_word_t canonical_scale_word() {
#pragma HLS INLINE
  scale_word_t word = 0;
canonical_scale_blocks:
  for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
#pragma HLS UNROLL
    pack_scale(word, block, E8M0_BIAS);
  }
  return word;
}

void clear_counters(counters_t counters) {
#pragma HLS INLINE
clear_rs2_counters:
  for (int index = 0; index < COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    counters[index] = 0;
  }
}

void copy_counters(const counters_t source, counters_t destination) {
#pragma HLS INLINE
copy_rs2_counters:
  for (int index = 0; index < COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    destination[index] = source[index];
  }
}

void accumulate_counters(const counters_t source, counters_t destination) {
#pragma HLS INLINE
accumulate_rs2_counters:
  for (int index = 0; index < COUNTER_COUNT; ++index) {
#pragma HLS UNROLL
    destination[index] += source[index];
  }
}

void publish_result(
    std::uint8_t status,
    generation_t generation,
    const counters_t command_counters,
    const counters_t cumulative_counters,
    std::uint8_t status_out[1],
    generation_t generation_out[1],
    counters_t command_counters_out,
    counters_t cumulative_counters_out) {
#pragma HLS INLINE
  status_out[0] = status;
  generation_out[0] = generation;
  copy_counters(command_counters, command_counters_out);
  copy_counters(cumulative_counters, cumulative_counters_out);
}

std::uint8_t payload_status(std::uint8_t command, std::uint8_t flags) {
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

bool valid_e2m1_code(e2m1_t code) {
#pragma HLS INLINE
  return code != 8;
}

bool validate_qk_stack(
    const qk_elements_t elements,
    const qk_scales_t scales) {
#pragma HLS INLINE off
  bool valid = true;
validate_qk_terms:
  for (int term = 0; term < STACK_DEPTH; ++term) {
  validate_qk_heads:
    for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
    validate_qk_blocks:
      for (int block = 0; block < gdn::QK_BLOCKS; ++block) {
        bool all_zero = true;
        const scale_t scale = scales[term][head][block];
        valid = valid && scale != 255;
      validate_qk_lanes:
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          const e2m1_t code =
              elements[term][head][block * gdn::BLOCK_SIZE + lane];
          valid = valid && valid_e2m1_code(code);
          all_zero = all_zero && code == 0;
        }
        valid = valid && (!all_zero || scale == E8M0_BIAS);
      }
    }
  }
  return valid;
}

bool validate_value_stack(
    const value_elements_t elements,
    const value_scales_t scales) {
#pragma HLS INLINE off
  bool valid = true;
validate_value_terms:
  for (int term = 0; term < STACK_DEPTH; ++term) {
  validate_value_heads:
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    validate_value_blocks:
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        bool all_zero = true;
        const scale_t scale = scales[term][head][block];
        valid = valid && scale != 255;
      validate_value_lanes:
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          const e2m1_t code =
              elements[term][head][block * gdn::BLOCK_SIZE + lane];
          valid = valid && valid_e2m1_code(code);
          all_zero = all_zero && code == 0;
        }
        valid = valid && (!all_zero || scale == E8M0_BIAS);
      }
    }
  }
  return valid;
}

bool validate_token(
    const qk_elements_t q_elements,
    const qk_scales_t q_scales,
    const qk_elements_t k_elements,
    const qk_scales_t k_scales,
    const value_elements_t v_elements,
    const value_scales_t v_scales,
    const coefficient_heads_t alpha,
    const coefficient_heads_t beta) {
#pragma HLS INLINE off
  bool valid = validate_qk_stack(q_elements, q_scales) &&
               validate_qk_stack(k_elements, k_scales) &&
               validate_value_stack(v_elements, v_scales);
validate_token_coefficients:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    valid = valid && alpha[head] <= COEFFICIENT_ONE &&
            beta[head] <= COEFFICIENT_ONE;
  }
  return valid;
}

bool validate_snapshot(
    const state_primary_elements_t primary,
    const state_scales_t primary_scales,
    const state_residual_elements_t residual,
    const state_scales_t residual_scales,
    const log_key_elements_t keys,
    const log_key_scales_t key_scales,
    const log_update_elements_t updates,
    const log_update_scales_t update_scales,
    const coefficient_heads_t gamma,
    const lambda_t lambda,
    live_entries_t live_entries) {
#pragma HLS INLINE off
  bool valid = live_entries < LOG_CAPACITY;
validate_snapshot_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    valid = valid && gamma[head] <= COEFFICIENT_ONE;
  validate_snapshot_rows:
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
    validate_snapshot_blocks:
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        bool primary_zero = true;
        bool residual_zero = true;
        const scale_t primary_scale = primary_scales[head][row][block];
        const scale_t residual_scale = residual_scales[head][row][block];
        valid = valid && primary_scale != 255 && residual_scale != 255;
      validate_snapshot_lanes:
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          const int column = block * gdn::BLOCK_SIZE + lane;
          const e2m1_t primary_code = primary[head][row][column];
          const e2m1_t residual_code = residual[head][row][column];
          valid = valid && valid_e2m1_code(primary_code) &&
                  valid_e2m1_code(residual_code);
          primary_zero = primary_zero && primary_code == 0;
          residual_zero = residual_zero && residual_code == 0;
        }
        valid = valid && (!primary_zero || primary_scale == E8M0_BIAS) &&
                (!residual_zero || residual_scale == E8M0_BIAS);
      }
    }
  }

validate_snapshot_entries:
  for (int entry = 0; entry < LOG_CAPACITY; ++entry) {
    const bool active = entry < static_cast<int>(live_entries);
  validate_snapshot_key_terms:
    for (int term = 0; term < STACK_DEPTH; ++term) {
    validate_snapshot_key_heads:
      for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
      validate_snapshot_key_blocks:
        for (int block = 0; block < gdn::QK_BLOCKS; ++block) {
          bool all_zero = true;
          const scale_t scale = key_scales[entry][term][head][block];
          valid = valid && scale != 255;
        validate_snapshot_key_lanes:
          for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
            const e2m1_t code = keys[entry][term][head]
                                         [block * gdn::BLOCK_SIZE + lane];
            valid = valid && valid_e2m1_code(code);
            all_zero = all_zero && code == 0;
            valid = valid && (active || code == 0);
          }
          valid = valid && (!all_zero || scale == E8M0_BIAS) &&
                  (active || scale == E8M0_BIAS);
        }
      }
    }
  validate_snapshot_update_terms:
    for (int term = 0; term < STACK_DEPTH; ++term) {
    validate_snapshot_update_heads:
      for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
      validate_snapshot_update_blocks:
        for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
          bool all_zero = true;
          const scale_t scale = update_scales[entry][term][head][block];
          valid = valid && scale != 255;
        validate_snapshot_update_lanes:
          for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
            const e2m1_t code = updates[entry][term][head]
                                            [block * gdn::BLOCK_SIZE + lane];
            valid = valid && valid_e2m1_code(code);
            all_zero = all_zero && code == 0;
            valid = valid && (active || code == 0);
          }
          valid = valid && (!all_zero || scale == E8M0_BIAS) &&
                  (active || scale == E8M0_BIAS);
        }
      }
    }
  validate_snapshot_lambda:
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
      valid = valid && lambda[entry][head] <= COEFFICIENT_ONE &&
              (active || lambda[entry][head] == 0);
    }
  }
  return valid;
}

aligned_t dot_log_entry(
    const qk_elements_t vector_elements,
    const qk_scales_t vector_scales,
    int qk_head,
    int entry,
    const resident_key_log_t keys,
    const resident_key_scale_log_t key_scales,
    counters_t counters) {
#pragma HLS INLINE off
  wide_mantissa_t terms[LOG_DOT_TERMS];
  exponent_t exponents[LOG_DOT_TERMS];
#pragma HLS ARRAY_PARTITION variable=terms cyclic factor=gdn::P_K dim=1
#pragma HLS ARRAY_PARTITION variable=exponents cyclic factor=gdn::P_K dim=1
  int index = 0;
dot_log_vector_terms:
  for (int vector_term = 0; vector_term < STACK_DEPTH; ++vector_term) {
  dot_log_key_terms:
    for (int key_term = 0; key_term < STACK_DEPTH; ++key_term) {
    dot_log_rows:
      for (int row = 0; row < gdn::KEY_DIM; ++row) {
#pragma HLS PIPELINE II=1
        const int block = row / gdn::BLOCK_SIZE;
        const int lane = row % gdn::BLOCK_SIZE;
        terms[index] = product_e2m1(
            vector_elements[vector_term][qk_head][row],
            unpack_e2m1(keys[entry][key_term][qk_head][block], lane));
        exponents[index] =
            decode_scale(vector_scales[vector_term][qk_head][block]) +
            decode_scale(unpack_scale(key_scales[entry][key_term][qk_head], block));
        ++index;
      }
    }
  }
  return aligned_sum_guarded<LOG_DOT_TERMS>(terms, exponents, counters);
}

aligned_t dot_base_column(
    const qk_elements_t vector_elements,
    const qk_scales_t vector_scales,
    int qk_head,
    int value_head,
    int column,
    const resident_primary_slot_t primary,
    const resident_scale_slot_t primary_scales,
    const resident_residual_slot_t residual,
    const resident_scale_slot_t residual_scales,
    coefficient_t gamma,
    counters_t counters) {
#pragma HLS INLINE off
  wide_mantissa_t terms[BASE_DOT_TERMS];
  exponent_t exponents[BASE_DOT_TERMS];
#pragma HLS ARRAY_PARTITION variable=terms cyclic factor=gdn::P_K dim=1
#pragma HLS ARRAY_PARTITION variable=exponents cyclic factor=gdn::P_K dim=1
  const int value_block = column / gdn::BLOCK_SIZE;
  const int value_lane = column % gdn::BLOCK_SIZE;
  int index = 0;
dot_base_vector_terms:
  for (int vector_term = 0; vector_term < STACK_DEPTH; ++vector_term) {
  dot_base_state_terms:
    for (int state_term = 0; state_term < 2; ++state_term) {
    dot_base_rows:
      for (int row = 0; row < gdn::KEY_DIM; ++row) {
#pragma HLS PIPELINE II=1
        const int qk_block = row / gdn::BLOCK_SIZE;
        const e2m1_t vector_code = vector_elements[vector_term][qk_head][row];
        if (state_term == 0) {
          const e2m1_t state_code = unpack_e2m1(
              primary[value_head][row][value_block], value_lane);
          terms[index] = product_e2m1(vector_code, state_code);
          exponents[index] =
              decode_scale(vector_scales[vector_term][qk_head][qk_block]) +
              decode_scale(unpack_scale(primary_scales[value_head][row], value_block));
        } else {
          const e2m1_t state_code = unpack_residual(
              residual[value_head][row][value_block], value_lane);
          terms[index] = product_e2m1(vector_code, state_code);
          exponents[index] =
              decode_scale(vector_scales[vector_term][qk_head][qk_block]) +
              decode_scale(unpack_scale(residual_scales[value_head][row], value_block));
        }
        ++index;
      }
    }
  }
  aligned_t result = aligned_sum_guarded<BASE_DOT_TERMS>(
      terms, exponents, counters);
  result.mantissa = multiply_q1_15(result.mantissa, gamma, counters);
  return result;
}

aligned_t combine_action(
    aligned_t base,
    int qk_head,
    int value_head,
    int column,
    int live_entries,
    const mantissa_t log_dot_m[LOG_CAPACITY][gdn::NUM_QK_HEADS],
    const exponent_t log_dot_x[LOG_CAPACITY][gdn::NUM_QK_HEADS],
    const resident_update_log_t updates,
    const resident_update_scale_log_t update_scales,
    const lambda_t lambda,
    counters_t counters) {
#pragma HLS INLINE off
  wide_mantissa_t terms[ACTION_TERMS] = {};
  exponent_t exponents[ACTION_TERMS] = {};
#pragma HLS ARRAY_PARTITION variable=terms complete dim=1
#pragma HLS ARRAY_PARTITION variable=exponents complete dim=1
  terms[0] = base.mantissa;
  exponents[0] = base.exponent;
  const int block = column / gdn::BLOCK_SIZE;
  const int lane = column % gdn::BLOCK_SIZE;
combine_action_entries:
  for (int entry = 0; entry < LOG_CAPACITY; ++entry) {
#pragma HLS UNROLL
    if (entry < live_entries) {
      const mantissa_t scaled_dot = multiply_q1_15(
          log_dot_m[entry][qk_head], lambda[entry][value_head], counters);
    combine_action_update_terms:
      for (int update_term = 0; update_term < STACK_DEPTH; ++update_term) {
#pragma HLS UNROLL
        const int index = 1 + entry * STACK_DEPTH + update_term;
        const e2m1_t update_code = unpack_e2m1(
            updates[entry][update_term][value_head][block], lane);
        terms[index] = static_cast<wide_mantissa_t>(scaled_dot) *
                       static_cast<wide_mantissa_t>(decode_e2m1(update_code));
        exponents[index] =
            log_dot_x[entry][qk_head] +
            decode_scale(unpack_scale(
                update_scales[entry][update_term][value_head], block));
      }
    }
  }
  return aligned_sum_guarded<ACTION_TERMS>(terms, exponents, counters);
}

void quantize_update_block(
    const mantissa_t delta_m[gdn::BLOCK_SIZE],
    const exponent_t delta_x[gdn::BLOCK_SIZE],
    int entry,
    int head,
    int block,
    resident_update_log_t updates,
    resident_update_scale_log_t update_scales,
    counters_t counters) {
#pragma HLS INLINE off
  mantissa_t first_m[gdn::BLOCK_SIZE];
  exponent_t first_x[gdn::BLOCK_SIZE];
  mantissa_t residual_m[gdn::BLOCK_SIZE];
  exponent_t residual_x[gdn::BLOCK_SIZE];
#pragma HLS ARRAY_PARTITION variable=first_m complete dim=1
#pragma HLS ARRAY_PARTITION variable=first_x complete dim=1
#pragma HLS ARRAY_PARTITION variable=residual_m complete dim=1
#pragma HLS ARRAY_PARTITION variable=residual_x complete dim=1

  const int first_power = select_e2m1_scale_power(delta_m, delta_x, counters);
  log_word_t first_word = 0;
quantize_update_first:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
    const e2m1_t code = quantize_e2m1(
        delta_m[lane], delta_x[lane], first_power, counters);
    pack_e2m1(first_word, lane, code);
    first_m[lane] = decode_e2m1(code);
    first_x[lane] = first_power - 1;
    const wide_mantissa_t pair_m[2] = {
        delta_m[lane],
        static_cast<wide_mantissa_t>(-static_cast<ap_int<33>>(first_m[lane]))};
    const exponent_t pair_x[2] = {delta_x[lane], first_x[lane]};
    const aligned_t residual = aligned_sum_guarded<2>(pair_m, pair_x, counters);
    residual_m[lane] = residual.mantissa;
    residual_x[lane] = residual.exponent;
  }
  updates[entry][0][head][block] = first_word;
  pack_scale(update_scales[entry][0][head], block, first_power + E8M0_BIAS);

  const int second_power = select_e2m1_scale_power(
      residual_m, residual_x, counters);
  log_word_t second_word = 0;
quantize_update_second:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    pack_e2m1(
        second_word,
        lane,
        quantize_e2m1(
            residual_m[lane], residual_x[lane], second_power, counters));
  }
  updates[entry][1][head][block] = second_word;
  pack_scale(update_scales[entry][1][head], block, second_power + E8M0_BIAS);
}

void clear_log(
    resident_key_log_t keys,
    resident_key_scale_log_t key_scales,
    resident_update_log_t updates,
    resident_update_scale_log_t update_scales,
    lambda_t lambda) {
#pragma HLS INLINE off
  const scale_word_t canonical = canonical_scale_word();
clear_log_entries:
  for (int entry = 0; entry < LOG_CAPACITY; ++entry) {
  clear_log_terms:
    for (int term = 0; term < STACK_DEPTH; ++term) {
    clear_log_key_heads:
      for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
        key_scales[entry][term][head] = canonical;
      clear_log_key_blocks:
        for (int block = 0; block < gdn::QK_BLOCKS; ++block) {
#pragma HLS PIPELINE II=1
          keys[entry][term][head][block] = 0;
        }
      }
    clear_log_update_heads:
      for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
        update_scales[entry][term][head] = canonical;
      clear_log_update_blocks:
        for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
#pragma HLS PIPELINE II=1
          updates[entry][term][head][block] = 0;
        }
      }
    }
  clear_log_lambda:
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
#pragma HLS PIPELINE II=1
      lambda[entry][head] = 0;
    }
  }
}

void commit_fold_block(
    int head,
    int row,
    int block,
    state_primary_word_t primary_word,
    state_residual_word_t residual_word,
    scale_t primary_scale,
    scale_t residual_scale,
    resident_primary_slot_t primary,
    resident_scale_slot_t primary_scales,
    resident_residual_slot_t residual,
    resident_scale_slot_t residual_scales) {
#pragma HLS INLINE off
  primary[head][row][block] = primary_word;
  residual[head][row][block] = residual_word;
  pack_scale(primary_scales[head][row], block, primary_scale);
  pack_scale(residual_scales[head][row], block, residual_scale);
}

void quantize_fold_block(
    const mantissa_t state_m[gdn::BLOCK_SIZE],
    const exponent_t state_x[gdn::BLOCK_SIZE],
    int head,
    int row,
    int block,
    resident_primary_slot_t primary,
    resident_scale_slot_t primary_scales,
    resident_residual_slot_t residual,
    resident_scale_slot_t residual_scales,
    counters_t counters) {
#pragma HLS INLINE off
  mantissa_t primary_m[gdn::BLOCK_SIZE];
  exponent_t primary_x[gdn::BLOCK_SIZE];
  mantissa_t residual_m[gdn::BLOCK_SIZE];
  exponent_t residual_x[gdn::BLOCK_SIZE];
#pragma HLS ARRAY_PARTITION variable=primary_m complete dim=1
#pragma HLS ARRAY_PARTITION variable=primary_x complete dim=1
#pragma HLS ARRAY_PARTITION variable=residual_m complete dim=1
#pragma HLS ARRAY_PARTITION variable=residual_x complete dim=1

  const scale_t old_primary_scale = unpack_scale(primary_scales[head][row], block);
  const scale_t old_residual_scale = unpack_scale(residual_scales[head][row], block);
  const int primary_power = select_e2m1_scale_power(state_m, state_x, counters);
  state_primary_word_t primary_word = 0;
quantize_fold_primary:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
    const e2m1_t code = quantize_e2m1(
        state_m[lane], state_x[lane], primary_power, counters);
    pack_e2m1(primary_word, lane, code);
    primary_m[lane] = decode_e2m1(code);
    primary_x[lane] = primary_power - 1;
    const wide_mantissa_t pair_m[2] = {
        state_m[lane],
        static_cast<wide_mantissa_t>(-static_cast<ap_int<33>>(primary_m[lane]))};
    const exponent_t pair_x[2] = {state_x[lane], primary_x[lane]};
    const aligned_t remainder = aligned_sum_guarded<2>(pair_m, pair_x, counters);
    residual_m[lane] = remainder.mantissa;
    residual_x[lane] = remainder.exponent;
  }

  const int residual_power = select_e2m1_scale_power(
      residual_m, residual_x, counters);
  state_residual_word_t residual_word = 0;
quantize_fold_residual:
  for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
    const e2m1_t code = quantize_e2m1(
        residual_m[lane], residual_x[lane], residual_power, counters);
    pack_residual(residual_word, lane, code);
  }

  const scale_t new_primary_scale = primary_power + E8M0_BIAS;
  const scale_t new_residual_scale = residual_power + E8M0_BIAS;
  counters[COUNTER_STATE_SCALE_CHANGES] +=
      static_cast<unsigned>(old_primary_scale != new_primary_scale) +
      static_cast<unsigned>(old_residual_scale != new_residual_scale);
  commit_fold_block(
      head,
      row,
      block,
      primary_word,
      residual_word,
      new_primary_scale,
      new_residual_scale,
      primary,
      primary_scales,
      residual,
      residual_scales);
}

void fold_log(
    resident_primary_slot_t primary,
    resident_scale_slot_t primary_scales,
    resident_residual_slot_t residual,
    resident_scale_slot_t residual_scales,
    resident_key_log_t keys,
    resident_key_scale_log_t key_scales,
    resident_update_log_t updates,
    resident_update_scale_log_t update_scales,
    coefficient_heads_t gamma,
    lambda_t lambda,
    counters_t counters) {
#pragma HLS INLINE off
fold_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    const int qk_head = head / HEADS_PER_QK;
  fold_rows:
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
    fold_blocks:
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        mantissa_t state_m[gdn::BLOCK_SIZE];
        exponent_t state_x[gdn::BLOCK_SIZE];
#pragma HLS ARRAY_PARTITION variable=state_m complete dim=1
#pragma HLS ARRAY_PARTITION variable=state_x complete dim=1
      fold_lanes:
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
          wide_mantissa_t base_terms[2];
          exponent_t base_exponents[2];
#pragma HLS ARRAY_PARTITION variable=base_terms complete dim=1
#pragma HLS ARRAY_PARTITION variable=base_exponents complete dim=1
          base_terms[0] = decode_e2m1(
              unpack_e2m1(primary[head][row][block], lane));
          base_exponents[0] = decode_scale(
              unpack_scale(primary_scales[head][row], block));
          base_terms[1] = decode_e2m1(
              unpack_residual(residual[head][row][block], lane));
          base_exponents[1] = decode_scale(
              unpack_scale(residual_scales[head][row], block));
          aligned_t base = aligned_sum_guarded<2>(
              base_terms, base_exponents, counters);
          base.mantissa = multiply_q1_15(
              base.mantissa, gamma[head], counters);

          wide_mantissa_t fold_terms[FOLD_TERMS] = {};
          exponent_t fold_exponents[FOLD_TERMS] = {};
#pragma HLS ARRAY_PARTITION variable=fold_terms complete dim=1
#pragma HLS ARRAY_PARTITION variable=fold_exponents complete dim=1
          fold_terms[0] = base.mantissa;
          fold_exponents[0] = base.exponent;
        fold_entries:
          for (int entry = 0; entry < LOG_CAPACITY; ++entry) {
#pragma HLS UNROLL
            wide_mantissa_t rank_terms[4];
            exponent_t rank_exponents[4];
#pragma HLS ARRAY_PARTITION variable=rank_terms complete dim=1
#pragma HLS ARRAY_PARTITION variable=rank_exponents complete dim=1
            int rank_index = 0;
          fold_key_terms:
            for (int key_term = 0; key_term < STACK_DEPTH; ++key_term) {
#pragma HLS UNROLL
            fold_update_terms:
              for (int update_term = 0; update_term < STACK_DEPTH; ++update_term) {
#pragma HLS UNROLL
                const e2m1_t key_code = unpack_e2m1(
                    keys[entry][key_term][qk_head][row / gdn::BLOCK_SIZE],
                    row % gdn::BLOCK_SIZE);
                const e2m1_t update_code = unpack_e2m1(
                    updates[entry][update_term][head][block], lane);
                rank_terms[rank_index] = product_e2m1(key_code, update_code);
                rank_exponents[rank_index] =
                    decode_scale(unpack_scale(
                        key_scales[entry][key_term][qk_head],
                        row / gdn::BLOCK_SIZE)) +
                    decode_scale(unpack_scale(
                        update_scales[entry][update_term][head], block));
                ++rank_index;
              }
            }
            aligned_t rank = aligned_sum_guarded<4>(
                rank_terms, rank_exponents, counters);
            rank.mantissa = multiply_q1_15(
                rank.mantissa, lambda[entry][head], counters);
            fold_terms[entry + 1] = rank.mantissa;
            fold_exponents[entry + 1] = rank.exponent;
          }
          const aligned_t materialized = aligned_sum_guarded<FOLD_TERMS>(
              fold_terms, fold_exponents, counters);
          state_m[lane] = materialized.mantissa;
          state_x[lane] = materialized.exponent;
        }
        quantize_fold_block(
            state_m,
            state_x,
            head,
            row,
            block,
            primary,
            primary_scales,
            residual,
            residual_scales,
            counters);
      }
    }
    gamma[head] = COEFFICIENT_ONE;
  }
  clear_log(keys, key_scales, updates, update_scales, lambda);
  ++counters[COUNTER_FOLDS];
}

void fold_log_if_full(
    int live_after_step,
    resident_primary_slot_t primary,
    resident_scale_slot_t primary_scales,
    resident_residual_slot_t residual,
    resident_scale_slot_t residual_scales,
    resident_key_log_t keys,
    resident_key_scale_log_t key_scales,
    resident_update_log_t updates,
    resident_update_scale_log_t update_scales,
    coefficient_heads_t gamma,
    lambda_t lambda,
    counters_t counters) {
#pragma HLS INLINE off
  if (live_after_step != LOG_CAPACITY) {
    return;
  }
  fold_log(
      primary,
      primary_scales,
      residual,
      residual_scales,
      keys,
      key_scales,
      updates,
      update_scales,
      gamma,
      lambda,
      counters);
}

void reset_slot(
    resident_primary_slot_t primary,
    resident_scale_slot_t primary_scales,
    resident_residual_slot_t residual,
    resident_scale_slot_t residual_scales,
    resident_key_log_t keys,
    resident_key_scale_log_t key_scales,
    resident_update_log_t updates,
    resident_update_scale_log_t update_scales,
    coefficient_heads_t gamma,
    lambda_t lambda) {
#pragma HLS INLINE off
  const scale_word_t canonical = canonical_scale_word();
reset_rs2_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    gamma[head] = COEFFICIENT_ONE;
  reset_rs2_rows:
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
      primary_scales[head][row] = canonical;
      residual_scales[head][row] = canonical;
    reset_rs2_blocks:
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
#pragma HLS PIPELINE II=1
        primary[head][row][block] = 0;
        residual[head][row][block] = 0;
      }
    }
  }
  clear_log(keys, key_scales, updates, update_scales, lambda);
}

void store_key(
    int entry,
    const qk_elements_t k_elements,
    const qk_scales_t k_scales,
    resident_key_log_t keys,
    resident_key_scale_log_t key_scales) {
#pragma HLS INLINE off
store_key_terms:
  for (int term = 0; term < STACK_DEPTH; ++term) {
  store_key_heads:
    for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
      scale_word_t scales = 0;
    store_key_blocks:
      for (int block = 0; block < gdn::QK_BLOCKS; ++block) {
        log_word_t word = 0;
      store_key_lanes:
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          pack_e2m1(
              word,
              lane,
              k_elements[term][head][block * gdn::BLOCK_SIZE + lane]);
        }
        keys[entry][term][head][block] = word;
        pack_scale(scales, block, k_scales[term][head][block]);
      }
      key_scales[entry][term][head] = scales;
    }
  }
}

void commit_snapshot_block(
    int head,
    int row,
    int block,
    state_primary_word_t primary_word,
    state_residual_word_t residual_word,
    resident_primary_slot_t primary,
    resident_residual_slot_t residual) {
#pragma HLS INLINE off
  primary[head][row][block] = primary_word;
  residual[head][row][block] = residual_word;
}

void load_snapshot(
    const state_primary_elements_t primary_in,
    const state_scales_t primary_scales_in,
    const state_residual_elements_t residual_in,
    const state_scales_t residual_scales_in,
    const log_key_elements_t keys_in,
    const log_key_scales_t key_scales_in,
    const log_update_elements_t updates_in,
    const log_update_scales_t update_scales_in,
    const coefficient_heads_t gamma_in,
    const lambda_t lambda_in,
    resident_primary_slot_t primary,
    resident_scale_slot_t primary_scales,
    resident_residual_slot_t residual,
    resident_scale_slot_t residual_scales,
    resident_key_log_t keys,
    resident_key_scale_log_t key_scales,
    resident_update_log_t updates,
    resident_update_scale_log_t update_scales,
    coefficient_heads_t gamma,
    lambda_t lambda) {
#pragma HLS INLINE off
load_snapshot_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    gamma[head] = gamma_in[head];
  load_snapshot_rows:
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
      scale_word_t primary_scale_word = 0;
      scale_word_t residual_scale_word = 0;
    load_snapshot_blocks:
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        state_primary_word_t primary_word = 0;
        state_residual_word_t residual_word = 0;
      load_snapshot_lanes:
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          const int column = block * gdn::BLOCK_SIZE + lane;
          pack_e2m1(primary_word, lane, primary_in[head][row][column]);
          pack_residual(residual_word, lane, residual_in[head][row][column]);
        }
        commit_snapshot_block(
            head,
            row,
            block,
            primary_word,
            residual_word,
            primary,
            residual);
        pack_scale(
            primary_scale_word, block, primary_scales_in[head][row][block]);
        pack_scale(
            residual_scale_word, block, residual_scales_in[head][row][block]);
      }
      primary_scales[head][row] = primary_scale_word;
      residual_scales[head][row] = residual_scale_word;
    }
  }

load_snapshot_entries:
  for (int entry = 0; entry < LOG_CAPACITY; ++entry) {
  load_snapshot_terms:
    for (int term = 0; term < STACK_DEPTH; ++term) {
    load_snapshot_key_heads:
      for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
        scale_word_t scales = 0;
      load_snapshot_key_blocks:
        for (int block = 0; block < gdn::QK_BLOCKS; ++block) {
          log_word_t word = 0;
        load_snapshot_key_lanes:
          for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
            pack_e2m1(
                word,
                lane,
                keys_in[entry][term][head]
                       [block * gdn::BLOCK_SIZE + lane]);
          }
          keys[entry][term][head][block] = word;
          pack_scale(scales, block, key_scales_in[entry][term][head][block]);
        }
        key_scales[entry][term][head] = scales;
      }
    load_snapshot_update_heads:
      for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
        scale_word_t scales = 0;
      load_snapshot_update_blocks:
        for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
          log_word_t word = 0;
        load_snapshot_update_lanes:
          for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
            pack_e2m1(
                word,
                lane,
                updates_in[entry][term][head]
                          [block * gdn::BLOCK_SIZE + lane]);
          }
          updates[entry][term][head][block] = word;
          pack_scale(
              scales, block, update_scales_in[entry][term][head][block]);
        }
        update_scales[entry][term][head] = scales;
      }
    }
  load_snapshot_lambda:
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
#pragma HLS PIPELINE II=1
      lambda[entry][head] = lambda_in[entry][head];
    }
  }
}

void read_snapshot(
    const resident_primary_slot_t primary,
    const resident_scale_slot_t primary_scales,
    const resident_residual_slot_t residual,
    const resident_scale_slot_t residual_scales,
    const resident_key_log_t keys,
    const resident_key_scale_log_t key_scales,
    const resident_update_log_t updates,
    const resident_update_scale_log_t update_scales,
    const coefficient_heads_t gamma,
    const lambda_t lambda,
    state_primary_elements_t primary_out,
    state_scales_t primary_scales_out,
    state_residual_elements_t residual_out,
    state_scales_t residual_scales_out,
    log_key_elements_t keys_out,
    log_key_scales_t key_scales_out,
    log_update_elements_t updates_out,
    log_update_scales_t update_scales_out,
    coefficient_heads_t gamma_out,
    lambda_t lambda_out) {
#pragma HLS INLINE off
read_snapshot_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    gamma_out[head] = gamma[head];
  read_snapshot_rows:
    for (int row = 0; row < gdn::KEY_DIM; ++row) {
    read_snapshot_blocks:
      for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
        primary_scales_out[head][row][block] =
            unpack_scale(primary_scales[head][row], block);
        residual_scales_out[head][row][block] =
            unpack_scale(residual_scales[head][row], block);
      read_snapshot_lanes:
        for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
          const int column = block * gdn::BLOCK_SIZE + lane;
          primary_out[head][row][column] =
              unpack_e2m1(primary[head][row][block], lane);
          residual_out[head][row][column] =
              unpack_residual(residual[head][row][block], lane);
        }
      }
    }
  }

read_snapshot_entries:
  for (int entry = 0; entry < LOG_CAPACITY; ++entry) {
  read_snapshot_terms:
    for (int term = 0; term < STACK_DEPTH; ++term) {
    read_snapshot_key_heads:
      for (int head = 0; head < gdn::NUM_QK_HEADS; ++head) {
      read_snapshot_key_blocks:
        for (int block = 0; block < gdn::QK_BLOCKS; ++block) {
          key_scales_out[entry][term][head][block] =
              unpack_scale(key_scales[entry][term][head], block);
        read_snapshot_key_lanes:
          for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
            keys_out[entry][term][head]
                    [block * gdn::BLOCK_SIZE + lane] =
                unpack_e2m1(keys[entry][term][head][block], lane);
          }
        }
      }
    read_snapshot_update_heads:
      for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
      read_snapshot_update_blocks:
        for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
          update_scales_out[entry][term][head][block] =
              unpack_scale(update_scales[entry][term][head], block);
        read_snapshot_update_lanes:
          for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
#pragma HLS PIPELINE II=1
            updates_out[entry][term][head]
                       [block * gdn::BLOCK_SIZE + lane] =
                unpack_e2m1(updates[entry][term][head][block], lane);
          }
        }
      }
    }
  read_snapshot_lambda:
    for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
#pragma HLS PIPELINE II=1
      lambda_out[entry][head] = lambda[entry][head];
    }
  }
}

}  // namespace

void gdn_rs2_top_impl(
    std::uint8_t command,
    std::uint16_t sequence_id,
    std::uint8_t layer_id,
    std::uint8_t payload_flags,
    const qk_elements_t q_elements,
    const qk_scales_t q_scales,
    const qk_elements_t k_elements,
    const qk_scales_t k_scales,
    const value_elements_t v_elements,
    const value_scales_t v_scales,
    const coefficient_heads_t alpha,
    const coefficient_heads_t beta,
    const state_primary_elements_t state_primary_in,
    const state_scales_t state_primary_scales_in,
    const state_residual_elements_t state_residual_in,
    const state_scales_t state_residual_scales_in,
    const log_key_elements_t log_keys_in,
    const log_key_scales_t log_key_scales_in,
    const log_update_elements_t log_updates_in,
    const log_update_scales_t log_update_scales_in,
    const coefficient_heads_t gamma_in,
    const lambda_t lambda_in,
    live_entries_t live_entries_in,
    output_mantissas_t output_mantissas,
    output_exponents_t output_exponents,
    state_primary_elements_t state_primary_out,
    state_scales_t state_primary_scales_out,
    state_residual_elements_t state_residual_out,
    state_scales_t state_residual_scales_out,
    log_key_elements_t log_keys_out,
    log_key_scales_t log_key_scales_out,
    log_update_elements_t log_updates_out,
    log_update_scales_t log_update_scales_out,
    coefficient_heads_t gamma_out,
    lambda_t lambda_out,
    live_entries_t live_entries_out[1],
    std::uint8_t status_out[1],
    generation_t generation_out[1],
    counters_t command_counters_out,
    counters_t cumulative_counters_out) {
  static resident_primary_slot_t resident_primary[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS];
  static resident_residual_slot_t resident_residual[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS];
  static resident_scale_slot_t resident_primary_scales[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS];
  static resident_scale_slot_t resident_residual_scales[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS];
  static resident_key_log_t resident_keys[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS];
  static resident_key_scale_log_t resident_key_scales[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS];
  static resident_update_log_t resident_updates[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS];
  static resident_update_scale_log_t resident_update_scales[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS];
  static coefficient_t resident_gamma[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS][gdn::NUM_VALUE_HEADS];
  static coefficient_t resident_lambda[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS]
                                      [LOG_CAPACITY][gdn::NUM_VALUE_HEADS];
  static live_entries_t resident_live[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS] = {};
  static bool initialized[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS] = {};
  static generation_t generations[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS] = {};
  static counter_t cumulative[gdn::NUM_SEQUENCES][gdn::NUM_LAYERS][COUNTER_COUNT] = {};
#pragma HLS BIND_STORAGE variable=resident_primary type=ram_t2p impl=uram
#pragma HLS ARRAY_PARTITION variable=resident_primary cyclic factor=6 dim=2
#pragma HLS BIND_STORAGE variable=resident_residual type=ram_t2p impl=uram
#pragma HLS ARRAY_PARTITION variable=resident_residual cyclic factor=6 dim=2
#pragma HLS BIND_STORAGE variable=resident_primary_scales type=ram_t2p impl=bram
#pragma HLS BIND_STORAGE variable=resident_residual_scales type=ram_t2p impl=bram
#pragma HLS BIND_STORAGE variable=resident_keys type=ram_t2p impl=uram
#pragma HLS BIND_STORAGE variable=resident_updates type=ram_t2p impl=uram
#pragma HLS BIND_STORAGE variable=resident_key_scales type=ram_t2p impl=bram
#pragma HLS BIND_STORAGE variable=resident_update_scales type=ram_t2p impl=bram
#pragma HLS ARRAY_PARTITION variable=cumulative complete dim=3

  counters_t command_counters;
  counters_t empty_counters;
#pragma HLS ARRAY_PARTITION variable=command_counters complete dim=1
#pragma HLS ARRAY_PARTITION variable=empty_counters complete dim=1
  clear_counters(command_counters);
  clear_counters(empty_counters);

clear_rs2_output_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
  clear_rs2_output_values:
    for (int column = 0; column < gdn::VALUE_DIM; ++column) {
#pragma HLS PIPELINE II=1
      output_mantissas[head][column] = 0;
      output_exponents[head][column] = 0;
    }
  }

  if (sequence_id >= gdn::NUM_SEQUENCES) {
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

  counter_t *slot_counters = cumulative[sequence_id][layer_id];
  if (command > gdn::COMMAND_READBACK) {
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
  const std::uint8_t payload_error = payload_status(command, payload_flags);
  if (payload_error != gdn::STATUS_OK) {
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

  resident_primary_slot_t &primary = resident_primary[sequence_id][layer_id];
  resident_scale_slot_t &primary_scales =
      resident_primary_scales[sequence_id][layer_id];
  resident_residual_slot_t &residual = resident_residual[sequence_id][layer_id];
  resident_scale_slot_t &residual_scales =
      resident_residual_scales[sequence_id][layer_id];
  resident_key_log_t &keys = resident_keys[sequence_id][layer_id];
  resident_key_scale_log_t &key_scales =
      resident_key_scales[sequence_id][layer_id];
  resident_update_log_t &updates = resident_updates[sequence_id][layer_id];
  resident_update_scale_log_t &update_scales =
      resident_update_scales[sequence_id][layer_id];
  coefficient_t *gamma = resident_gamma[sequence_id][layer_id];
  coefficient_t (*lambda)[gdn::NUM_VALUE_HEADS] =
      resident_lambda[sequence_id][layer_id];

  if (command == gdn::COMMAND_RESET) {
    reset_slot(
        primary,
        primary_scales,
        residual,
        residual_scales,
        keys,
        key_scales,
        updates,
        update_scales,
        gamma,
        lambda);
    resident_live[sequence_id][layer_id] = 0;
    initialized[sequence_id][layer_id] = true;
    generations[sequence_id][layer_id] = 0;
    clear_counters(slot_counters);
    live_entries_out[0] = 0;
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
    if (!validate_snapshot(
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
            live_entries_in)) {
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
    load_snapshot(
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
        primary,
        primary_scales,
        residual,
        residual_scales,
        keys,
        key_scales,
        updates,
        update_scales,
        gamma,
        lambda);
    resident_live[sequence_id][layer_id] = live_entries_in;
    initialized[sequence_id][layer_id] = true;
    ++generations[sequence_id][layer_id];
    ++command_counters[COUNTER_COMMITTED_GENERATIONS];
    accumulate_counters(command_counters, slot_counters);
    live_entries_out[0] = live_entries_in;
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
    read_snapshot(
        primary,
        primary_scales,
        residual,
        residual_scales,
        keys,
        key_scales,
        updates,
        update_scales,
        gamma,
        lambda,
        state_primary_out,
        state_primary_scales_out,
        state_residual_out,
        state_residual_scales_out,
        log_keys_out,
        log_key_scales_out,
        log_updates_out,
        log_update_scales_out,
        gamma_out,
        lambda_out);
    live_entries_out[0] = resident_live[sequence_id][layer_id];
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

  if (!validate_token(
          q_elements,
          q_scales,
          k_elements,
          k_scales,
          v_elements,
          v_scales,
          alpha,
          beta)) {
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

  const int old_live = resident_live[sequence_id][layer_id].to_uint();
decay_coefficients_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    gamma[head] = multiply_coefficients(gamma[head], alpha[head]);
  decay_coefficients_entries:
    for (int entry = 0; entry < LOG_CAPACITY; ++entry) {
#pragma HLS UNROLL
      if (entry < old_live) {
        lambda[entry][head] = multiply_coefficients(
            lambda[entry][head], alpha[head]);
      }
    }
  }

  mantissa_t prediction_log_m[LOG_CAPACITY][gdn::NUM_QK_HEADS] = {};
  exponent_t prediction_log_x[LOG_CAPACITY][gdn::NUM_QK_HEADS] = {};
  mantissa_t output_log_m[LOG_CAPACITY][gdn::NUM_QK_HEADS] = {};
  exponent_t output_log_x[LOG_CAPACITY][gdn::NUM_QK_HEADS] = {};
#pragma HLS ARRAY_PARTITION variable=prediction_log_m complete dim=1
#pragma HLS ARRAY_PARTITION variable=prediction_log_x complete dim=1
#pragma HLS ARRAY_PARTITION variable=output_log_m complete dim=1
#pragma HLS ARRAY_PARTITION variable=output_log_x complete dim=1
prediction_log_entries:
  for (int entry = 0; entry < LOG_CAPACITY; ++entry) {
  prediction_log_heads:
    for (int qk_head = 0; qk_head < gdn::NUM_QK_HEADS; ++qk_head) {
      if (entry < old_live) {
        const aligned_t dot = dot_log_entry(
            k_elements,
            k_scales,
            qk_head,
            entry,
            keys,
            key_scales,
            command_counters);
        prediction_log_m[entry][qk_head] = dot.mantissa;
        prediction_log_x[entry][qk_head] = dot.exponent;
      }
    }
  }

  const int new_entry = old_live;
  store_key(new_entry, k_elements, k_scales, keys, key_scales);
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
#pragma HLS PIPELINE II=1
    lambda[new_entry][head] = COEFFICIENT_ONE;
  }

output_log_entries:
  for (int entry = 0; entry < LOG_CAPACITY; ++entry) {
  output_log_heads:
    for (int qk_head = 0; qk_head < gdn::NUM_QK_HEADS; ++qk_head) {
      if (entry <= old_live) {
        const aligned_t dot = dot_log_entry(
            q_elements,
            q_scales,
            qk_head,
            entry,
            keys,
            key_scales,
            command_counters);
        output_log_m[entry][qk_head] = dot.mantissa;
        output_log_x[entry][qk_head] = dot.exponent;
      }
    }
  }

step_rs2_heads:
  for (int head = 0; head < gdn::NUM_VALUE_HEADS; ++head) {
    const int qk_head = head / HEADS_PER_QK;
  step_rs2_blocks:
    for (int block = 0; block < gdn::VALUE_BLOCKS; ++block) {
      mantissa_t delta_m[gdn::BLOCK_SIZE];
      exponent_t delta_x[gdn::BLOCK_SIZE];
#pragma HLS ARRAY_PARTITION variable=delta_m complete dim=1
#pragma HLS ARRAY_PARTITION variable=delta_x complete dim=1
    step_rs2_lanes:
      for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
        const int column = block * gdn::BLOCK_SIZE + lane;
        const aligned_t prediction_base = dot_base_column(
            k_elements,
            k_scales,
            qk_head,
            head,
            column,
            primary,
            primary_scales,
            residual,
            residual_scales,
            gamma[head],
            command_counters);
        const aligned_t prediction = combine_action(
            prediction_base,
            qk_head,
            head,
            column,
            old_live,
            prediction_log_m,
            prediction_log_x,
            updates,
            update_scales,
            lambda,
            command_counters);

        wide_mantissa_t residual_terms[3] = {
            decode_e2m1(v_elements[0][head][column]),
            decode_e2m1(v_elements[1][head][column]),
            static_cast<wide_mantissa_t>(
                -static_cast<ap_int<33>>(prediction.mantissa))};
        exponent_t residual_exponents[3] = {
            decode_scale(v_scales[0][head][block]),
            decode_scale(v_scales[1][head][block]),
            prediction.exponent};
#pragma HLS ARRAY_PARTITION variable=residual_terms complete dim=1
#pragma HLS ARRAY_PARTITION variable=residual_exponents complete dim=1
        aligned_t delta = aligned_sum_guarded<3>(
            residual_terms, residual_exponents, command_counters);
        delta.mantissa = multiply_q1_15(
            delta.mantissa, beta[head], command_counters);
        delta_m[lane] = delta.mantissa;
        delta_x[lane] = delta.exponent;
      }
      quantize_update_block(
          delta_m,
          delta_x,
          new_entry,
          head,
          block,
          updates,
          update_scales,
          command_counters);

    output_rs2_lanes:
      for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
        const int column = block * gdn::BLOCK_SIZE + lane;
        const aligned_t output_base = dot_base_column(
            q_elements,
            q_scales,
            qk_head,
            head,
            column,
            primary,
            primary_scales,
            residual,
            residual_scales,
            gamma[head],
            command_counters);
        const aligned_t output = combine_action(
            output_base,
            qk_head,
            head,
            column,
            old_live + 1,
            output_log_m,
            output_log_x,
            updates,
            update_scales,
            lambda,
            command_counters);
        output_mantissas[head][column] = output.mantissa;
        output_exponents[head][column] = output.exponent;
      }
    }
  }

  const int live_after_step = old_live + 1;
  fold_log_if_full(
      live_after_step,
      primary,
      primary_scales,
      residual,
      residual_scales,
      keys,
      key_scales,
      updates,
      update_scales,
      gamma,
      lambda,
      command_counters);
  resident_live[sequence_id][layer_id] =
      live_after_step == LOG_CAPACITY ? 0 : live_after_step;

  ++generations[sequence_id][layer_id];
  ++command_counters[COUNTER_COMMITTED_GENERATIONS];
  accumulate_counters(command_counters, slot_counters);
  live_entries_out[0] = resident_live[sequence_id][layer_id];
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

}  // namespace gdn_rs2

void gdn_rs2_top(
    std::uint8_t command,
    std::uint16_t sequence_id,
    std::uint8_t layer_id,
    std::uint8_t payload_flags,
    const gdn_rs2::qk_elements_t q_elements,
    const gdn_rs2::qk_scales_t q_scales,
    const gdn_rs2::qk_elements_t k_elements,
    const gdn_rs2::qk_scales_t k_scales,
    const gdn_rs2::value_elements_t v_elements,
    const gdn_rs2::value_scales_t v_scales,
    const gdn_rs2::coefficient_heads_t alpha,
    const gdn_rs2::coefficient_heads_t beta,
    const gdn_rs2::state_primary_elements_t state_primary_in,
    const gdn_rs2::state_scales_t state_primary_scales_in,
    const gdn_rs2::state_residual_elements_t state_residual_in,
    const gdn_rs2::state_scales_t state_residual_scales_in,
    const gdn_rs2::log_key_elements_t log_keys_in,
    const gdn_rs2::log_key_scales_t log_key_scales_in,
    const gdn_rs2::log_update_elements_t log_updates_in,
    const gdn_rs2::log_update_scales_t log_update_scales_in,
    const gdn_rs2::coefficient_heads_t gamma_in,
    const gdn_rs2::lambda_t lambda_in,
    gdn_rs2::live_entries_t live_entries_in,
    gdn_rs2::output_mantissas_t output_mantissas,
    gdn_rs2::output_exponents_t output_exponents,
    gdn_rs2::state_primary_elements_t state_primary_out,
    gdn_rs2::state_scales_t state_primary_scales_out,
    gdn_rs2::state_residual_elements_t state_residual_out,
    gdn_rs2::state_scales_t state_residual_scales_out,
    gdn_rs2::log_key_elements_t log_keys_out,
    gdn_rs2::log_key_scales_t log_key_scales_out,
    gdn_rs2::log_update_elements_t log_updates_out,
    gdn_rs2::log_update_scales_t log_update_scales_out,
    gdn_rs2::coefficient_heads_t gamma_out,
    gdn_rs2::lambda_t lambda_out,
    gdn_rs2::live_entries_t live_entries_out[1],
    std::uint8_t status_out[1],
    gdn_rs2::generation_t generation_out[1],
    gdn_rs2::counters_t command_counters_out,
    gdn_rs2::counters_t cumulative_counters_out) {
#pragma HLS INTERFACE s_axilite port=command bundle=control
#pragma HLS INTERFACE s_axilite port=sequence_id bundle=control
#pragma HLS INTERFACE s_axilite port=layer_id bundle=control
#pragma HLS INTERFACE s_axilite port=payload_flags bundle=control
#pragma HLS INTERFACE m_axi port=q_elements offset=slave bundle=gmem0
#pragma HLS INTERFACE m_axi port=q_scales offset=slave bundle=gmem16
#pragma HLS INTERFACE m_axi port=k_elements offset=slave bundle=gmem1
#pragma HLS INTERFACE m_axi port=k_scales offset=slave bundle=gmem17
#pragma HLS INTERFACE m_axi port=v_elements offset=slave bundle=gmem2
#pragma HLS INTERFACE m_axi port=v_scales offset=slave bundle=gmem18
#pragma HLS INTERFACE m_axi port=alpha offset=slave bundle=gmem3
#pragma HLS INTERFACE m_axi port=beta offset=slave bundle=gmem3
#pragma HLS INTERFACE m_axi port=state_primary_in offset=slave bundle=gmem4
#pragma HLS INTERFACE m_axi port=state_primary_scales_in offset=slave bundle=gmem4
#pragma HLS INTERFACE m_axi port=state_residual_in offset=slave bundle=gmem5
#pragma HLS INTERFACE m_axi port=state_residual_scales_in offset=slave bundle=gmem5
#pragma HLS INTERFACE m_axi port=log_keys_in offset=slave bundle=gmem6
#pragma HLS INTERFACE m_axi port=log_key_scales_in offset=slave bundle=gmem6
#pragma HLS INTERFACE m_axi port=log_updates_in offset=slave bundle=gmem7
#pragma HLS INTERFACE m_axi port=log_update_scales_in offset=slave bundle=gmem7
#pragma HLS INTERFACE m_axi port=gamma_in offset=slave bundle=gmem8
#pragma HLS INTERFACE m_axi port=lambda_in offset=slave bundle=gmem8
#pragma HLS INTERFACE m_axi port=output_mantissas offset=slave bundle=gmem9
#pragma HLS INTERFACE m_axi port=output_exponents offset=slave bundle=gmem19
#pragma HLS INTERFACE m_axi port=state_primary_out offset=slave bundle=gmem10
#pragma HLS INTERFACE m_axi port=state_primary_scales_out offset=slave bundle=gmem10
#pragma HLS INTERFACE m_axi port=state_residual_out offset=slave bundle=gmem11
#pragma HLS INTERFACE m_axi port=state_residual_scales_out offset=slave bundle=gmem11
#pragma HLS INTERFACE m_axi port=log_keys_out offset=slave bundle=gmem12
#pragma HLS INTERFACE m_axi port=log_key_scales_out offset=slave bundle=gmem12
#pragma HLS INTERFACE m_axi port=log_updates_out offset=slave bundle=gmem13
#pragma HLS INTERFACE m_axi port=log_update_scales_out offset=slave bundle=gmem13
#pragma HLS INTERFACE m_axi port=gamma_out offset=slave bundle=gmem14
#pragma HLS INTERFACE m_axi port=lambda_out offset=slave bundle=gmem14
#pragma HLS INTERFACE m_axi port=live_entries_out offset=slave bundle=gmem15
#pragma HLS INTERFACE m_axi port=status_out offset=slave bundle=gmem15
#pragma HLS INTERFACE m_axi port=generation_out offset=slave bundle=gmem15
#pragma HLS INTERFACE m_axi port=command_counters_out offset=slave bundle=gmem15
#pragma HLS INTERFACE m_axi port=cumulative_counters_out offset=slave bundle=gmem15
#pragma HLS INTERFACE s_axilite port=return bundle=control

  gdn_rs2::gdn_rs2_top_impl(
      command,
      sequence_id,
      layer_id,
      payload_flags,
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
      live_entries_in,
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
      command_counters_out,
      cumulative_counters_out);
}

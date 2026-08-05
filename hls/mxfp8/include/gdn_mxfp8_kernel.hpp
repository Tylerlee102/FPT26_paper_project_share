#pragma once

#include "gdn_params.hpp"
#include "mx_types.hpp"

namespace gdn_mxfp8 {

constexpr int NUM_QK_HEADS = gdn::NUM_QK_HEADS;
constexpr int NUM_VALUE_HEADS = gdn::NUM_VALUE_HEADS;
constexpr int KEY_DIM = gdn::KEY_DIM;
constexpr int VALUE_DIM = gdn::VALUE_DIM;
constexpr int NUM_LAYERS = gdn::NUM_LAYERS;
constexpr int NUM_SEQUENCES = gdn::NUM_SEQUENCES;
constexpr int P_K = gdn::P_K;
constexpr int P_V = gdn::P_V;
constexpr int BLOCK_SIZE = gdn::BLOCK_SIZE;
constexpr int QK_BLOCKS = gdn::QK_BLOCKS;
constexpr int VALUE_BLOCKS = gdn::VALUE_BLOCKS;
constexpr int E8M0_BIAS = gdn::E8M0_BIAS;
constexpr int MX_ELEMENT_BITS = 8;

constexpr std::uint8_t COMMAND_RESET = gdn::COMMAND_RESET;
constexpr std::uint8_t COMMAND_LOAD = gdn::COMMAND_LOAD;
constexpr std::uint8_t COMMAND_STEP = gdn::COMMAND_STEP;
constexpr std::uint8_t COMMAND_READBACK = gdn::COMMAND_READBACK;
constexpr std::uint8_t STATUS_OK = gdn::STATUS_OK;
constexpr std::uint8_t STATUS_INVALID_COMMAND = gdn::STATUS_INVALID_COMMAND;
constexpr std::uint8_t STATUS_INVALID_SEQUENCE_ID = gdn::STATUS_INVALID_SEQUENCE_ID;
constexpr std::uint8_t STATUS_INVALID_LAYER_ID = gdn::STATUS_INVALID_LAYER_ID;
constexpr std::uint8_t STATUS_UNINITIALIZED_STATE = gdn::STATUS_UNINITIALIZED_STATE;
constexpr std::uint8_t STATUS_MISSING_PAYLOAD = gdn::STATUS_MISSING_PAYLOAD;
constexpr std::uint8_t STATUS_UNEXPECTED_PAYLOAD = gdn::STATUS_UNEXPECTED_PAYLOAD;
constexpr std::uint8_t STATUS_INVALID_ENCODING = gdn::STATUS_INVALID_ENCODING;
constexpr std::uint8_t STATUS_SHAPE_MISMATCH = gdn::STATUS_SHAPE_MISMATCH;
constexpr std::uint8_t PAYLOAD_NONE = gdn::PAYLOAD_NONE;
constexpr std::uint8_t PAYLOAD_STATE = gdn::PAYLOAD_STATE;
constexpr std::uint8_t PAYLOAD_TOKEN = gdn::PAYLOAD_TOKEN;

constexpr int COUNTER_ELEMENT_SATURATIONS = gdn::COUNTER_ELEMENT_SATURATIONS;
constexpr int COUNTER_ACCUMULATOR_SATURATIONS = gdn::COUNTER_ACCUMULATOR_SATURATIONS;
constexpr int COUNTER_SCALE_CLAMPS = gdn::COUNTER_SCALE_CLAMPS;
constexpr int COUNTER_ALIGNMENT_UNDERFLOWS = gdn::COUNTER_ALIGNMENT_UNDERFLOWS;
constexpr int COUNTER_STATE_SCALE_CHANGES = gdn::COUNTER_STATE_SCALE_CHANGES;
constexpr int COUNTER_INVALID_ENCODINGS = gdn::COUNTER_INVALID_ENCODINGS;
constexpr int COUNTER_REJECTED_COMMANDS = gdn::COUNTER_REJECTED_COMMANDS;
constexpr int COUNTER_COMMITTED_STATE_GENERATIONS = gdn::COUNTER_COMMITTED_STATE_GENERATIONS;
constexpr int COUNTER_COUNT = gdn::COUNTER_COUNT;

using mx_element_t = gdn::mx_e4m3_t;
using mx_scale_t = gdn::mx_scale_t;
using q1_15_t = gdn::q1_15_t;
using mantissa_t = gdn::mantissa_t;
using wide_mantissa_t = gdn::wide_mantissa_t;
using exponent_t = gdn::exponent_t;
using counter_t = gdn::counter_t;
using command_counter_t = gdn::command_counter_t;
using generation_t = gdn::generation_t;
using status_t = gdn::status_t;
using aligned_value_t = gdn::aligned_value_t;

using qk_tensor_t = mx_element_t[NUM_QK_HEADS][KEY_DIM];
using qk_scale_tensor_t = mx_scale_t[NUM_QK_HEADS][QK_BLOCKS];
using value_tensor_t = mx_element_t[NUM_VALUE_HEADS][VALUE_DIM];
using value_scale_tensor_t = mx_scale_t[NUM_VALUE_HEADS][VALUE_BLOCKS];
using q1_15_head_t = q1_15_t[NUM_VALUE_HEADS];
using state_tensor_t = mx_element_t[NUM_VALUE_HEADS][KEY_DIM][VALUE_DIM];
using state_scale_t = mx_scale_t[NUM_VALUE_HEADS][KEY_DIM][VALUE_BLOCKS];
using output_mantissa_t = mantissa_t[NUM_VALUE_HEADS][VALUE_DIM];
using output_exponent_t = exponent_t[NUM_VALUE_HEADS][VALUE_DIM];
using counter_array_t = counter_t[COUNTER_COUNT];
using command_counter_array_t = command_counter_t[COUNTER_COUNT];

using qk_head_t = mx_element_t[KEY_DIM];
using qk_head_scales_t = mx_scale_t[QK_BLOCKS];
using value_head_t = mx_element_t[VALUE_DIM];
using value_head_scales_t = mx_scale_t[VALUE_BLOCKS];
using state_block_tile_t = mx_element_t[KEY_DIM][BLOCK_SIZE];
using state_scale_tile_t = mx_scale_t[KEY_DIM];
using tile_mantissa_t = mantissa_t[KEY_DIM][BLOCK_SIZE];
using tile_exponent_t = exponent_t[KEY_DIM][BLOCK_SIZE];
using block_mantissa_t = mantissa_t[BLOCK_SIZE];
using block_exponent_t = exponent_t[BLOCK_SIZE];

bool phase1_validate_token(
    const qk_tensor_t q, const qk_scale_tensor_t q_scales,
    const qk_tensor_t k, const qk_scale_tensor_t k_scales,
    const value_tensor_t v, const value_scale_tensor_t v_scales,
    const q1_15_head_t alpha, const q1_15_head_t beta,
    qk_tensor_t q_local, qk_scale_tensor_t q_scales_local,
    qk_tensor_t k_local, qk_scale_tensor_t k_scales_local,
    value_tensor_t v_local, value_scale_tensor_t v_scales_local,
    q1_15_head_t alpha_local, q1_15_head_t beta_local);

bool phase1_validate_state(const state_tensor_t state, const state_scale_t state_scales);

void phase2_decay_predict_tile(
    const qk_head_t k, const qk_head_scales_t k_scales, q1_15_t alpha,
    const state_block_tile_t state, const state_scale_tile_t state_scales,
    tile_mantissa_t decayed_mantissas, tile_exponent_t decayed_exponents,
    block_mantissa_t prediction_mantissas, block_exponent_t prediction_exponents,
    command_counter_array_t counters);

void phase3_delta_tile(
    const value_head_t v, const value_head_scales_t v_scales, q1_15_t beta,
    int value_block, const block_mantissa_t prediction_mantissas,
    const block_exponent_t prediction_exponents, block_mantissa_t delta_mantissas,
    block_exponent_t delta_exponents, command_counter_array_t counters);

void phase4_update_state_tile(
    const qk_head_t k, const qk_head_scales_t k_scales,
    const block_mantissa_t delta_mantissas, const block_exponent_t delta_exponents,
    const tile_mantissa_t decayed_mantissas, const tile_exponent_t decayed_exponents,
    state_block_tile_t state, state_scale_tile_t state_scales,
    tile_mantissa_t updated_mantissas, tile_exponent_t updated_exponents,
    command_counter_array_t counters);

void phase5_output_tile(
    const qk_head_t q, const qk_head_scales_t q_scales, int value_block,
    const tile_mantissa_t updated_mantissas, const tile_exponent_t updated_exponents,
    mantissa_t output_mantissas[VALUE_DIM], exponent_t output_exponents[VALUE_DIM],
    command_counter_array_t counters);

void gdn_mxfp8_top_impl(
    std::uint8_t command, std::uint16_t sequence_id, std::uint8_t layer_id,
    std::uint8_t payload_flags, const qk_tensor_t q,
    const qk_scale_tensor_t q_scales, const qk_tensor_t k,
    const qk_scale_tensor_t k_scales, const value_tensor_t v,
    const value_scale_tensor_t v_scales, const q1_15_head_t alpha,
    const q1_15_head_t beta, const state_tensor_t state_in,
    const state_scale_t state_scales_in, output_mantissa_t output_mantissas,
    output_exponent_t output_exponents, state_tensor_t state_out,
    state_scale_t state_scales_out, status_t status_out[1],
    generation_t generation_out[1], counter_array_t command_counters_out,
    counter_array_t cumulative_counters_out);

}  // namespace gdn_mxfp8

void gdn_mxfp8_top(
    std::uint8_t command, std::uint16_t sequence_id, std::uint8_t layer_id,
    std::uint8_t payload_flags, const gdn_mxfp8::qk_tensor_t q,
    const gdn_mxfp8::qk_scale_tensor_t q_scales,
    const gdn_mxfp8::qk_tensor_t k,
    const gdn_mxfp8::qk_scale_tensor_t k_scales,
    const gdn_mxfp8::value_tensor_t v,
    const gdn_mxfp8::value_scale_tensor_t v_scales,
    const gdn_mxfp8::q1_15_head_t alpha,
    const gdn_mxfp8::q1_15_head_t beta,
    const gdn_mxfp8::state_tensor_t state_in,
    const gdn_mxfp8::state_scale_t state_scales_in,
    gdn_mxfp8::output_mantissa_t output_mantissas,
    gdn_mxfp8::output_exponent_t output_exponents,
    gdn_mxfp8::state_tensor_t state_out,
    gdn_mxfp8::state_scale_t state_scales_out,
    gdn_mxfp8::status_t status_out[1],
    gdn_mxfp8::generation_t generation_out[1],
    gdn_mxfp8::counter_array_t command_counters_out,
    gdn_mxfp8::counter_array_t cumulative_counters_out);

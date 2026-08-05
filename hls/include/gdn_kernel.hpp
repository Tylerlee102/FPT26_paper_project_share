#pragma once

#include "gdn_params.hpp"
#include "mx_types.hpp"

namespace gdn {

using mx_element_t = mx_e2m1_t;
constexpr int MX_ELEMENT_BITS = 4;

using qk_tensor_t = mx_element_t[NUM_QK_HEADS][KEY_DIM];
using qk_scale_tensor_t = mx_scale_t[NUM_QK_HEADS][QK_BLOCKS];
using value_tensor_t = mx_element_t[NUM_VALUE_HEADS][VALUE_DIM];
using value_scale_tensor_t = mx_scale_t[NUM_VALUE_HEADS][VALUE_BLOCKS];
using q1_15_head_t = q1_15_t[NUM_VALUE_HEADS];
using state_tensor_t = mx_element_t[NUM_VALUE_HEADS][KEY_DIM][VALUE_DIM];
using state_scale_t =
    mx_scale_t[NUM_VALUE_HEADS][KEY_DIM][VALUE_BLOCKS];
using output_mantissa_t = mantissa_t[NUM_VALUE_HEADS][VALUE_DIM];
using output_exponent_t = exponent_t[NUM_VALUE_HEADS][VALUE_DIM];
using counter_array_t = counter_t[COUNTER_COUNT];
using command_counter_array_t = command_counter_t[COUNTER_COUNT];

using qk_head_t = mx_element_t[KEY_DIM];
using qk_head_scales_t = mx_scale_t[QK_BLOCKS];
using value_head_t = mx_element_t[VALUE_DIM];
using value_head_scales_t = mx_scale_t[VALUE_BLOCKS];
using state_matrix_t = mx_element_t[KEY_DIM][VALUE_DIM];
using state_scale_matrix_t = mx_scale_t[KEY_DIM][VALUE_BLOCKS];
using state_block_tile_t = mx_element_t[KEY_DIM][BLOCK_SIZE];
using state_scale_tile_t = mx_scale_t[KEY_DIM];
using tile_mantissa_t = mantissa_t[KEY_DIM][BLOCK_SIZE];
using tile_exponent_t = exponent_t[KEY_DIM][BLOCK_SIZE];
using block_mantissa_t = mantissa_t[BLOCK_SIZE];
using block_exponent_t = exponent_t[BLOCK_SIZE];

bool phase1_validate_token(
    const qk_tensor_t q,
    const qk_scale_tensor_t q_scales,
    const qk_tensor_t k,
    const qk_scale_tensor_t k_scales,
    const value_tensor_t v,
    const value_scale_tensor_t v_scales,
    const q1_15_head_t alpha,
    const q1_15_head_t beta,
    qk_tensor_t q_local,
    qk_scale_tensor_t q_scales_local,
    qk_tensor_t k_local,
    qk_scale_tensor_t k_scales_local,
    value_tensor_t v_local,
    value_scale_tensor_t v_scales_local,
    q1_15_head_t alpha_local,
    q1_15_head_t beta_local);

bool phase1_validate_state(
    const state_tensor_t state,
    const state_scale_t state_scales);

void phase2_decay_predict_tile(
    const qk_head_t k,
    const qk_head_scales_t k_scales,
    q1_15_t alpha,
    const state_block_tile_t state,
    const state_scale_tile_t state_scales,
    tile_mantissa_t decayed_mantissas,
    tile_exponent_t decayed_exponents,
    block_mantissa_t prediction_mantissas,
    block_exponent_t prediction_exponents,
    command_counter_array_t counters);

void phase3_delta_tile(
    const value_head_t v,
    const value_head_scales_t v_scales,
    q1_15_t beta,
    int value_block,
    const block_mantissa_t prediction_mantissas,
    const block_exponent_t prediction_exponents,
    block_mantissa_t delta_mantissas,
    block_exponent_t delta_exponents,
    command_counter_array_t counters);

void phase4_update_state_tile(
    const qk_head_t k,
    const qk_head_scales_t k_scales,
    const block_mantissa_t delta_mantissas,
    const block_exponent_t delta_exponents,
    const tile_mantissa_t decayed_mantissas,
    const tile_exponent_t decayed_exponents,
    state_block_tile_t state,
    state_scale_tile_t state_scales,
    tile_mantissa_t updated_mantissas,
    tile_exponent_t updated_exponents,
    command_counter_array_t counters);

void phase5_output_tile(
    const qk_head_t q,
    const qk_head_scales_t q_scales,
    int value_block,
    const tile_mantissa_t updated_mantissas,
    const tile_exponent_t updated_exponents,
    mantissa_t output_mantissas[VALUE_DIM],
    exponent_t output_exponents[VALUE_DIM],
    command_counter_array_t counters);

void gdn_top_impl(
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
    counter_array_t cumulative_counters_out);

}  // namespace gdn

void gdn_top(
    std::uint8_t command,
    std::uint16_t sequence_id,
    std::uint8_t layer_id,
    std::uint8_t payload_flags,
    const gdn::qk_tensor_t q,
    const gdn::qk_scale_tensor_t q_scales,
    const gdn::qk_tensor_t k,
    const gdn::qk_scale_tensor_t k_scales,
    const gdn::value_tensor_t v,
    const gdn::value_scale_tensor_t v_scales,
    const gdn::q1_15_head_t alpha,
    const gdn::q1_15_head_t beta,
    const gdn::state_tensor_t state_in,
    const gdn::state_scale_t state_scales_in,
    gdn::output_mantissa_t output_mantissas,
    gdn::output_exponent_t output_exponents,
    gdn::state_tensor_t state_out,
    gdn::state_scale_t state_scales_out,
    gdn::status_t status_out[1],
    gdn::generation_t generation_out[1],
    gdn::counter_array_t command_counters_out,
    gdn::counter_array_t cumulative_counters_out);

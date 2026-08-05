#pragma once

#include <ap_float.h>
#include <ap_int.h>
#include <cstdint>

#include "gdn_params.hpp"
#include "mx_types.hpp"

namespace gdn_bf16 {

using bf16_bits_t = ap_uint<16>;
using bf16_t = ap_float_bf16;
using accum_t = ap_float_single;

using qk_tensor_t = bf16_bits_t[gdn::NUM_QK_HEADS][gdn::KEY_DIM];
using value_tensor_t = bf16_bits_t[gdn::NUM_VALUE_HEADS][gdn::VALUE_DIM];
using head_tensor_t = bf16_bits_t[gdn::NUM_VALUE_HEADS];
using state_tensor_t =
    bf16_bits_t[gdn::NUM_VALUE_HEADS][gdn::KEY_DIM][gdn::VALUE_DIM];
using output_tensor_t = bf16_bits_t[gdn::NUM_VALUE_HEADS][gdn::VALUE_DIM];

using qk_head_t = bf16_bits_t[gdn::KEY_DIM];
using value_head_t = bf16_bits_t[gdn::VALUE_DIM];
using state_tile_t = bf16_bits_t[gdn::KEY_DIM][gdn::BLOCK_SIZE];
using accum_tile_t = accum_t[gdn::KEY_DIM][gdn::BLOCK_SIZE];
using accum_block_t = accum_t[gdn::BLOCK_SIZE];

using counter_array_t = gdn::counter_t[gdn::COUNTER_COUNT];
using command_counter_array_t = gdn::command_counter_t[gdn::COUNTER_COUNT];

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
    counter_array_t cumulative_counters_out);

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
    gdn_bf16::counter_array_t cumulative_counters_out);

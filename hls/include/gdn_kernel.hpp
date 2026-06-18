#pragma once

#include "gdn_params.hpp"
#include "mx_types.hpp"

namespace gdn {

using head_vec_t = mx_e2m1_t[NUM_HEADS][HEAD_DIM];
using head_scale_t = mx_scale_t[NUM_HEADS][NUM_BLOCKS];
using state_tensor_t = mx_e2m1_t[NUM_HEADS][HEAD_DIM][HEAD_DIM];
using state_scale_t = mx_scale_t[NUM_HEADS][HEAD_DIM][STATE_BLOCKS];
#if GDN_HAS_AP_INT
using output_word_t = ap_uint<16 * P_V>;
#else
struct output_word_t {
  std::uint16_t lane[P_V];
};
#endif
using output_tensor_t = output_word_t[NUM_HEADS][HEAD_DIM / P_V];

void phase1_prepare(
    const head_scale_t q_scales,
    const head_scale_t k_scales,
    const head_scale_t v_scales,
    const head_scale_t gate_scales,
    mx_scale_t activation_exp[NUM_HEADS][4][NUM_BLOCKS]);

void phase2_state_read(
    const state_scale_t state_scales,
    mx_scale_t row_exp[NUM_HEADS][HEAD_DIM][STATE_BLOCKS]);

q4_3_t phase3_delta_update(q4_3_t state_q3, q4_3_t predicted_q3, q4_3_t value_q3, q4_3_t key_q3, std::uint8_t beta_u8);

void phase4_state_write(
    const state_tensor_t state_in,
    state_tensor_t state_out);

q4_3_t phase5_apply_gate(q4_3_t value_q3, q4_3_t gate_q3);

void gdn_top_impl(
    const head_vec_t q,
    const head_scale_t q_scales,
    const head_vec_t k,
    const head_scale_t k_scales,
    const head_vec_t v,
    const head_scale_t v_scales,
    const std::uint8_t beta[NUM_HEADS],
    const head_vec_t gate,
    const head_scale_t gate_scales,
    const state_tensor_t state_in,
    const state_scale_t state_scales,
    output_tensor_t output,
    state_tensor_t state_out);

}  // namespace gdn

void gdn_top(
    const gdn::head_vec_t q,
    const gdn::head_scale_t q_scales,
    const gdn::head_vec_t k,
    const gdn::head_scale_t k_scales,
    const gdn::head_vec_t v,
    const gdn::head_scale_t v_scales,
    const std::uint8_t beta[gdn::NUM_HEADS],
    const gdn::head_vec_t gate,
    const gdn::head_scale_t gate_scales,
    const gdn::state_tensor_t state_in,
    const gdn::state_scale_t state_scales,
    gdn::output_tensor_t output,
    gdn::state_tensor_t state_out);

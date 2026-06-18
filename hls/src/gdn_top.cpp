#include "gdn_kernel.hpp"

#include "mac_e2m1.hpp"

namespace gdn {

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
    state_tensor_t state_out) {
  mx_scale_t activation_exp[NUM_HEADS][4][NUM_BLOCKS];
  mx_scale_t state_exp[NUM_HEADS][HEAD_DIM][STATE_BLOCKS];
#pragma HLS ARRAY_PARTITION variable=activation_exp complete dim=2

  static head_vec_t q_buf;
  static head_vec_t k_buf;
  static head_vec_t v_buf;
  static head_vec_t gate_buf;
  static state_tensor_t resident_state;
  static q4_3_t output_buf[NUM_HEADS][HEAD_DIM];
#pragma HLS ARRAY_PARTITION variable=q_buf cyclic factor=P_K dim=2
#pragma HLS ARRAY_PARTITION variable=k_buf cyclic factor=P_K dim=2
#pragma HLS ARRAY_PARTITION variable=v_buf cyclic factor=P_V dim=2
#pragma HLS ARRAY_PARTITION variable=gate_buf cyclic factor=P_V dim=2
#pragma HLS ARRAY_PARTITION variable=output_buf cyclic factor=P_V dim=2
#pragma HLS BIND_STORAGE variable=resident_state type=ram_t2p impl=bram
#pragma HLS ARRAY_PARTITION variable=resident_state cyclic factor=P_V dim=2
#pragma HLS ARRAY_PARTITION variable=resident_state cyclic factor=P_K dim=3

  phase1_prepare(q_scales, k_scales, v_scales, gate_scales, activation_exp);
  phase2_state_read(state_scales, state_exp);

  load_heads:
  for (int h = 0; h < NUM_HEADS; ++h) {
    load_head_vecs:
    for (int r = 0; r < HEAD_DIM; ++r) {
#pragma HLS PIPELINE II=1
      q_buf[h][r] = q[h][r];
      k_buf[h][r] = k[h][r];
      v_buf[h][r] = v[h][r];
      gate_buf[h][r] = gate[h][r];
    }
  }

  q4_3_t predicted[NUM_HEADS][HEAD_DIM];
#pragma HLS ARRAY_PARTITION variable=predicted cyclic factor=P_V dim=2

  predict_heads:
  for (int h = 0; h < NUM_HEADS; ++h) {
    predict_row_tiles:
    for (int r0 = 0; r0 < HEAD_DIM; r0 += P_V) {
      acc32_t sum_q3[P_V];
#pragma HLS ARRAY_PARTITION variable=sum_q3 complete dim=1
      predict_init_rows:
      for (int pv = 0; pv < P_V; ++pv) {
#pragma HLS UNROLL
        sum_q3[pv] = 0;
      }
      predict_col_tiles:
      for (int c0 = 0; c0 < HEAD_DIM; c0 += P_K) {
#pragma HLS PIPELINE II=1
        predict_tile_rows:
        for (int pv = 0; pv < P_V; ++pv) {
#pragma HLS UNROLL
          predict_tile_cols:
          for (int pk = 0; pk < P_K; ++pk) {
#pragma HLS UNROLL
            sum_q3[pv] += static_cast<acc32_t>(
                e2m1_mul_q4_3(resident_state[h][r0 + pv][c0 + pk], k_buf[h][c0 + pk]));
          }
        }
      }
      predict_store_rows:
      for (int pv = 0; pv < P_V; ++pv) {
#pragma HLS UNROLL
        if (sum_q3[pv] > 32767) {
          predicted[h][r0 + pv] = 32767;
        } else if (sum_q3[pv] < -32768) {
          predicted[h][r0 + pv] = -32768;
        } else {
          predicted[h][r0 + pv] = static_cast<q4_3_t>(sum_q3[pv]);
        }
      }
    }
  }

  update_heads:
  for (int h = 0; h < NUM_HEADS; ++h) {
    update_row_tiles:
    for (int r0 = 0; r0 < HEAD_DIM; r0 += P_V) {
      acc32_t output_sum_q3[P_V];
#pragma HLS ARRAY_PARTITION variable=output_sum_q3 complete dim=1
      update_init_rows:
      for (int pv = 0; pv < P_V; ++pv) {
#pragma HLS UNROLL
        output_sum_q3[pv] = 0;
      }
      update_col_tiles:
      for (int c0 = 0; c0 < HEAD_DIM; c0 += P_K) {
#pragma HLS PIPELINE II=1
        update_tile_rows:
        for (int pv = 0; pv < P_V; ++pv) {
#pragma HLS UNROLL
          update_tile_cols:
          for (int pk = 0; pk < P_K; ++pk) {
#pragma HLS UNROLL
            const int r = r0 + pv;
            const int c = c0 + pk;
            const q4_3_t state_q3 = decode_e2m1_q3(resident_state[h][r][c]);
            const q4_3_t value_q3 = decode_e2m1_q3(v_buf[h][r]);
            const q4_3_t key_q3 = decode_e2m1_q3(k_buf[h][c]);
            const q4_3_t updated_q3 = phase3_delta_update(state_q3, predicted[h][r], value_q3, key_q3, beta[h]);
            const mx_e2m1_t encoded = encode_e2m1_q3(updated_q3);
            resident_state[h][r][c] = encoded;
            output_sum_q3[pv] += static_cast<acc32_t>(e2m1_mul_q4_3(encoded, q_buf[h][c]));
#if GDN_STATE_READBACK
            state_out[h][r][c] = encoded;
#endif
          }
        }
      }
      output_store_rows:
      for (int pv = 0; pv < P_V; ++pv) {
#pragma HLS UNROLL
        q4_3_t projected_q3 = 0;
        if (output_sum_q3[pv] > 32767) {
          projected_q3 = 32767;
        } else if (output_sum_q3[pv] < -32768) {
          projected_q3 = -32768;
        } else {
          projected_q3 = static_cast<q4_3_t>(output_sum_q3[pv]);
        }
        output_buf[h][r0 + pv] = projected_q3;
      }
    }
  }

  store_output_heads:
  for (int h = 0; h < NUM_HEADS; ++h) {
    store_output_row_tiles:
    for (int r0 = 0; r0 < HEAD_DIM; r0 += P_V) {
#pragma HLS PIPELINE II=1
      output_word_t packed = 0;
      store_output_lanes:
      for (int pv = 0; pv < P_V; ++pv) {
#pragma HLS UNROLL
        const int r = r0 + pv;
        const q4_3_t gated = phase5_apply_gate(output_buf[h][r], decode_e2m1_q3(gate_buf[h][r]));
#if GDN_HAS_AP_INT
        packed.range(16 * pv + 15, 16 * pv) = static_cast<ap_uint<16>>(gated);
#else
        packed.lane[pv] = static_cast<std::uint16_t>(gated);
#endif
      }
      output[h][r0 / P_V] = packed;
    }
  }
}

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
    gdn::state_tensor_t state_out) {
#pragma HLS INTERFACE m_axi port=q offset=slave bundle=gmem0
#pragma HLS INTERFACE m_axi port=q_scales offset=slave bundle=gmem0
#pragma HLS INTERFACE m_axi port=k offset=slave bundle=gmem1
#pragma HLS INTERFACE m_axi port=k_scales offset=slave bundle=gmem1
#pragma HLS INTERFACE m_axi port=v offset=slave bundle=gmem2
#pragma HLS INTERFACE m_axi port=v_scales offset=slave bundle=gmem2
#pragma HLS INTERFACE m_axi port=gate offset=slave bundle=gmem3
#pragma HLS INTERFACE m_axi port=gate_scales offset=slave bundle=gmem3
#pragma HLS INTERFACE m_axi port=state_in offset=slave bundle=gmem4
#pragma HLS INTERFACE m_axi port=state_scales offset=slave bundle=gmem4
#pragma HLS INTERFACE m_axi port=output offset=slave bundle=gmem5 max_widen_bitwidth=512
#pragma HLS INTERFACE m_axi port=state_out offset=slave bundle=gmem6
#pragma HLS INTERFACE s_axilite port=return bundle=control

  gdn::gdn_top_impl(
      q, q_scales, k, k_scales, v, v_scales, beta, gate, gate_scales,
      state_in, state_scales, output, state_out);
}

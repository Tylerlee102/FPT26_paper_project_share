#include <iostream>

#include "gdn_kernel.hpp"
#include "mac_e2m1.hpp"

#ifndef GDN_TB_VECTORS
#define GDN_TB_VECTORS 64
#endif

namespace {

gdn::mx_e2m1_t vector_value(int vector_id, int head, int row) {
  static const unsigned codes[8] = {0, 1, 2, 3, 4, 5, 10, 11};
  return static_cast<gdn::mx_e2m1_t>(codes[(vector_id * 17 + head * 5 + row) & 7]);
}

void clear_case(
    gdn::head_vec_t q,
    gdn::head_vec_t k,
    gdn::head_vec_t v,
    gdn::head_vec_t gate,
    gdn::head_scale_t q_scales,
    gdn::head_scale_t k_scales,
    gdn::head_scale_t v_scales,
    gdn::head_scale_t gate_scales,
    gdn::state_tensor_t state_in,
    gdn::state_scale_t state_scales,
    std::uint8_t beta[gdn::NUM_HEADS]) {
  for (int h = 0; h < gdn::NUM_HEADS; ++h) {
    beta[h] = 127;
    for (int b = 0; b < gdn::NUM_BLOCKS; ++b) {
      q_scales[h][b] = 127;
      k_scales[h][b] = 127;
      v_scales[h][b] = 127;
      gate_scales[h][b] = 127;
    }
    for (int r = 0; r < gdn::HEAD_DIM; ++r) {
      q[h][r] = 0;
      k[h][r] = 0;
      v[h][r] = 0;
      gate[h][r] = 2;  // +1.0
      for (int sb = 0; sb < gdn::STATE_BLOCKS; ++sb) {
        state_scales[h][r][sb] = 127;
      }
      for (int c = 0; c < gdn::HEAD_DIM; ++c) {
        state_in[h][r][c] = 0;
      }
    }
  }
}

gdn::q4_3_t output_lane(gdn::output_word_t word, int lane) {
#if GDN_HAS_AP_INT
  return static_cast<gdn::q4_3_t>(word.range(16 * lane + 15, 16 * lane));
#else
  return static_cast<gdn::q4_3_t>(word.lane[lane]);
#endif
}

}  // namespace

int main() {
  static gdn::head_vec_t q{};
  static gdn::head_vec_t k{};
  static gdn::head_vec_t v{};
  static gdn::head_vec_t gate{};
  static gdn::head_scale_t q_scales{};
  static gdn::head_scale_t k_scales{};
  static gdn::head_scale_t v_scales{};
  static gdn::head_scale_t gate_scales{};
  static gdn::state_tensor_t state_in{};
  static gdn::state_scale_t state_scales{};
  static gdn::output_tensor_t output{};
  static gdn::state_tensor_t state_out{};
  static std::uint8_t beta[gdn::NUM_HEADS]{};

  int passed = 0;
  for (int vector_id = 0; vector_id < GDN_TB_VECTORS; ++vector_id) {
    clear_case(q, k, v, gate, q_scales, k_scales, v_scales, gate_scales, state_in, state_scales, beta);
    const int pivot = (vector_id * 13) % gdn::HEAD_DIM;
    for (int h = 0; h < gdn::NUM_HEADS; ++h) {
      q[h][pivot] = 2;  // +1.0
      k[h][pivot] = 2;  // +1.0
      for (int r = 0; r < gdn::HEAD_DIM; ++r) {
        v[h][r] = vector_value(vector_id, h, r);
      }
    }

    gdn_top(
        q, q_scales, k, k_scales, v, v_scales, beta, gate, gate_scales,
        state_in, state_scales, output, state_out);

    for (int h = 0; h < gdn::NUM_HEADS; ++h) {
      for (int r = 0; r < gdn::HEAD_DIM; ++r) {
        const int expected_output = static_cast<int>(gdn::decode_e2m1_q3(v[h][r]));
        const int got_output = static_cast<int>(output_lane(output[h][r / gdn::P_V], r % gdn::P_V));
        if (got_output != expected_output) {
          std::cerr << "vector " << vector_id << " output mismatch h=" << h << " r=" << r
                    << " got=" << got_output
                    << " expected=" << expected_output << "\n";
          return 1;
        }
#if GDN_STATE_READBACK
        for (int c = 0; c < gdn::HEAD_DIM; ++c) {
          const gdn::mx_e2m1_t expected_state = (c == pivot) ? v[h][r] : static_cast<gdn::mx_e2m1_t>(0);
          if (state_out[h][r][c] != expected_state) {
            std::cerr << "vector " << vector_id << " state mismatch h=" << h << " r=" << r
                      << " c=" << c << " got=" << static_cast<int>(state_out[h][r][c])
                      << " expected=" << static_cast<int>(expected_state) << "\n";
            return 1;
          }
        }
#endif
      }
    }
    ++passed;
  }

  std::cout << "tb_gdn_top PASS vectors=" << passed << "/" << GDN_TB_VECTORS << "\n";
  return 0;
}

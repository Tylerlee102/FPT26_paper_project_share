#include "gdn_e2m0_kernel.hpp"

#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>

namespace {

bool expect_label(std::istream &input, const char *expected) {
  std::string actual;
  input >> actual;
  if (actual != expected) {
    std::cerr << "expected label " << expected << ", got " << actual << "\n";
    return false;
  }
  return true;
}

bool primitive_checks() {
  static const int e2m1_magnitudes[8] = {0, 1, 2, 3, 4, 6, 8, 12};
  static const int e2m0_magnitudes[4] = {0, 1, 2, 4};
  for (unsigned code = 0; code < 16; ++code) {
    const int magnitude = e2m1_magnitudes[code & 7u];
    const int expected = (code & 8u) != 0u && magnitude != 0 ? -magnitude : magnitude;
    if (gdn_e2m0::decode_e2m1(code).to_int() != expected) {
      std::cerr << "E2M1 decode mismatch at code " << code << "\n";
      return false;
    }
  }
  for (unsigned code = 0; code < 8; ++code) {
    const int magnitude = e2m0_magnitudes[code & 3u];
    const int expected = (code & 4u) != 0u && magnitude != 0 ? -magnitude : magnitude;
    if (gdn_e2m0::decode_e2m0(code).to_int() != expected) {
      std::cerr << "E2M0 decode mismatch at code " << code << "\n";
      return false;
    }
  }
  if (gdn_e2m0::decode_scale(0).to_int() != -128 ||
      gdn_e2m0::decode_scale(127).to_int() != -1 ||
      gdn_e2m0::decode_scale(254).to_int() != 126) {
    std::cerr << "E8M0 decode mismatch\n";
    return false;
  }
  if (gdn_e2m0::round_shift_rne(5, 1).to_int64() != 2 ||
      gdn_e2m0::round_shift_rne(7, 1).to_int64() != 4 ||
      gdn_e2m0::round_shift_rne(-5, 1).to_int64() != -2 ||
      gdn_e2m0::round_shift_rne(-7, 1).to_int64() != -4) {
    std::cerr << "signed RNE mismatch\n";
    return false;
  }
  gdn_e2m0::counter_t counters[gdn_e2m0::COUNTER_COUNT] = {};
  if (gdn_e2m0::multiply_q1_15(7, 16384, counters).to_int() != 4 ||
      gdn_e2m0::multiply_q1_15(-7, 16384, counters).to_int() != -4 ||
      gdn_e2m0::multiply_coefficients(32768, 32768).to_uint() != 32768 ||
      gdn_e2m0::multiply_coefficients(16384, 16384).to_uint() != 8192) {
    std::cerr << "Q1.15 arithmetic mismatch\n";
    return false;
  }
  return true;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "usage: tb_e2m0_arithmetic VECTOR_FILE\n";
    return 2;
  }
  if (!primitive_checks()) {
    return 1;
  }

  std::ifstream input(argv[1]);
  if (!input) {
    std::cerr << "cannot open vector file " << argv[1] << "\n";
    return 2;
  }
  std::string magic;
  int case_count = 0;
  input >> magic >> case_count;
  if (magic != "E2M0_ARITHMETIC_V1" || case_count <= 0) {
    std::cerr << "invalid vector header\n";
    return 2;
  }

  for (int expected_case = 0; expected_case < case_count; ++expected_case) {
    if (!expect_label(input, "CASE")) {
      return 2;
    }
    int case_id = -1;
    input >> case_id;
    if (case_id != expected_case) {
      std::cerr << "unexpected case id " << case_id << "\n";
      return 2;
    }

    gdn_e2m0::mantissa_t mantissas[gdn::BLOCK_SIZE];
    gdn_e2m0::exponent_t exponents[gdn::BLOCK_SIZE];
    for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
      std::int64_t mantissa = 0;
      int exponent = 0;
      input >> mantissa >> exponent;
      mantissas[lane] = mantissa;
      exponents[lane] = exponent;
    }

    std::int64_t expected_aligned_m = 0;
    int expected_aligned_e = 0;
    if (!expect_label(input, "ALIGNED")) {
      return 2;
    }
    input >> expected_aligned_m >> expected_aligned_e;

    int expected_e2m1_power = 0;
    unsigned expected_e2m1[gdn::BLOCK_SIZE];
    if (!expect_label(input, "E2M1")) {
      return 2;
    }
    input >> expected_e2m1_power;
    for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
      input >> expected_e2m1[lane];
    }

    int expected_upper = 0;
    int expected_selected = 0;
    unsigned expected_choose_lower = 0;
    unsigned expected_e2m0[gdn::BLOCK_SIZE];
    if (!expect_label(input, "E2M0")) {
      return 2;
    }
    input >> expected_upper >> expected_selected >> expected_choose_lower;
    for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
      input >> expected_e2m0[lane];
    }

    std::uint64_t expected_counters[gdn_e2m0::COUNTER_COUNT];
    if (!expect_label(input, "COUNTERS")) {
      return 2;
    }
    for (int index = 0; index < gdn_e2m0::COUNTER_COUNT; ++index) {
      input >> expected_counters[index];
    }
    if (!input) {
      std::cerr << "truncated vector case " << case_id << "\n";
      return 2;
    }

    gdn_e2m0::e2m1_t actual_e2m1[gdn::BLOCK_SIZE];
    gdn_e2m0::e2m0_t actual_e2m0[gdn::BLOCK_SIZE];
    gdn_e2m0::exponent_t actual_scales[3];
    ap_uint<1> actual_choose_lower[1];
    gdn_e2m0::mantissa_t actual_aligned_m[1];
    gdn_e2m0::exponent_t actual_aligned_e[1];
    gdn_e2m0::counter_t actual_counters[gdn_e2m0::COUNTER_COUNT];
    e2m0_arithmetic_top(
        mantissas,
        exponents,
        actual_e2m1,
        actual_e2m0,
        actual_scales,
        actual_choose_lower,
        actual_aligned_m,
        actual_aligned_e,
        actual_counters);

    bool match = actual_aligned_m[0].to_int64() == expected_aligned_m &&
                 actual_aligned_e[0].to_int() == expected_aligned_e &&
                 actual_scales[0].to_int() == expected_e2m1_power &&
                 actual_scales[1].to_int() == expected_upper &&
                 actual_scales[2].to_int() == expected_selected &&
                 actual_choose_lower[0].to_uint() == expected_choose_lower;
    for (int lane = 0; lane < gdn::BLOCK_SIZE; ++lane) {
      match = match && actual_e2m1[lane].to_uint() == expected_e2m1[lane] &&
              actual_e2m0[lane].to_uint() == expected_e2m0[lane];
    }
    for (int index = 0; index < gdn_e2m0::COUNTER_COUNT; ++index) {
      match = match && actual_counters[index].to_uint64() == expected_counters[index];
    }
    if (!match) {
      std::cerr << "oracle mismatch in case " << case_id << "\n";
      std::cerr << "aligned expected " << expected_aligned_m << " @ "
                << expected_aligned_e << ", actual "
                << actual_aligned_m[0].to_int64() << " @ "
                << actual_aligned_e[0].to_int() << "\n";
      std::cerr << "scales expected " << expected_e2m1_power << " "
                << expected_upper << " " << expected_selected << ", actual "
                << actual_scales[0].to_int() << " "
                << actual_scales[1].to_int() << " "
                << actual_scales[2].to_int() << "\n";
      return 1;
    }
  }

  std::cout << "PASS: " << case_count
            << " frozen-oracle arithmetic cases plus primitive checks\n";
  return 0;
}

#pragma once

#include "gdn_params.hpp"
#include "mx_types.hpp"

namespace gdn {

wide_mantissa_t round_shift_rne(wide_mantissa_t value, int shift);
mantissa_t saturate_int32(
    wide_mantissa_t value,
    command_counter_t counters[COUNTER_COUNT]);
mantissa_t multiply_q1_15(
    mantissa_t value,
    q1_15_t coefficient,
    command_counter_t counters[COUNTER_COUNT]);
aligned_value_t aligned_sum(
    const wide_mantissa_t mantissas[KEY_DIM],
    const exponent_t exponents[KEY_DIM],
    int count,
    command_counter_t counters[COUNTER_COUNT]);
aligned_value_t aligned_pair(
    wide_mantissa_t first_mantissa,
    exponent_t first_exponent,
    wide_mantissa_t second_mantissa,
    exponent_t second_exponent,
    bool& alignment_underflow,
    command_counter_t counters[COUNTER_COUNT]);

}  // namespace gdn

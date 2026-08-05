#pragma once

#include "gdn_mxfp8_kernel.hpp"

namespace gdn_mxfp8 {

unsigned raw_e4m3(mx_element_t value);
bool valid_e4m3(mx_element_t value);
mantissa_t decode_e4m3_mantissa(mx_element_t value);
exponent_t decode_e4m3_exponent(mx_element_t value, mx_scale_t scale);
wide_mantissa_t scale_by_e4m3(mx_element_t coefficient, mantissa_t value);
int select_scale_power_e4m3(
    const mantissa_t mantissas[BLOCK_SIZE],
    const exponent_t exponents[BLOCK_SIZE],
    command_counter_array_t counters);
mx_element_t quantize_exact_e4m3(
    mantissa_t mantissa,
    exponent_t exponent,
    int scale_power,
    command_counter_array_t counters);

}  // namespace gdn_mxfp8

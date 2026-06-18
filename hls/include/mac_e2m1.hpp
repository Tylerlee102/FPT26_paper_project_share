#pragma once

#include "mx_types.hpp"

namespace gdn {

q4_3_t decode_e2m1_q3(mx_e2m1_t x);
mx_e2m1_t encode_e2m1_q3(q4_3_t x_q3);
q4_3_t e2m1_mul_q4_3(mx_e2m1_t a, mx_e2m1_t b);

}  // namespace gdn

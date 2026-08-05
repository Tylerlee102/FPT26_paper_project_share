#pragma once

#include "mx_types.hpp"

namespace gdn {

mantissa_t decode_e2m1_mantissa(mx_e2m1_t value);
exponent_t decode_e2m1_exponent(mx_scale_t scale);
wide_mantissa_t e2m1_product_mantissa(mx_e2m1_t a, mx_e2m1_t b);
wide_mantissa_t scale_by_e2m1(mx_e2m1_t coefficient, mantissa_t value);

}  // namespace gdn

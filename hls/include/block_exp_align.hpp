#pragma once

#include "mx_types.hpp"

namespace gdn {

std::int16_t effective_block_exp(mx_scale_t exp_a, mx_scale_t exp_b);
block_accum_t block_exp_align_accumulate(const mx_partial_t partials[], int count);

}  // namespace gdn


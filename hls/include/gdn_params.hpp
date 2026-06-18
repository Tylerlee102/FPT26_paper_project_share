#pragma once

namespace gdn {

constexpr int NUM_HEADS = 32;
constexpr int HEAD_DIM = 128;

#ifndef GDN_P_K
#define GDN_P_K 16
#endif

#ifndef GDN_P_V
#define GDN_P_V 8
#endif

#ifndef GDN_BLOCK_SIZE
#define GDN_BLOCK_SIZE 32
#endif

#ifndef GDN_STATE_READBACK
#define GDN_STATE_READBACK 0
#endif

constexpr int P_K = GDN_P_K;
constexpr int P_V = GDN_P_V;
constexpr int BLOCK_SIZE = GDN_BLOCK_SIZE;
constexpr float CLOCK_NS = 4.0f;
constexpr bool USE_MXFP4 = true;
constexpr bool STATE_READBACK = GDN_STATE_READBACK != 0;

constexpr int STATE_BLOCK_SIZE = 16;
constexpr int NUM_BLOCKS = HEAD_DIM / BLOCK_SIZE;
constexpr int STATE_BLOCKS = HEAD_DIM / STATE_BLOCK_SIZE;
constexpr int E8M0_BIAS = 127;
constexpr int INT24_MIN = -(1 << 23);
constexpr int INT24_MAX = (1 << 23) - 1;

static_assert(HEAD_DIM % BLOCK_SIZE == 0, "HEAD_DIM must be divisible by BLOCK_SIZE");
static_assert(HEAD_DIM % STATE_BLOCK_SIZE == 0, "HEAD_DIM must be divisible by STATE_BLOCK_SIZE");
static_assert(HEAD_DIM % P_K == 0, "HEAD_DIM must be divisible by P_K");
static_assert(HEAD_DIM % P_V == 0, "HEAD_DIM must be divisible by P_V");
static_assert(BLOCK_SIZE == 16 || BLOCK_SIZE == 32, "MXFP4 block size must be 16 or 32");
static_assert(P_K == 8 || P_K == 16 || P_K == 32, "P_K must match a Phase 6 sweep point");
static_assert(P_V == 4 || P_V == 8 || P_V == 16, "P_V must match a Phase 6 sweep point");

}  // namespace gdn

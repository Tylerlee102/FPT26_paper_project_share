#pragma once

#include <cstdint>

namespace gdn {

constexpr int NUM_QK_HEADS = 16;
constexpr int NUM_VALUE_HEADS = 32;
constexpr int KEY_DIM = 128;
constexpr int VALUE_DIM = 128;
constexpr int NUM_LAYERS = 36;

#ifndef GDN_NUM_SEQUENCES
#define GDN_NUM_SEQUENCES 1
#endif

#ifndef GDN_P_K
#define GDN_P_K 16
#endif

#ifndef GDN_P_V
#define GDN_P_V 8
#endif

#ifndef GDN_BLOCK_SIZE
#define GDN_BLOCK_SIZE 32
#endif

constexpr int NUM_SEQUENCES = GDN_NUM_SEQUENCES;
constexpr int P_K = GDN_P_K;
constexpr int P_V = GDN_P_V;
constexpr int BLOCK_SIZE = GDN_BLOCK_SIZE;
constexpr int QK_BLOCKS = KEY_DIM / BLOCK_SIZE;
constexpr int VALUE_BLOCKS = VALUE_DIM / BLOCK_SIZE;
constexpr float CLOCK_NS = 4.0f;
constexpr bool USE_MXFP4 = true;
constexpr int E8M0_BIAS = 127;
constexpr std::uint64_t MAX_COMMAND_EVENT_BOUND =
    8ull * NUM_VALUE_HEADS * VALUE_BLOCKS * KEY_DIM * BLOCK_SIZE;

// Compatibility names used by report extractors; the corrected boundary uses
// the explicit Q/K and value-head constants above.
constexpr int NUM_HEADS = NUM_VALUE_HEADS;
constexpr int HEAD_DIM = VALUE_DIM;
constexpr int NUM_BLOCKS = VALUE_BLOCKS;
constexpr int STATE_BLOCKS = VALUE_BLOCKS;

enum ResidentCommand : std::uint8_t {
  COMMAND_RESET = 0,
  COMMAND_LOAD = 1,
  COMMAND_STEP = 2,
  COMMAND_READBACK = 3,
};

enum ResidentStatus : std::uint8_t {
  STATUS_OK = 0,
  STATUS_INVALID_COMMAND = 1,
  STATUS_INVALID_SEQUENCE_ID = 2,
  STATUS_INVALID_LAYER_ID = 3,
  STATUS_UNINITIALIZED_STATE = 4,
  STATUS_MISSING_PAYLOAD = 5,
  STATUS_UNEXPECTED_PAYLOAD = 6,
  STATUS_INVALID_ENCODING = 7,
  STATUS_SHAPE_MISMATCH = 8,
};

enum PayloadFlag : std::uint8_t {
  PAYLOAD_NONE = 0,
  PAYLOAD_STATE = 1,
  PAYLOAD_TOKEN = 2,
};

enum CounterIndex : int {
  COUNTER_ELEMENT_SATURATIONS = 0,
  COUNTER_ACCUMULATOR_SATURATIONS = 1,
  COUNTER_SCALE_CLAMPS = 2,
  COUNTER_ALIGNMENT_UNDERFLOWS = 3,
  COUNTER_STATE_SCALE_CHANGES = 4,
  COUNTER_INVALID_ENCODINGS = 5,
  COUNTER_REJECTED_COMMANDS = 6,
  COUNTER_COMMITTED_STATE_GENERATIONS = 7,
  COUNTER_COUNT = 8,
};

static_assert(NUM_SEQUENCES > 0, "at least one sequence slot is required");
static_assert(NUM_VALUE_HEADS % NUM_QK_HEADS == 0,
              "value heads must be divisible by Q/K heads");
static_assert(KEY_DIM % BLOCK_SIZE == 0,
              "KEY_DIM must be divisible by BLOCK_SIZE");
static_assert(VALUE_DIM % BLOCK_SIZE == 0,
              "VALUE_DIM must be divisible by BLOCK_SIZE");
static_assert(KEY_DIM % P_K == 0, "KEY_DIM must be divisible by P_K");
static_assert(VALUE_DIM % P_V == 0, "VALUE_DIM must be divisible by P_V");
static_assert(BLOCK_SIZE == 16 || BLOCK_SIZE == 32,
              "MXFP4 block size must be 16 or 32");
static_assert(P_K == 8 || P_K == 16 || P_K == 32,
              "P_K must match a controlled sweep point");
static_assert(P_V == 4 || P_V == 8 || P_V == 16,
              "P_V must match a controlled sweep point");
static_assert(MAX_COMMAND_EVENT_BOUND < (1ull << 24),
              "per-command diagnostic counters must fit in 24 bits");

}  // namespace gdn

#include "Vrs2_fast_wrapper.h"
#include "Vrs2_fast_wrapper___024root.h"
#include "verilated.h"

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#define ROOT_SIGNAL(name) root->rs2_fast_wrapper__DOT__##name
#define ROOT_MEM(index) root->rs2_fast_wrapper__DOT__mem##index##__DOT__mem

#ifndef RS2_MODEL_THREADS
#define RS2_MODEL_THREADS 1
#endif

namespace {

constexpr int kTraceTokens = 64;
constexpr int kQElements = 2 * 16 * 128;
constexpr int kQScales = 2 * 16 * 4;
constexpr int kVElements = 2 * 32 * 128;
constexpr int kVScales = 2 * 32 * 4;
constexpr int kHeads = 32;
constexpr int kOutputElements = 32 * 128;
constexpr int kCounters = 7;
constexpr int kStateElements = 32 * 128 * 128;
constexpr int kStateScales = 32 * 128 * 4;
constexpr int kLogKeyElements = 3 * 2 * 16 * 128;
constexpr int kLogKeyScales = 3 * 2 * 16 * 4;
constexpr int kLogUpdateElements = 3 * 2 * 32 * 128;
constexpr int kLogUpdateScales = 3 * 2 * 32 * 4;
constexpr int kLambdaElements = 3 * 32;

std::vector<std::uint64_t> read_hex(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open asset: " + path);
    std::vector<std::uint64_t> values;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        values.push_back(std::stoull(line, nullptr, 16));
    }
    return values;
}

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

template <typename Memory>
std::uint16_t bytes_u16(const Memory& memory, std::size_t address) {
    return static_cast<std::uint16_t>(memory[address]) |
           (static_cast<std::uint16_t>(memory[address + 1]) << 8);
}

template <typename Memory>
std::uint32_t bytes_u32(const Memory& memory, std::size_t address) {
    std::uint32_t value = 0;
    for (int byte = 0; byte < 4; ++byte)
        value |= static_cast<std::uint32_t>(memory[address + byte]) << (8 * byte);
    return value;
}

template <typename Memory>
std::uint64_t bytes_u64(const Memory& memory, std::size_t address) {
    std::uint64_t value = 0;
    for (int byte = 0; byte < 8; ++byte)
        value |= static_cast<std::uint64_t>(memory[address + byte]) << (8 * byte);
    return value;
}

class Harness {
  public:
    explicit Harness(std::string asset_root)
        : context(),
          top(configure_context(context)),
          root(top.rootp),
          assets(std::move(asset_root)) {
        initialize_inputs();
        load_assets();
    }

    void run(int token_limit) {
        require(token_limit >= 0 && token_limit <= kTraceTokens,
                "TOKEN_LIMIT must be in [0,64]");
        load_initial_snapshot();
        for (int cycle = 0; cycle < 10; ++cycle) tick();
        ROOT_SIGNAL(ap_rst_n) = 1;
        for (int cycle = 0; cycle < 10; ++cycle) tick();
        configure_pointers();

        run_command(1, 4, 1);
        require(ROOT_MEM(15)[8] == 0 && bytes_u64(ROOT_MEM(15), 16) == 1 &&
                    ROOT_MEM(15)[0] == initial_live.at(0),
                "initial LOAD metadata mismatch");
        ROOT_SIGNAL(live_entries_in) = 0;

        for (int token = 0; token < token_limit; ++token) {
            load_token(token);
            run_command(2, 4, 2);
            check_token(token);
        }
        if (token_limit != kTraceTokens) {
            std::cout << "RS2_DIRECT_RTL_BENCHMARK PASS tokens=" << token_limit
                      << std::endl;
            return;
        }
        run_command(3, 4, 0);
        check_final_snapshot();
        std::cout << "RS2_DIRECT_RTL_TRACE64 PASS tokens=64 transactions=66 "
                     "outputs=262144 final_snapshot=PASS"
                  << std::endl;
    }

  private:
    static VerilatedContext* configure_context(VerilatedContext& context) {
        context.threads(RS2_MODEL_THREADS);
        return &context;
    }

    VerilatedContext context;
    Vrs2_fast_wrapper top;
    Vrs2_fast_wrapper___024root* root;
    std::string assets;
    std::uint64_t cycles = 0;
    std::vector<std::uint64_t> initial_primary, initial_primary_scales;
    std::vector<std::uint64_t> initial_residual, initial_residual_scales;
    std::vector<std::uint64_t> initial_log_keys, initial_log_key_scales;
    std::vector<std::uint64_t> initial_log_updates, initial_log_update_scales;
    std::vector<std::uint64_t> initial_gamma, initial_lambda, initial_live;
    std::vector<std::uint64_t> q, q_scales, k, k_scales, v, v_scales;
    std::vector<std::uint64_t> alpha, beta, status, generation, live;
    std::vector<std::uint64_t> command_counters, cumulative_counters;
    std::vector<std::uint64_t> output_mantissas, output_exponents;
    std::vector<std::uint64_t> final_primary, final_primary_scales;
    std::vector<std::uint64_t> final_residual, final_residual_scales;
    std::vector<std::uint64_t> final_log_keys, final_log_key_scales;
    std::vector<std::uint64_t> final_log_updates, final_log_update_scales;
    std::vector<std::uint64_t> final_gamma, final_lambda, final_live;
    std::vector<std::uint64_t> final_status, final_generation;
    std::vector<std::uint64_t> final_cumulative_counters;

    std::string path(const char* name) const { return assets + "/" + name; }

    void initialize_inputs() {
        ROOT_SIGNAL(ap_clk) = 0;
        ROOT_SIGNAL(ap_rst_n) = 0;
        ROOT_SIGNAL(live_entries_in) = 0;
        ROOT_SIGNAL(s_axi_control_AWVALID) = 0;
        ROOT_SIGNAL(s_axi_control_AWADDR) = 0;
        ROOT_SIGNAL(s_axi_control_WVALID) = 0;
        ROOT_SIGNAL(s_axi_control_WDATA) = 0;
        ROOT_SIGNAL(s_axi_control_WSTRB) = 0;
        ROOT_SIGNAL(s_axi_control_ARVALID) = 0;
        ROOT_SIGNAL(s_axi_control_ARADDR) = 0;
        ROOT_SIGNAL(s_axi_control_RREADY) = 0;
        ROOT_SIGNAL(s_axi_control_BREADY) = 0;
        ROOT_SIGNAL(s_axi_control_r_AWVALID) = 0;
        ROOT_SIGNAL(s_axi_control_r_AWADDR) = 0;
        ROOT_SIGNAL(s_axi_control_r_WVALID) = 0;
        ROOT_SIGNAL(s_axi_control_r_WDATA) = 0;
        ROOT_SIGNAL(s_axi_control_r_WSTRB) = 0;
        ROOT_SIGNAL(s_axi_control_r_ARVALID) = 0;
        ROOT_SIGNAL(s_axi_control_r_ARADDR) = 0;
        ROOT_SIGNAL(s_axi_control_r_RREADY) = 0;
        ROOT_SIGNAL(s_axi_control_r_BREADY) = 0;
        top.eval();
    }

    void tick() {
        ROOT_SIGNAL(ap_clk) = 1;
        top.eval();
        ROOT_SIGNAL(ap_clk) = 0;
        top.eval();
        ++cycles;
    }

    void load_assets() {
#define LOAD(name) name = read_hex(path(#name ".hex"))
        LOAD(initial_primary); LOAD(initial_primary_scales);
        LOAD(initial_residual); LOAD(initial_residual_scales);
        LOAD(initial_log_keys); LOAD(initial_log_key_scales);
        LOAD(initial_log_updates); LOAD(initial_log_update_scales);
        LOAD(initial_gamma); LOAD(initial_lambda); LOAD(initial_live);
        LOAD(q); LOAD(q_scales); LOAD(k); LOAD(k_scales); LOAD(v); LOAD(v_scales);
        LOAD(alpha); LOAD(beta); LOAD(status); LOAD(generation); LOAD(live);
        LOAD(command_counters); LOAD(cumulative_counters);
        LOAD(output_mantissas); LOAD(output_exponents);
        LOAD(final_primary); LOAD(final_primary_scales);
        LOAD(final_residual); LOAD(final_residual_scales);
        LOAD(final_log_keys); LOAD(final_log_key_scales);
        LOAD(final_log_updates); LOAD(final_log_update_scales);
        LOAD(final_gamma); LOAD(final_lambda); LOAD(final_live);
        LOAD(final_status); LOAD(final_generation); LOAD(final_cumulative_counters);
#undef LOAD
    }

    void load_initial_snapshot() {
        for (int item = 0; item < kStateElements; ++item) {
            ROOT_MEM(4)[item] = initial_primary.at(item);
            ROOT_MEM(5)[item] = initial_residual.at(item);
        }
        for (int item = 0; item < kStateScales; ++item) {
            ROOT_MEM(4)[0x80000 + item] = initial_primary_scales.at(item);
            ROOT_MEM(5)[0x80000 + item] = initial_residual_scales.at(item);
        }
        for (int item = 0; item < kLogKeyElements; ++item)
            ROOT_MEM(6)[item] = initial_log_keys.at(item);
        for (int item = 0; item < kLogKeyScales; ++item)
            ROOT_MEM(6)[0x8000 + item] = initial_log_key_scales.at(item);
        for (int item = 0; item < kLogUpdateElements; ++item)
            ROOT_MEM(7)[item] = initial_log_updates.at(item);
        for (int item = 0; item < kLogUpdateScales; ++item)
            ROOT_MEM(7)[0x10000 + item] = initial_log_update_scales.at(item);
        for (int item = 0; item < kHeads; ++item) {
            ROOT_MEM(8)[2 * item] = initial_gamma.at(item) & 0xff;
            ROOT_MEM(8)[2 * item + 1] = initial_gamma.at(item) >> 8;
        }
        for (int item = 0; item < kLambdaElements; ++item) {
            ROOT_MEM(8)[0x100 + 2 * item] = initial_lambda.at(item) & 0xff;
            ROOT_MEM(8)[0x100 + 2 * item + 1] = initial_lambda.at(item) >> 8;
        }
        ROOT_SIGNAL(live_entries_in) = initial_live.at(0) & 0xf;
    }

    void load_token(int token) {
        for (int item = 0; item < kQElements; ++item) {
            ROOT_MEM(0)[item] = q.at(token * kQElements + item);
            ROOT_MEM(1)[item] = k.at(token * kQElements + item);
        }
        for (int item = 0; item < kQScales; ++item) {
            ROOT_MEM(16)[item] = q_scales.at(token * kQScales + item);
            ROOT_MEM(17)[item] = k_scales.at(token * kQScales + item);
        }
        for (int item = 0; item < kVElements; ++item)
            ROOT_MEM(2)[item] = v.at(token * kVElements + item);
        for (int item = 0; item < kVScales; ++item)
            ROOT_MEM(18)[item] = v_scales.at(token * kVScales + item);
        for (int item = 0; item < kHeads; ++item) {
            const auto a = alpha.at(token * kHeads + item);
            const auto b = beta.at(token * kHeads + item);
            ROOT_MEM(3)[2 * item] = a & 0xff;
            ROOT_MEM(3)[2 * item + 1] = a >> 8;
            ROOT_MEM(3)[0x100 + 2 * item] = b & 0xff;
            ROOT_MEM(3)[0x100 + 2 * item + 1] = b >> 8;
        }
    }

    void check_token(int token) {
        require(ROOT_MEM(15)[8] == status.at(token) &&
                    bytes_u64(ROOT_MEM(15), 16) == generation.at(token) &&
                    ROOT_MEM(15)[0] == live.at(token),
                "token metadata mismatch token=" + std::to_string(token + 1));
        for (int counter = 0; counter < kCounters; ++counter) {
            require(bytes_u64(ROOT_MEM(15), 32 + 8 * counter) ==
                        command_counters.at(token * kCounters + counter),
                    "command counter mismatch");
            require(bytes_u64(ROOT_MEM(15), 96 + 8 * counter) ==
                        cumulative_counters.at(token * kCounters + counter),
                    "cumulative counter mismatch");
        }
        for (int item = 0; item < kOutputElements; ++item) {
            require(bytes_u32(ROOT_MEM(9), 4 * item) ==
                        output_mantissas.at(token * kOutputElements + item),
                    "output mantissa mismatch token=" + std::to_string(token + 1));
            require(bytes_u16(ROOT_MEM(19), 2 * item) ==
                        output_exponents.at(token * kOutputElements + item),
                    "output exponent mismatch token=" + std::to_string(token + 1));
        }
        std::cout << "RS2_DIRECT_RTL_TOKEN token=" << token + 1
                  << " status=" << static_cast<int>(ROOT_MEM(15)[8])
                  << " generation=" << bytes_u64(ROOT_MEM(15), 16)
                  << " live=" << static_cast<int>(ROOT_MEM(15)[0]) << " PASS"
                  << std::endl;
    }

    void check_final_snapshot() {
        require(ROOT_MEM(15)[0] == final_live.at(0) &&
                    ROOT_MEM(15)[8] == final_status.at(0) &&
                    bytes_u64(ROOT_MEM(15), 16) == final_generation.at(0),
                "final readback metadata mismatch");
        for (int counter = 0; counter < kCounters; ++counter)
            require(bytes_u64(ROOT_MEM(15), 96 + 8 * counter) ==
                        final_cumulative_counters.at(counter),
                    "final cumulative counter mismatch");
        for (int item = 0; item < kStateElements; ++item) {
            require(ROOT_MEM(10)[item] == final_primary.at(item),
                    "final primary mismatch");
            require(ROOT_MEM(11)[item] == final_residual.at(item),
                    "final residual mismatch");
        }
        for (int item = 0; item < kStateScales; ++item) {
            require(ROOT_MEM(10)[0x80000 + item] == final_primary_scales.at(item),
                    "final primary scale mismatch");
            require(ROOT_MEM(11)[0x80000 + item] == final_residual_scales.at(item),
                    "final residual scale mismatch");
        }
        for (int item = 0; item < kLogKeyElements; ++item)
            require(ROOT_MEM(12)[item] == final_log_keys.at(item), "final key log mismatch");
        for (int item = 0; item < kLogKeyScales; ++item)
            require(ROOT_MEM(12)[0x8000 + item] == final_log_key_scales.at(item),
                    "final key-log scale mismatch");
        for (int item = 0; item < kLogUpdateElements; ++item)
            require(ROOT_MEM(13)[item] == final_log_updates.at(item),
                    "final update log mismatch");
        for (int item = 0; item < kLogUpdateScales; ++item)
            require(ROOT_MEM(13)[0x10000 + item] == final_log_update_scales.at(item),
                    "final update-log scale mismatch");
        for (int item = 0; item < kHeads; ++item)
            require(bytes_u16(ROOT_MEM(14), 2 * item) == final_gamma.at(item),
                    "final gamma mismatch");
        for (int item = 0; item < kLambdaElements; ++item)
            require(bytes_u16(ROOT_MEM(14), 0x100 + 2 * item) == final_lambda.at(item),
                    "final lambda mismatch");
    }

    void control_write(std::uint32_t address, std::uint32_t data) {
        ROOT_SIGNAL(s_axi_control_AWADDR) = address;
        ROOT_SIGNAL(s_axi_control_AWVALID) = 1;
        top.eval();
        while (!ROOT_SIGNAL(s_axi_control_AWREADY)) tick();
        tick();
        ROOT_SIGNAL(s_axi_control_AWVALID) = 0;
        ROOT_SIGNAL(s_axi_control_WDATA) = data;
        ROOT_SIGNAL(s_axi_control_WSTRB) = 0xf;
        ROOT_SIGNAL(s_axi_control_WVALID) = 1;
        top.eval();
        while (!ROOT_SIGNAL(s_axi_control_WREADY)) tick();
        tick();
        ROOT_SIGNAL(s_axi_control_WVALID) = 0;
        ROOT_SIGNAL(s_axi_control_BREADY) = 1;
        top.eval();
        while (!ROOT_SIGNAL(s_axi_control_BVALID)) tick();
        tick();
        ROOT_SIGNAL(s_axi_control_BREADY) = 0;
        top.eval();
    }

    void pointer_write(std::uint32_t address, std::uint32_t data) {
        ROOT_SIGNAL(s_axi_control_r_AWADDR) = address;
        ROOT_SIGNAL(s_axi_control_r_AWVALID) = 1;
        top.eval();
        while (!ROOT_SIGNAL(s_axi_control_r_AWREADY)) tick();
        tick();
        ROOT_SIGNAL(s_axi_control_r_AWVALID) = 0;
        ROOT_SIGNAL(s_axi_control_r_WDATA) = data;
        ROOT_SIGNAL(s_axi_control_r_WSTRB) = 0xf;
        ROOT_SIGNAL(s_axi_control_r_WVALID) = 1;
        top.eval();
        while (!ROOT_SIGNAL(s_axi_control_r_WREADY)) tick();
        tick();
        ROOT_SIGNAL(s_axi_control_r_WVALID) = 0;
        ROOT_SIGNAL(s_axi_control_r_BREADY) = 1;
        top.eval();
        while (!ROOT_SIGNAL(s_axi_control_r_BVALID)) tick();
        tick();
        ROOT_SIGNAL(s_axi_control_r_BREADY) = 0;
        top.eval();
    }

    void set_pointer(std::uint32_t address, std::uint64_t value) {
        pointer_write(address, value & 0xffffffffu);
        pointer_write(address + 4, value >> 32);
    }

    void configure_pointers() {
        const std::uint32_t addresses[] = {
            0x010, 0x01c, 0x028, 0x034, 0x040, 0x04c, 0x058, 0x064,
            0x070, 0x07c, 0x088, 0x094, 0x0a0, 0x0ac, 0x0b8, 0x0c4,
            0x0d0, 0x0dc, 0x0e8, 0x0f4, 0x100, 0x10c, 0x118, 0x124,
            0x130, 0x13c, 0x148, 0x154, 0x160, 0x16c, 0x178, 0x184,
            0x190, 0x19c, 0x1a8};
        const std::uint64_t values[] = {
            0, 0, 0, 0, 0, 0, 0, 0x100, 0, 0x80000, 0, 0x80000,
            0, 0x8000, 0, 0x10000, 0, 0x100, 0, 0, 0, 0x80000, 0,
            0x80000, 0, 0x8000, 0, 0x10000, 0, 0x100, 0, 0x8, 0x10,
            0x20, 0x60};
        for (std::size_t index = 0; index < sizeof(addresses) / sizeof(addresses[0]); ++index)
            set_pointer(addresses[index], values[index]);
    }

    void run_command(std::uint32_t command, std::uint32_t layer,
                     std::uint32_t flags) {
        while (!(ROOT_SIGNAL(fast_ap_idle) && !ROOT_SIGNAL(fast_ap_start))) tick();
        control_write(0x10, command);
        control_write(0x18, 0);
        control_write(0x20, layer);
        control_write(0x28, flags);
        const auto start = cycles;
        control_write(0x00, 1);
        int launch = 0;
        while (ROOT_SIGNAL(fast_ap_idle) && launch < 200) {
            tick();
            ++launch;
        }
        require(!ROOT_SIGNAL(fast_ap_idle), "command did not leave idle state");
        int completion = 0;
        while (!ROOT_SIGNAL(fast_ap_done) && completion < 200000000) {
            tick();
            ++completion;
        }
        require(ROOT_SIGNAL(fast_ap_done), "command exceeded 200,000,000 RTL cycles");
        tick();
        // Match the SystemVerilog cycle_count sampled after the completion edge.
        const auto reported_cycles = cycles - start + 1;
        std::cout << "RS2_DIRECT_RTL command=" << command
                  << " cycles=" << reported_cycles
                  << " status=" << static_cast<int>(ROOT_MEM(15)[8])
                  << " generation=" << bytes_u64(ROOT_MEM(15), 16) << std::endl;
        while (!(ROOT_SIGNAL(fast_ap_idle) && !ROOT_SIGNAL(fast_ap_start))) tick();
    }
};

}  // namespace

int main(int argc, char** argv) {
    try {
        Verilated::commandArgs(argc, argv);
        if (argc < 2) throw std::runtime_error("usage: fast_harness ASSET_DIR [TOKEN_LIMIT]");
        const int token_limit = argc >= 3 ? std::atoi(argv[2]) : kTraceTokens;
        Harness harness(argv[1]);
        harness.run(token_limit);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "RS2_FAST_RTL_FAIL " << error.what() << std::endl;
        return 1;
    }
}

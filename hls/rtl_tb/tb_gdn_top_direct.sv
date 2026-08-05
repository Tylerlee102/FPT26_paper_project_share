`timescale 1ns / 1ps

`define DECL_AXI(N, DW) \
    wire m_axi_gmem``N``_AWVALID; \
    wire m_axi_gmem``N``_AWREADY; \
    wire [63:0] m_axi_gmem``N``_AWADDR; \
    wire [0:0] m_axi_gmem``N``_AWID; \
    wire [7:0] m_axi_gmem``N``_AWLEN; \
    wire [2:0] m_axi_gmem``N``_AWSIZE; \
    wire [1:0] m_axi_gmem``N``_AWBURST; \
    wire [1:0] m_axi_gmem``N``_AWLOCK; \
    wire [3:0] m_axi_gmem``N``_AWCACHE; \
    wire [2:0] m_axi_gmem``N``_AWPROT; \
    wire [3:0] m_axi_gmem``N``_AWQOS; \
    wire [3:0] m_axi_gmem``N``_AWREGION; \
    wire [0:0] m_axi_gmem``N``_AWUSER; \
    wire m_axi_gmem``N``_WVALID; \
    wire m_axi_gmem``N``_WREADY; \
    wire [DW-1:0] m_axi_gmem``N``_WDATA; \
    wire [DW/8-1:0] m_axi_gmem``N``_WSTRB; \
    wire m_axi_gmem``N``_WLAST; \
    wire [0:0] m_axi_gmem``N``_WID; \
    wire [0:0] m_axi_gmem``N``_WUSER; \
    wire m_axi_gmem``N``_ARVALID; \
    wire m_axi_gmem``N``_ARREADY; \
    wire [63:0] m_axi_gmem``N``_ARADDR; \
    wire [0:0] m_axi_gmem``N``_ARID; \
    wire [7:0] m_axi_gmem``N``_ARLEN; \
    wire [2:0] m_axi_gmem``N``_ARSIZE; \
    wire [1:0] m_axi_gmem``N``_ARBURST; \
    wire [1:0] m_axi_gmem``N``_ARLOCK; \
    wire [3:0] m_axi_gmem``N``_ARCACHE; \
    wire [2:0] m_axi_gmem``N``_ARPROT; \
    wire [3:0] m_axi_gmem``N``_ARQOS; \
    wire [3:0] m_axi_gmem``N``_ARREGION; \
    wire [0:0] m_axi_gmem``N``_ARUSER; \
    wire m_axi_gmem``N``_RVALID; \
    wire m_axi_gmem``N``_RREADY; \
    wire [DW-1:0] m_axi_gmem``N``_RDATA; \
    wire m_axi_gmem``N``_RLAST; \
    wire [0:0] m_axi_gmem``N``_RID; \
    wire [0:0] m_axi_gmem``N``_RUSER; \
    wire [1:0] m_axi_gmem``N``_RRESP; \
    wire m_axi_gmem``N``_BVALID; \
    wire m_axi_gmem``N``_BREADY; \
    wire [1:0] m_axi_gmem``N``_BRESP; \
    wire [0:0] m_axi_gmem``N``_BID; \
    wire [0:0] m_axi_gmem``N``_BUSER;

`define CONNECT_MEM(N, DW, BYTES) \
    axi_memory_model #(.DATA_WIDTH(DW), .MEM_BYTES(BYTES)) mem``N ( \
        .clk(ap_clk), .rst(!ap_rst_n), \
        .awvalid(m_axi_gmem``N``_AWVALID), .awready(m_axi_gmem``N``_AWREADY), \
        .awaddr(m_axi_gmem``N``_AWADDR), .awid(m_axi_gmem``N``_AWID), \
        .awlen(m_axi_gmem``N``_AWLEN), .awsize(m_axi_gmem``N``_AWSIZE), \
        .awburst(m_axi_gmem``N``_AWBURST), \
        .wvalid(m_axi_gmem``N``_WVALID), .wready(m_axi_gmem``N``_WREADY), \
        .wdata(m_axi_gmem``N``_WDATA), .wstrb(m_axi_gmem``N``_WSTRB), \
        .wlast(m_axi_gmem``N``_WLAST), \
        .bvalid(m_axi_gmem``N``_BVALID), .bready(m_axi_gmem``N``_BREADY), \
        .bresp(m_axi_gmem``N``_BRESP), .bid(m_axi_gmem``N``_BID), \
        .buser(m_axi_gmem``N``_BUSER), \
        .arvalid(m_axi_gmem``N``_ARVALID), .arready(m_axi_gmem``N``_ARREADY), \
        .araddr(m_axi_gmem``N``_ARADDR), .arid(m_axi_gmem``N``_ARID), \
        .arlen(m_axi_gmem``N``_ARLEN), .arsize(m_axi_gmem``N``_ARSIZE), \
        .arburst(m_axi_gmem``N``_ARBURST), \
        .rvalid(m_axi_gmem``N``_RVALID), .rready(m_axi_gmem``N``_RREADY), \
        .rdata(m_axi_gmem``N``_RDATA), .rlast(m_axi_gmem``N``_RLAST), \
        .rid(m_axi_gmem``N``_RID), .ruser(m_axi_gmem``N``_RUSER), \
        .rresp(m_axi_gmem``N``_RRESP));

module tb_gdn_top_direct;
    reg ap_clk = 1'b0;
    reg ap_rst_n = 1'b0;
    wire interrupt;
    always #2 ap_clk = ~ap_clk;

    `DECL_AXI(0, 32)
    `DECL_AXI(1, 32)
    `DECL_AXI(2, 32)
    `DECL_AXI(3, 32)
    `DECL_AXI(4, 32)
    `DECL_AXI(5, 32)
    `DECL_AXI(6, 32)
    `DECL_AXI(7, 64)

    reg s_axi_control_AWVALID = 1'b0;
    wire s_axi_control_AWREADY;
    reg [5:0] s_axi_control_AWADDR = 6'd0;
    reg s_axi_control_WVALID = 1'b0;
    wire s_axi_control_WREADY;
    reg [31:0] s_axi_control_WDATA = 32'd0;
    reg [3:0] s_axi_control_WSTRB = 4'd0;
    reg s_axi_control_ARVALID = 1'b0;
    wire s_axi_control_ARREADY;
    reg [5:0] s_axi_control_ARADDR = 6'd0;
    wire s_axi_control_RVALID;
    reg s_axi_control_RREADY = 1'b0;
    wire [31:0] s_axi_control_RDATA;
    wire [1:0] s_axi_control_RRESP;
    wire s_axi_control_BVALID;
    reg s_axi_control_BREADY = 1'b0;
    wire [1:0] s_axi_control_BRESP;

    reg s_axi_control_r_AWVALID = 1'b0;
    wire s_axi_control_r_AWREADY;
    reg [7:0] s_axi_control_r_AWADDR = 8'd0;
    reg s_axi_control_r_WVALID = 1'b0;
    wire s_axi_control_r_WREADY;
    reg [31:0] s_axi_control_r_WDATA = 32'd0;
    reg [3:0] s_axi_control_r_WSTRB = 4'd0;
    reg s_axi_control_r_ARVALID = 1'b0;
    wire s_axi_control_r_ARREADY;
    reg [7:0] s_axi_control_r_ARADDR = 8'd0;
    wire s_axi_control_r_RVALID;
    reg s_axi_control_r_RREADY = 1'b0;
    wire [31:0] s_axi_control_r_RDATA;
    wire [1:0] s_axi_control_r_RRESP;
    wire s_axi_control_r_BVALID;
    reg s_axi_control_r_BREADY = 1'b0;
    wire [1:0] s_axi_control_r_BRESP;

    `CONNECT_MEM(0, 32, 4096)
    `CONNECT_MEM(1, 32, 4096)
    `CONNECT_MEM(2, 32, 8192)
    `CONNECT_MEM(3, 32, 256)
    `CONNECT_MEM(4, 32, 600000)
    `CONNECT_MEM(5, 32, 32768)
    `CONNECT_MEM(6, 32, 600000)
    `CONNECT_MEM(7, 64, 512)

    gdn_top dut (.*);

    longint unsigned cycle_count = 0;
    integer index;
    integer head;
    longint unsigned command_start;

`ifdef GDN_TRACE64
    localparam integer TRACE_TOKENS = 64;
    localparam integer TRACE_Q_ELEMENTS = 16 * 128;
    localparam integer TRACE_Q_SCALES = 16 * 4;
    localparam integer TRACE_V_ELEMENTS = 32 * 128;
    localparam integer TRACE_V_SCALES = 32 * 4;
    localparam integer TRACE_GATE_BYTES = 32 * 2;
    localparam integer TRACE_OUTPUT_ELEMENTS = 32 * 128;
    localparam integer TRACE_COUNTERS = 8;
    localparam integer TRACE_STATE_ELEMENTS = 32 * 128 * 128;
    localparam integer TRACE_STATE_SCALES = 32 * 128 * 4;

    reg [7:0] trace_q [0:TRACE_TOKENS * TRACE_Q_ELEMENTS - 1];
    reg [7:0] trace_q_scales [0:TRACE_TOKENS * TRACE_Q_SCALES - 1];
    reg [7:0] trace_k [0:TRACE_TOKENS * TRACE_Q_ELEMENTS - 1];
    reg [7:0] trace_k_scales [0:TRACE_TOKENS * TRACE_Q_SCALES - 1];
    reg [7:0] trace_v [0:TRACE_TOKENS * TRACE_V_ELEMENTS - 1];
    reg [7:0] trace_v_scales [0:TRACE_TOKENS * TRACE_V_SCALES - 1];
    reg [7:0] trace_alpha [0:TRACE_TOKENS * TRACE_GATE_BYTES - 1];
    reg [7:0] trace_beta [0:TRACE_TOKENS * TRACE_GATE_BYTES - 1];
    reg [7:0] trace_status [0:TRACE_TOKENS - 1];
    reg [63:0] trace_generation [0:TRACE_TOKENS - 1];
    reg [63:0] trace_command_counters [0:TRACE_TOKENS * TRACE_COUNTERS - 1];
    reg [63:0] trace_cumulative_counters [0:TRACE_TOKENS * TRACE_COUNTERS - 1];
    reg [31:0] trace_output_mantissas [0:TRACE_TOKENS * TRACE_OUTPUT_ELEMENTS - 1];
    reg [15:0] trace_output_exponents [0:TRACE_TOKENS * TRACE_OUTPUT_ELEMENTS - 1];
    reg [7:0] trace_final_state [0:TRACE_STATE_ELEMENTS - 1];
    reg [7:0] trace_final_scales [0:TRACE_STATE_SCALES - 1];
    reg [63:0] trace_readback_counters [0:TRACE_COUNTERS - 1];
`endif

    always @(posedge ap_clk)
        cycle_count <= cycle_count + 1;

    task automatic control_write(input [5:0] address, input [31:0] data);
        begin
            @(negedge ap_clk);
            s_axi_control_AWADDR = address;
            s_axi_control_AWVALID = 1'b1;
            while (!s_axi_control_AWREADY)
                @(negedge ap_clk);
            @(negedge ap_clk);
            s_axi_control_AWVALID = 1'b0;
            s_axi_control_WDATA = data;
            s_axi_control_WSTRB = 4'hf;
            s_axi_control_WVALID = 1'b1;
            while (!s_axi_control_WREADY)
                @(negedge ap_clk);
            @(negedge ap_clk);
            s_axi_control_WVALID = 1'b0;
            s_axi_control_BREADY = 1'b1;
            while (!s_axi_control_BVALID)
                @(negedge ap_clk);
            @(negedge ap_clk);
            s_axi_control_BREADY = 1'b0;
        end
    endtask

    task automatic pointer_write(input [7:0] address, input [31:0] data);
        begin
            @(negedge ap_clk);
            s_axi_control_r_AWADDR = address;
            s_axi_control_r_AWVALID = 1'b1;
            while (!s_axi_control_r_AWREADY)
                @(negedge ap_clk);
            @(negedge ap_clk);
            s_axi_control_r_AWVALID = 1'b0;
            s_axi_control_r_WDATA = data;
            s_axi_control_r_WSTRB = 4'hf;
            s_axi_control_r_WVALID = 1'b1;
            while (!s_axi_control_r_WREADY)
                @(negedge ap_clk);
            @(negedge ap_clk);
            s_axi_control_r_WVALID = 1'b0;
            s_axi_control_r_BREADY = 1'b1;
            while (!s_axi_control_r_BVALID)
                @(negedge ap_clk);
            @(negedge ap_clk);
            s_axi_control_r_BREADY = 1'b0;
        end
    endtask

    task automatic set_pointer(input [7:0] address, input [63:0] value);
        begin
            pointer_write(address, value[31:0]);
            pointer_write(address + 8'h04, value[63:32]);
        end
    endtask

    task automatic run_command(
        input [7:0] command,
        input [7:0] layer,
        input [7:0] flags);
        integer launch_cycles;
        integer completion_cycles;
        begin
            wait (dut.ap_idle === 1'b1 && dut.ap_CS_fsm === 3'd1 &&
                  dut.ap_start === 1'b0);
            control_write(6'h10, command);
            control_write(6'h18, 32'd0);
            control_write(6'h20, layer);
            control_write(6'h28, flags);
            if (dut.control_s_axi_U.int_command !== command ||
                dut.control_s_axi_U.int_payload_flags !== flags)
                $fatal(1, "AXI-Lite command register mismatch");

            command_start = cycle_count;
            control_write(6'h00, 32'd1);

            launch_cycles = 0;
            while (dut.ap_CS_fsm !== 3'd4 && launch_cycles < 100) begin
                @(negedge ap_clk);
                launch_cycles = launch_cycles + 1;
            end
            if (dut.ap_CS_fsm !== 3'd4)
                $fatal(1, "command did not enter active FSM state");
            if (dut.command_read_reg_3145 !== command)
                $fatal(1, "launched command register mismatch");

            completion_cycles = 0;
            while (dut.ap_done !== 1'b1 && completion_cycles < 20000000) begin
                @(negedge ap_clk);
                completion_cycles = completion_cycles + 1;
            end
            if (dut.ap_done !== 1'b1)
                $fatal(1, "command exceeded 20,000,000 RTL cycles");
            $display(
                "DIRECT_RTL command=%0d latched=%0d cycles=%0d status=%0d generation=%0d",
                command,
                dut.command_read_reg_3145,
                cycle_count - command_start,
                mem7.mem[0],
                mem7_u64(8));
            @(negedge ap_clk);
            wait (dut.ap_idle === 1'b1 && dut.ap_start === 1'b0);
        end
    endtask

    function automatic signed [31:0] mem5_i32(input integer address);
        mem5_i32 = $signed(
            {mem5.mem[address + 3], mem5.mem[address + 2],
             mem5.mem[address + 1], mem5.mem[address]});
    endfunction

    function automatic signed [15:0] mem5_i16(input integer address);
        mem5_i16 = $signed({mem5.mem[address + 1], mem5.mem[address]});
    endfunction

    function automatic [63:0] mem7_u64(input integer address);
        mem7_u64 = {
            mem7.mem[address + 7], mem7.mem[address + 6],
            mem7.mem[address + 5], mem7.mem[address + 4],
            mem7.mem[address + 3], mem7.mem[address + 2],
            mem7.mem[address + 1], mem7.mem[address]};
    endfunction

`ifdef GDN_TRACE64
    task automatic load_trace_assets;
        begin
            $readmemh("../assets/q.hex", trace_q);
            $readmemh("../assets/q_scales.hex", trace_q_scales);
            $readmemh("../assets/k.hex", trace_k);
            $readmemh("../assets/k_scales.hex", trace_k_scales);
            $readmemh("../assets/v.hex", trace_v);
            $readmemh("../assets/v_scales.hex", trace_v_scales);
            $readmemh("../assets/alpha.hex", trace_alpha);
            $readmemh("../assets/beta.hex", trace_beta);
            $readmemh("../assets/status.hex", trace_status);
            $readmemh("../assets/generation.hex", trace_generation);
            $readmemh("../assets/command_counters.hex", trace_command_counters);
            $readmemh("../assets/cumulative_counters.hex", trace_cumulative_counters);
            $readmemh("../assets/output_mantissas.hex", trace_output_mantissas);
            $readmemh("../assets/output_exponents.hex", trace_output_exponents);
            $readmemh("../assets/final_state.hex", trace_final_state);
            $readmemh("../assets/final_scales.hex", trace_final_scales);
            $readmemh("../assets/readback_counters.hex", trace_readback_counters);
        end
    endtask

    task automatic load_trace_token(input integer token);
        integer item;
        begin
            for (item = 0; item < TRACE_Q_ELEMENTS; item = item + 1) begin
                mem0.mem[item] = trace_q[token * TRACE_Q_ELEMENTS + item];
                mem1.mem[item] = trace_k[token * TRACE_Q_ELEMENTS + item];
            end
            for (item = 0; item < TRACE_Q_SCALES; item = item + 1) begin
                mem0.mem[16'h0800 + item] =
                    trace_q_scales[token * TRACE_Q_SCALES + item];
                mem1.mem[16'h0800 + item] =
                    trace_k_scales[token * TRACE_Q_SCALES + item];
            end
            for (item = 0; item < TRACE_V_ELEMENTS; item = item + 1)
                mem2.mem[item] = trace_v[token * TRACE_V_ELEMENTS + item];
            for (item = 0; item < TRACE_V_SCALES; item = item + 1)
                mem2.mem[16'h1000 + item] =
                    trace_v_scales[token * TRACE_V_SCALES + item];
            for (item = 0; item < TRACE_GATE_BYTES; item = item + 1) begin
                mem3.mem[item] = trace_alpha[token * TRACE_GATE_BYTES + item];
                mem3.mem[16'h0040 + item] =
                    trace_beta[token * TRACE_GATE_BYTES + item];
            end
        end
    endtask

    task automatic check_trace_token(input integer token);
        integer item;
        integer counter;
        begin
            if (mem7.mem[0] !== trace_status[token] ||
                mem7_u64(8) !== trace_generation[token])
                $fatal(1, "trace token status or generation mismatch token=%0d", token + 1);
            for (counter = 0; counter < TRACE_COUNTERS; counter = counter + 1) begin
                if (mem7_u64(16'h0010 + 8 * counter) !==
                    trace_command_counters[token * TRACE_COUNTERS + counter])
                    $fatal(1, "trace command counter mismatch token=%0d counter=%0d",
                           token + 1, counter);
                if (mem7_u64(16'h0050 + 8 * counter) !==
                    trace_cumulative_counters[token * TRACE_COUNTERS + counter])
                    $fatal(1, "trace cumulative counter mismatch token=%0d counter=%0d",
                           token + 1, counter);
            end
            for (item = 0; item < TRACE_OUTPUT_ELEMENTS; item = item + 1) begin
                if ($unsigned(mem5_i32(4 * item)) !==
                    trace_output_mantissas[token * TRACE_OUTPUT_ELEMENTS + item])
                    $fatal(1, "trace output mantissa mismatch token=%0d item=%0d",
                           token + 1, item);
                if ($unsigned(mem5_i16(16'h4000 + 2 * item)) !==
                    trace_output_exponents[token * TRACE_OUTPUT_ELEMENTS + item])
                    $fatal(1, "trace output exponent mismatch token=%0d item=%0d",
                           token + 1, item);
            end
            $display("DIRECT_RTL_TRACE token=%0d status=%0d generation=%0d PASS",
                     token + 1, mem7.mem[0], mem7_u64(8));
        end
    endtask

    task automatic run_trace64;
        integer token;
        integer item;
        integer counter;
        begin
            load_trace_assets();
            run_command(8'd0, 8'd3, 8'd0);
            if (mem7.mem[0] !== 8'd0 || mem7_u64(8) !== 64'd0)
                $fatal(1, "trace RESET status or generation mismatch");
            for (token = 0; token < TRACE_TOKENS; token = token + 1) begin
                load_trace_token(token);
                run_command(8'd2, 8'd3, 8'd2);
                check_trace_token(token);
            end
            run_command(8'd3, 8'd3, 8'd0);
            if (mem7.mem[0] !== 8'd0 || mem7_u64(8) !== 64'd64)
                $fatal(1, "trace READBACK status or generation mismatch");
            for (item = 0; item < TRACE_STATE_ELEMENTS; item = item + 1)
                if (mem6.mem[item] !== trace_final_state[item])
                    $fatal(1, "trace final state mismatch item=%0d", item);
            for (item = 0; item < TRACE_STATE_SCALES; item = item + 1)
                if (mem6.mem[32'h00080000 + item] !== trace_final_scales[item])
                    $fatal(1, "trace final scale mismatch item=%0d", item);
            for (counter = 0; counter < TRACE_COUNTERS; counter = counter + 1)
                if (mem7_u64(16'h0050 + 8 * counter) !==
                    trace_readback_counters[counter])
                    $fatal(1, "trace final counter mismatch counter=%0d", counter);
            $display("DIRECT_RTL_TRACE64 PASS tokens=64 outputs_per_token=4096 state_elements=524288");
        end
    endtask
`endif

    initial begin
`ifdef GDN_TRACE64
        #2000000000;
        $fatal(1, "direct RTL trace exceeded 2 s simulation time");
`else
        #100000000;
        $fatal(1, "direct RTL smoke exceeded 100 ms simulation time");
`endif
    end

    initial begin
        #1;
        for (head = 0; head < 16; head = head + 1) begin
            mem0.mem[head * 128] = 8'h02;
            mem1.mem[head * 128] = 8'h02;
        end
        for (index = 0; index < 64; index = index + 1) begin
            mem0.mem[16'h0800 + index] = 8'h7f;
            mem1.mem[16'h0800 + index] = 8'h7f;
        end
        for (index = 0; index < 4096; index = index + 1)
            mem2.mem[index] = 8'h02;
        for (index = 0; index < 128; index = index + 1)
            mem2.mem[16'h1000 + index] = 8'h7f;
        for (head = 0; head < 32; head = head + 1) begin
            mem3.mem[2 * head] = 8'h00;
            mem3.mem[2 * head + 1] = 8'h80;
            mem3.mem[16'h0040 + 2 * head] = 8'h00;
            mem3.mem[16'h0040 + 2 * head + 1] = 8'h80;
        end

        repeat (10) @(posedge ap_clk);
        ap_rst_n = 1'b1;
        repeat (10) @(posedge ap_clk);

        set_pointer(8'h10, 64'h00000000);
        set_pointer(8'h1c, 64'h00000800);
        set_pointer(8'h28, 64'h00000000);
        set_pointer(8'h34, 64'h00000800);
        set_pointer(8'h40, 64'h00000000);
        set_pointer(8'h4c, 64'h00001000);
        set_pointer(8'h58, 64'h00000000);
        set_pointer(8'h64, 64'h00000040);
        set_pointer(8'h70, 64'h00000000);
        set_pointer(8'h7c, 64'h00080000);
        set_pointer(8'h88, 64'h00000000);
        set_pointer(8'h94, 64'h00004000);
        set_pointer(8'ha0, 64'h00000000);
        set_pointer(8'hac, 64'h00080000);
        set_pointer(8'hb8, 64'h00000000);
        set_pointer(8'hc4, 64'h00000008);
        set_pointer(8'hd0, 64'h00000010);
        set_pointer(8'hdc, 64'h00000050);

`ifdef GDN_TRACE64
        run_trace64();
        $finish;
`else
        run_command(8'd0, 8'd0, 8'd0);
        if (mem7.mem[0] !== 8'd0 || mem7_u64(8) !== 64'd0)
            $fatal(1, "RESET status or generation mismatch");

        run_command(8'd2, 8'd0, 8'd2);
        if (mem7.mem[0] !== 8'd0 || mem7_u64(8) !== 64'd1)
            $fatal(1, "STEP status or generation mismatch");
        if (mem7_u64(16'h0048) !== 64'd1)
            $fatal(1, "STEP committed-generation counter mismatch");
        if (mem5_i32(0) !== 32'sd8 || mem5_i16(16'h4000) !== -16'sd3)
            $fatal(1, "STEP first output mismatch");
        if (mem5_i32(4 * 4095) !== 32'sd8 ||
            mem5_i16(16'h4000 + 2 * 4095) !== -16'sd3)
            $fatal(1, "STEP last output mismatch");

        run_command(8'd3, 8'd0, 8'd0);
        if (mem6.mem[0] !== 8'h06 || mem6.mem[127] !== 8'h06 ||
            mem6.mem[(31 * 128 * 128) + 127] !== 8'h06)
            $fatal(1, "READBACK updated-state mismatch");
        if (mem6.mem[128] !== 8'h00)
            $fatal(1, "READBACK untouched-state mismatch");
        if (mem6.mem[32'h00080000] !== 8'd125 ||
            mem6.mem[32'h00080000 + 4] !== 8'd127)
            $fatal(1, "READBACK state-scale mismatch");

        $display("DIRECT_RTL_SMOKE PASS reset_step_readback=3");
        $finish;
`endif
    end
endmodule

`undef CONNECT_MEM
`undef DECL_AXI

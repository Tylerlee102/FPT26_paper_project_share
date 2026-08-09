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

module tb_gdn_rs2_top_direct;
    localparam integer TRACE_TOKENS = 64;
    localparam integer Q_ELEMENTS = 2 * 16 * 128;
    localparam integer Q_SCALES = 2 * 16 * 4;
    localparam integer V_ELEMENTS = 2 * 32 * 128;
    localparam integer V_SCALES = 2 * 32 * 4;
    localparam integer HEADS = 32;
    localparam integer OUTPUT_ELEMENTS = 32 * 128;
    localparam integer COUNTERS = 7;
    localparam integer STATE_ELEMENTS = 32 * 128 * 128;
    localparam integer STATE_SCALES = 32 * 128 * 4;
    localparam integer LOG_KEY_ELEMENTS = 3 * 2 * 16 * 128;
    localparam integer LOG_KEY_SCALES = 3 * 2 * 16 * 4;
    localparam integer LOG_UPDATE_ELEMENTS = 3 * 2 * 32 * 128;
    localparam integer LOG_UPDATE_SCALES = 3 * 2 * 32 * 4;
    localparam integer LAMBDA_ELEMENTS = 3 * 32;

    reg ap_clk = 1'b0;
    reg ap_rst_n = 1'b0;
    reg [3:0] live_entries_in = 4'd0;
    wire interrupt;
    always #2 ap_clk = ~ap_clk;

    `DECL_AXI(0, 32)
    `DECL_AXI(1, 32)
    `DECL_AXI(2, 32)
    `DECL_AXI(3, 32)
    `DECL_AXI(4, 32)
    `DECL_AXI(5, 32)
    `DECL_AXI(6, 32)
    `DECL_AXI(7, 32)
    `DECL_AXI(8, 32)
    `DECL_AXI(9, 32)
    `DECL_AXI(10, 32)
    `DECL_AXI(11, 32)
    `DECL_AXI(12, 32)
    `DECL_AXI(13, 32)
    `DECL_AXI(14, 32)
    `DECL_AXI(15, 64)
    `DECL_AXI(16, 32)
    `DECL_AXI(17, 32)
    `DECL_AXI(18, 32)
    `DECL_AXI(19, 32)

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
    reg [8:0] s_axi_control_r_AWADDR = 9'd0;
    reg s_axi_control_r_WVALID = 1'b0;
    wire s_axi_control_r_WREADY;
    reg [31:0] s_axi_control_r_WDATA = 32'd0;
    reg [3:0] s_axi_control_r_WSTRB = 4'd0;
    reg s_axi_control_r_ARVALID = 1'b0;
    wire s_axi_control_r_ARREADY;
    reg [8:0] s_axi_control_r_ARADDR = 9'd0;
    wire s_axi_control_r_RVALID;
    reg s_axi_control_r_RREADY = 1'b0;
    wire [31:0] s_axi_control_r_RDATA;
    wire [1:0] s_axi_control_r_RRESP;
    wire s_axi_control_r_BVALID;
    reg s_axi_control_r_BREADY = 1'b0;
    wire [1:0] s_axi_control_r_BRESP;

    `CONNECT_MEM(0, 32, 4352)
    `CONNECT_MEM(1, 32, 4352)
    `CONNECT_MEM(2, 32, 8448)
    `CONNECT_MEM(3, 32, 320)
    `CONNECT_MEM(4, 32, 540672)
    `CONNECT_MEM(5, 32, 540672)
    `CONNECT_MEM(6, 32, 33664)
    `CONNECT_MEM(7, 32, 67328)
    `CONNECT_MEM(8, 32, 704)
    `CONNECT_MEM(9, 32, 16640)
    `CONNECT_MEM(10, 32, 540672)
    `CONNECT_MEM(11, 32, 540672)
    `CONNECT_MEM(12, 32, 33664)
    `CONNECT_MEM(13, 32, 67328)
    `CONNECT_MEM(14, 32, 704)
    `CONNECT_MEM(15, 64, 160)
    `CONNECT_MEM(16, 32, 256)
    `CONNECT_MEM(17, 32, 256)
    `CONNECT_MEM(18, 32, 512)
    `CONNECT_MEM(19, 32, 8448)

    gdn_rs2_top dut (.*);

    reg [7:0] initial_primary [0:STATE_ELEMENTS-1];
    reg [7:0] initial_primary_scales [0:STATE_SCALES-1];
    reg [7:0] initial_residual [0:STATE_ELEMENTS-1];
    reg [7:0] initial_residual_scales [0:STATE_SCALES-1];
    reg [7:0] initial_log_keys [0:LOG_KEY_ELEMENTS-1];
    reg [7:0] initial_log_key_scales [0:LOG_KEY_SCALES-1];
    reg [7:0] initial_log_updates [0:LOG_UPDATE_ELEMENTS-1];
    reg [7:0] initial_log_update_scales [0:LOG_UPDATE_SCALES-1];
    reg [15:0] initial_gamma [0:HEADS-1];
    reg [15:0] initial_lambda [0:LAMBDA_ELEMENTS-1];
    reg [7:0] initial_live [0:0];

    reg [7:0] trace_q [0:TRACE_TOKENS*Q_ELEMENTS-1];
    reg [7:0] trace_q_scales [0:TRACE_TOKENS*Q_SCALES-1];
    reg [7:0] trace_k [0:TRACE_TOKENS*Q_ELEMENTS-1];
    reg [7:0] trace_k_scales [0:TRACE_TOKENS*Q_SCALES-1];
    reg [7:0] trace_v [0:TRACE_TOKENS*V_ELEMENTS-1];
    reg [7:0] trace_v_scales [0:TRACE_TOKENS*V_SCALES-1];
    reg [15:0] trace_alpha [0:TRACE_TOKENS*HEADS-1];
    reg [15:0] trace_beta [0:TRACE_TOKENS*HEADS-1];
    reg [7:0] trace_status [0:TRACE_TOKENS-1];
    reg [63:0] trace_generation [0:TRACE_TOKENS-1];
    reg [7:0] trace_live [0:TRACE_TOKENS-1];
    reg [63:0] trace_command_counters [0:TRACE_TOKENS*COUNTERS-1];
    reg [63:0] trace_cumulative_counters [0:TRACE_TOKENS*COUNTERS-1];
    reg [31:0] trace_output_mantissas [0:TRACE_TOKENS*OUTPUT_ELEMENTS-1];
    reg [15:0] trace_output_exponents [0:TRACE_TOKENS*OUTPUT_ELEMENTS-1];

    reg [7:0] final_primary [0:STATE_ELEMENTS-1];
    reg [7:0] final_primary_scales [0:STATE_SCALES-1];
    reg [7:0] final_residual [0:STATE_ELEMENTS-1];
    reg [7:0] final_residual_scales [0:STATE_SCALES-1];
    reg [7:0] final_log_keys [0:LOG_KEY_ELEMENTS-1];
    reg [7:0] final_log_key_scales [0:LOG_KEY_SCALES-1];
    reg [7:0] final_log_updates [0:LOG_UPDATE_ELEMENTS-1];
    reg [7:0] final_log_update_scales [0:LOG_UPDATE_SCALES-1];
    reg [15:0] final_gamma [0:HEADS-1];
    reg [15:0] final_lambda [0:LAMBDA_ELEMENTS-1];
    reg [7:0] final_live [0:0];
    reg [7:0] final_status [0:0];
    reg [63:0] final_generation [0:0];
    reg [63:0] final_cumulative_counters [0:COUNTERS-1];

    longint unsigned cycle_count = 0;
    longint unsigned command_start;
    integer item;

    always @(posedge ap_clk)
        cycle_count <= cycle_count + 1;

    function automatic [31:0] mem9_u32(input integer address);
        mem9_u32 = {mem9.mem[address+3], mem9.mem[address+2],
                    mem9.mem[address+1], mem9.mem[address]};
    endfunction

    function automatic [15:0] mem19_u16(input integer address);
        mem19_u16 = {mem19.mem[address+1], mem19.mem[address]};
    endfunction

    function automatic [15:0] mem14_u16(input integer address);
        mem14_u16 = {mem14.mem[address+1], mem14.mem[address]};
    endfunction

    function automatic [63:0] mem15_u64(input integer address);
        mem15_u64 = {
            mem15.mem[address+7], mem15.mem[address+6],
            mem15.mem[address+5], mem15.mem[address+4],
            mem15.mem[address+3], mem15.mem[address+2],
            mem15.mem[address+1], mem15.mem[address]};
    endfunction

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

    task automatic pointer_write(input [8:0] address, input [31:0] data);
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

    task automatic set_pointer(input [8:0] address, input [63:0] value);
        begin
            pointer_write(address, value[31:0]);
            pointer_write(address + 9'h004, value[63:32]);
        end
    endtask

    task automatic run_command(
        input [7:0] command,
        input [7:0] layer,
        input [7:0] flags);
        integer launch_cycles;
        integer completion_cycles;
        begin
            wait (dut.ap_idle === 1'b1 && dut.ap_start === 1'b0);
            control_write(6'h10, command);
            control_write(6'h18, 32'd0);
            control_write(6'h20, layer);
            control_write(6'h28, flags);
            command_start = cycle_count;
            control_write(6'h00, 32'd1);
            launch_cycles = 0;
            while (dut.ap_idle !== 1'b0 && launch_cycles < 200) begin
                @(negedge ap_clk);
                launch_cycles = launch_cycles + 1;
            end
            if (dut.ap_idle !== 1'b0)
                $fatal(1, "command did not leave idle state");
            completion_cycles = 0;
            while (dut.ap_done !== 1'b1 && completion_cycles < 200000000) begin
                @(negedge ap_clk);
                completion_cycles = completion_cycles + 1;
            end
            if (dut.ap_done !== 1'b1)
                $fatal(1, "command exceeded 200,000,000 RTL cycles");
            @(negedge ap_clk);
            $display(
                "RS2_DIRECT_RTL command=%0d cycles=%0d status=%0d generation=%0d",
                command, cycle_count-command_start, mem15.mem[8], mem15_u64(16));
            wait (dut.ap_idle === 1'b1 && dut.ap_start === 1'b0);
        end
    endtask

    task automatic load_assets;
        begin
            $readmemh("assets/initial_primary.hex", initial_primary);
            $readmemh("assets/initial_primary_scales.hex", initial_primary_scales);
            $readmemh("assets/initial_residual.hex", initial_residual);
            $readmemh("assets/initial_residual_scales.hex", initial_residual_scales);
            $readmemh("assets/initial_log_keys.hex", initial_log_keys);
            $readmemh("assets/initial_log_key_scales.hex", initial_log_key_scales);
            $readmemh("assets/initial_log_updates.hex", initial_log_updates);
            $readmemh("assets/initial_log_update_scales.hex", initial_log_update_scales);
            $readmemh("assets/initial_gamma.hex", initial_gamma);
            $readmemh("assets/initial_lambda.hex", initial_lambda);
            $readmemh("assets/initial_live.hex", initial_live);
            $readmemh("assets/q.hex", trace_q);
            $readmemh("assets/q_scales.hex", trace_q_scales);
            $readmemh("assets/k.hex", trace_k);
            $readmemh("assets/k_scales.hex", trace_k_scales);
            $readmemh("assets/v.hex", trace_v);
            $readmemh("assets/v_scales.hex", trace_v_scales);
            $readmemh("assets/alpha.hex", trace_alpha);
            $readmemh("assets/beta.hex", trace_beta);
            $readmemh("assets/status.hex", trace_status);
            $readmemh("assets/generation.hex", trace_generation);
            $readmemh("assets/live.hex", trace_live);
            $readmemh("assets/command_counters.hex", trace_command_counters);
            $readmemh("assets/cumulative_counters.hex", trace_cumulative_counters);
            $readmemh("assets/output_mantissas.hex", trace_output_mantissas);
            $readmemh("assets/output_exponents.hex", trace_output_exponents);
            $readmemh("assets/final_primary.hex", final_primary);
            $readmemh("assets/final_primary_scales.hex", final_primary_scales);
            $readmemh("assets/final_residual.hex", final_residual);
            $readmemh("assets/final_residual_scales.hex", final_residual_scales);
            $readmemh("assets/final_log_keys.hex", final_log_keys);
            $readmemh("assets/final_log_key_scales.hex", final_log_key_scales);
            $readmemh("assets/final_log_updates.hex", final_log_updates);
            $readmemh("assets/final_log_update_scales.hex", final_log_update_scales);
            $readmemh("assets/final_gamma.hex", final_gamma);
            $readmemh("assets/final_lambda.hex", final_lambda);
            $readmemh("assets/final_live.hex", final_live);
            $readmemh("assets/final_status.hex", final_status);
            $readmemh("assets/final_generation.hex", final_generation);
            $readmemh("assets/final_cumulative_counters.hex", final_cumulative_counters);
        end
    endtask

    task automatic load_initial_snapshot;
        begin
            for (item = 0; item < STATE_ELEMENTS; item = item + 1) begin
                mem4.mem[item] = initial_primary[item];
                mem5.mem[item] = initial_residual[item];
            end
            for (item = 0; item < STATE_SCALES; item = item + 1) begin
                mem4.mem[32'h00080000+item] = initial_primary_scales[item];
                mem5.mem[32'h00080000+item] = initial_residual_scales[item];
            end
            for (item = 0; item < LOG_KEY_ELEMENTS; item = item + 1)
                mem6.mem[item] = initial_log_keys[item];
            for (item = 0; item < LOG_KEY_SCALES; item = item + 1)
                mem6.mem[32'h00008000+item] = initial_log_key_scales[item];
            for (item = 0; item < LOG_UPDATE_ELEMENTS; item = item + 1)
                mem7.mem[item] = initial_log_updates[item];
            for (item = 0; item < LOG_UPDATE_SCALES; item = item + 1)
                mem7.mem[32'h00010000+item] = initial_log_update_scales[item];
            for (item = 0; item < HEADS; item = item + 1) begin
                mem8.mem[2*item] = initial_gamma[item][7:0];
                mem8.mem[2*item+1] = initial_gamma[item][15:8];
            end
            for (item = 0; item < LAMBDA_ELEMENTS; item = item + 1) begin
                mem8.mem[32'h00000100+2*item] = initial_lambda[item][7:0];
                mem8.mem[32'h00000100+2*item+1] = initial_lambda[item][15:8];
            end
            live_entries_in = initial_live[0][3:0];
        end
    endtask

    task automatic load_token(input integer token);
        integer token_item;
        begin
            for (token_item = 0; token_item < Q_ELEMENTS; token_item = token_item + 1) begin
                mem0.mem[token_item] = trace_q[token*Q_ELEMENTS+token_item];
                mem1.mem[token_item] = trace_k[token*Q_ELEMENTS+token_item];
            end
            for (token_item = 0; token_item < Q_SCALES; token_item = token_item + 1) begin
                mem16.mem[token_item] = trace_q_scales[token*Q_SCALES+token_item];
                mem17.mem[token_item] = trace_k_scales[token*Q_SCALES+token_item];
            end
            for (token_item = 0; token_item < V_ELEMENTS; token_item = token_item + 1)
                mem2.mem[token_item] = trace_v[token*V_ELEMENTS+token_item];
            for (token_item = 0; token_item < V_SCALES; token_item = token_item + 1)
                mem18.mem[token_item] = trace_v_scales[token*V_SCALES+token_item];
            for (token_item = 0; token_item < HEADS; token_item = token_item + 1) begin
                mem3.mem[2*token_item] = trace_alpha[token*HEADS+token_item][7:0];
                mem3.mem[2*token_item+1] = trace_alpha[token*HEADS+token_item][15:8];
                mem3.mem[32'h00000100+2*token_item] = trace_beta[token*HEADS+token_item][7:0];
                mem3.mem[32'h00000100+2*token_item+1] = trace_beta[token*HEADS+token_item][15:8];
            end
        end
    endtask

    task automatic check_token(input integer token);
        integer token_item;
        integer counter;
        begin
            if (mem15.mem[8] !== trace_status[token] ||
                mem15_u64(16) !== trace_generation[token] ||
                mem15.mem[0] !== trace_live[token])
                $fatal(1, "token metadata mismatch token=%0d", token+1);
            for (counter = 0; counter < COUNTERS; counter = counter + 1) begin
                if (mem15_u64(32+8*counter) !==
                    trace_command_counters[token*COUNTERS+counter])
                    $fatal(1, "command counter mismatch token=%0d counter=%0d", token+1, counter);
                if (mem15_u64(96+8*counter) !==
                    trace_cumulative_counters[token*COUNTERS+counter])
                    $fatal(1, "cumulative counter mismatch token=%0d counter=%0d", token+1, counter);
            end
            for (token_item = 0; token_item < OUTPUT_ELEMENTS; token_item = token_item + 1) begin
                if (mem9_u32(4*token_item) !==
                    trace_output_mantissas[token*OUTPUT_ELEMENTS+token_item])
                    $fatal(1, "output mantissa mismatch token=%0d item=%0d", token+1, token_item);
                if (mem19_u16(2*token_item) !==
                    trace_output_exponents[token*OUTPUT_ELEMENTS+token_item])
                    $fatal(1, "output exponent mismatch token=%0d item=%0d", token+1, token_item);
            end
            $display("RS2_DIRECT_RTL_TOKEN token=%0d status=%0d generation=%0d live=%0d PASS",
                     token+1, mem15.mem[8], mem15_u64(16), mem15.mem[0]);
        end
    endtask

    task automatic check_final_snapshot;
        integer counter;
        begin
            if (mem15.mem[0] !== final_live[0] ||
                mem15.mem[8] !== final_status[0] ||
                mem15_u64(16) !== final_generation[0])
                $fatal(1, "final readback metadata mismatch");
            for (counter = 0; counter < COUNTERS; counter = counter + 1)
                if (mem15_u64(96+8*counter) !== final_cumulative_counters[counter])
                    $fatal(1, "final cumulative counter mismatch counter=%0d", counter);
            for (item = 0; item < STATE_ELEMENTS; item = item + 1) begin
                if (mem10.mem[item] !== final_primary[item])
                    $fatal(1, "final primary mismatch item=%0d", item);
                if (mem11.mem[item] !== final_residual[item])
                    $fatal(1, "final residual mismatch item=%0d", item);
            end
            for (item = 0; item < STATE_SCALES; item = item + 1) begin
                if (mem10.mem[32'h00080000+item] !== final_primary_scales[item])
                    $fatal(1, "final primary scale mismatch item=%0d", item);
                if (mem11.mem[32'h00080000+item] !== final_residual_scales[item])
                    $fatal(1, "final residual scale mismatch item=%0d", item);
            end
            for (item = 0; item < LOG_KEY_ELEMENTS; item = item + 1)
                if (mem12.mem[item] !== final_log_keys[item])
                    $fatal(1, "final key log mismatch item=%0d", item);
            for (item = 0; item < LOG_KEY_SCALES; item = item + 1)
                if (mem12.mem[32'h00008000+item] !== final_log_key_scales[item])
                    $fatal(1, "final key-log scale mismatch item=%0d", item);
            for (item = 0; item < LOG_UPDATE_ELEMENTS; item = item + 1)
                if (mem13.mem[item] !== final_log_updates[item])
                    $fatal(1, "final update log mismatch item=%0d", item);
            for (item = 0; item < LOG_UPDATE_SCALES; item = item + 1)
                if (mem13.mem[32'h00010000+item] !== final_log_update_scales[item])
                    $fatal(1, "final update-log scale mismatch item=%0d", item);
            for (item = 0; item < HEADS; item = item + 1)
                if (mem14_u16(2*item) !== final_gamma[item])
                    $fatal(1, "final gamma mismatch item=%0d", item);
            for (item = 0; item < LAMBDA_ELEMENTS; item = item + 1)
                if (mem14_u16(32'h00000100+2*item) !== final_lambda[item])
                    $fatal(1, "final lambda mismatch item=%0d", item);
        end
    endtask

    task automatic configure_pointers;
        begin
            set_pointer(9'h010, 64'h00000000);
            set_pointer(9'h01c, 64'h00000000);
            set_pointer(9'h028, 64'h00000000);
            set_pointer(9'h034, 64'h00000000);
            set_pointer(9'h040, 64'h00000000);
            set_pointer(9'h04c, 64'h00000000);
            set_pointer(9'h058, 64'h00000000);
            set_pointer(9'h064, 64'h00000100);
            set_pointer(9'h070, 64'h00000000);
            set_pointer(9'h07c, 64'h00080000);
            set_pointer(9'h088, 64'h00000000);
            set_pointer(9'h094, 64'h00080000);
            set_pointer(9'h0a0, 64'h00000000);
            set_pointer(9'h0ac, 64'h00008000);
            set_pointer(9'h0b8, 64'h00000000);
            set_pointer(9'h0c4, 64'h00010000);
            set_pointer(9'h0d0, 64'h00000000);
            set_pointer(9'h0dc, 64'h00000100);
            set_pointer(9'h0e8, 64'h00000000);
            set_pointer(9'h0f4, 64'h00000000);
            set_pointer(9'h100, 64'h00000000);
            set_pointer(9'h10c, 64'h00080000);
            set_pointer(9'h118, 64'h00000000);
            set_pointer(9'h124, 64'h00080000);
            set_pointer(9'h130, 64'h00000000);
            set_pointer(9'h13c, 64'h00008000);
            set_pointer(9'h148, 64'h00000000);
            set_pointer(9'h154, 64'h00010000);
            set_pointer(9'h160, 64'h00000000);
            set_pointer(9'h16c, 64'h00000100);
            set_pointer(9'h178, 64'h00000000);
            set_pointer(9'h184, 64'h00000008);
            set_pointer(9'h190, 64'h00000010);
            set_pointer(9'h19c, 64'h00000020);
            set_pointer(9'h1a8, 64'h00000060);
        end
    endtask

    initial begin
        integer token;
        integer token_limit;
        if (!$value$plusargs("TOKEN_LIMIT=%d", token_limit))
            token_limit = TRACE_TOKENS;
        if (token_limit < 0 || token_limit > TRACE_TOKENS)
            $fatal(1, "TOKEN_LIMIT must be in [0,64]");
        load_assets();
        load_initial_snapshot();
        repeat (10) @(posedge ap_clk);
        ap_rst_n = 1'b1;
        repeat (10) @(posedge ap_clk);
        configure_pointers();

        run_command(8'd1, 8'd4, 8'd1);
        if (mem15.mem[8] !== 8'd0 || mem15_u64(16) !== 64'd1 ||
            mem15.mem[0] !== initial_live[0])
            $fatal(1, "initial LOAD metadata mismatch");
        live_entries_in = 4'd0;

        for (token = 0; token < token_limit; token = token + 1) begin
            load_token(token);
            run_command(8'd2, 8'd4, 8'd2);
            check_token(token);
        end

        if (token_limit != TRACE_TOKENS) begin
            $display("RS2_DIRECT_RTL_BENCHMARK PASS tokens=%0d", token_limit);
            $finish;
        end

        run_command(8'd3, 8'd4, 8'd0);
        check_final_snapshot();
        $display(
            "RS2_DIRECT_RTL_TRACE64 PASS tokens=64 transactions=66 outputs=262144 final_snapshot=PASS");
        $finish;
    end
endmodule

`undef CONNECT_MEM
`undef DECL_AXI

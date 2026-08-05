`timescale 1ns / 1ps

module axi_memory_model #(
    parameter integer DATA_WIDTH = 32,
    parameter integer MEM_BYTES = 4096
) (
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    awvalid,
    output wire                    awready,
    input  wire [63:0]             awaddr,
    input  wire [0:0]              awid,
    input  wire [7:0]              awlen,
    input  wire [2:0]              awsize,
    input  wire [1:0]              awburst,
    input  wire                    wvalid,
    output wire                    wready,
    input  wire [DATA_WIDTH-1:0]   wdata,
    input  wire [DATA_WIDTH/8-1:0] wstrb,
    input  wire                    wlast,
    output reg                     bvalid,
    input  wire                    bready,
    output wire [1:0]              bresp,
    output reg  [0:0]              bid,
    output wire [0:0]              buser,
    input  wire                    arvalid,
    output wire                    arready,
    input  wire [63:0]             araddr,
    input  wire [0:0]              arid,
    input  wire [7:0]              arlen,
    input  wire [2:0]              arsize,
    input  wire [1:0]              arburst,
    output reg                     rvalid,
    input  wire                    rready,
    output reg  [DATA_WIDTH-1:0]   rdata,
    output reg                     rlast,
    output reg  [0:0]              rid,
    output wire [0:0]              ruser,
    output wire [1:0]              rresp
);
    localparam integer STRB_WIDTH = DATA_WIDTH / 8;

    reg [7:0] mem [0:MEM_BYTES-1];
    reg write_active;
    reg [63:0] write_addr;
    reg [2:0] write_size;
    reg [8:0] write_beats;
    reg [0:0] write_id;
    reg read_active;
    reg [63:0] read_addr;
    reg [2:0] read_size;
    reg [8:0] read_beats;
    reg [0:0] read_id;
    integer index;

    initial begin
        for (index = 0; index < MEM_BYTES; index = index + 1)
            mem[index] = 8'h00;
    end

    assign awready = !write_active && !bvalid;
    assign wready = write_active && !bvalid;
    assign bresp = 2'b00;
    assign buser = 1'b0;
    assign arready = !read_active && !rvalid;
    assign rresp = 2'b00;
    assign ruser = 1'b0;

    always @(posedge clk) begin
        if (rst) begin
            write_active <= 1'b0;
            write_addr <= 64'd0;
            write_size <= 3'd0;
            write_beats <= 9'd0;
            write_id <= 1'b0;
            bvalid <= 1'b0;
            bid <= 1'b0;
        end else begin
            if (awvalid && awready) begin
                if (awburst != 2'b01)
                    $fatal(1, "only AXI INCR writes are supported");
                write_active <= 1'b1;
                write_addr <= awaddr;
                write_size <= awsize;
                write_beats <= {1'b0, awlen} + 9'd1;
                write_id <= awid;
            end

            if (wvalid && wready) begin
                for (index = 0; index < STRB_WIDTH; index = index + 1) begin
                    if (wstrb[index]) begin
                        if (write_addr + index >= MEM_BYTES)
                            $fatal(1, "AXI write address outside memory");
                        mem[write_addr + index] <= wdata[index * 8 +: 8];
                    end
                end
                if (wlast) begin
                    if (write_beats != 9'd1)
                        $fatal(1, "AXI WLAST before final beat");
                    write_active <= 1'b0;
                    bvalid <= 1'b1;
                    bid <= write_id;
                end else begin
                    if (write_beats <= 9'd1)
                        $fatal(1, "AXI write burst omitted WLAST");
                    write_addr <= write_addr + (64'd1 << write_size);
                    write_beats <= write_beats - 9'd1;
                end
            end

            if (bvalid && bready)
                bvalid <= 1'b0;
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            read_active <= 1'b0;
            read_addr <= 64'd0;
            read_size <= 3'd0;
            read_beats <= 9'd0;
            read_id <= 1'b0;
            rvalid <= 1'b0;
            rdata <= {DATA_WIDTH{1'b0}};
            rlast <= 1'b0;
            rid <= 1'b0;
        end else begin
            if (arvalid && arready) begin
                if (arburst != 2'b01)
                    $fatal(1, "only AXI INCR reads are supported");
                read_active <= 1'b1;
                read_addr <= araddr;
                read_size <= arsize;
                read_beats <= {1'b0, arlen} + 9'd1;
                read_id <= arid;
            end

            if (read_active && !rvalid) begin
                for (index = 0; index < STRB_WIDTH; index = index + 1) begin
                    if (read_addr + index >= MEM_BYTES)
                        $fatal(1, "AXI read address outside memory");
                    rdata[index * 8 +: 8] <= mem[read_addr + index];
                end
                rvalid <= 1'b1;
                rlast <= read_beats == 9'd1;
                rid <= read_id;
            end

            if (rvalid && rready) begin
                rvalid <= 1'b0;
                if (rlast) begin
                    read_active <= 1'b0;
                    rlast <= 1'b0;
                end else begin
                    read_addr <= read_addr + (64'd1 << read_size);
                    read_beats <= read_beats - 9'd1;
                end
            end
        end
    end
endmodule

create_clock -period 4.000 -name ap_clk [get_ports ap_clk]
set_input_delay 1.000 -clock ap_clk [get_ports -filter {DIRECTION == IN && NAME != ap_clk}]
set_output_delay 1.000 -clock ap_clk [all_outputs]

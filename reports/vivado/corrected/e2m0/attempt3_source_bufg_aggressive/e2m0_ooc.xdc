# The platform shell supplies a clock buffer and synchronizes startup reset.
set_false_path -from [get_ports ap_rst_n]

# Boundary hold depends on shell placement; retain setup and all internal hold checks.
set_false_path -hold -from [get_ports -filter {DIRECTION == IN && NAME != ap_clk}]


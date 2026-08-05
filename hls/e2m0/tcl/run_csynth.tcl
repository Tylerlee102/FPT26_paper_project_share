open_project -reset gdn_e2m0_hls
set_top gdn_e2m0_top
set config_cflags "-Ihls/include -Ihls/e2m0/include -std=c++14"
add_files -cflags $config_cflags hls/e2m0/src/e2m0_arithmetic.cpp
add_files -cflags $config_cflags hls/e2m0/src/gdn_e2m0_top.cpp
open_solution -reset "u55c_250mhz"
set_part {xcu55c-fsvh2892-2L-e}
create_clock -period 4.0 -name default
config_compile -pipeline_loops 0
csynth_design
exit

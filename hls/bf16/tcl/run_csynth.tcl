open_project -reset gdn_bf16_hls
set_top gdn_bf16_top
set config_cflags "-Ihls/include -Ihls/bf16/include -std=c++14"
add_files -cflags $config_cflags hls/bf16/src/gdn_bf16_top.cpp
open_solution -reset "u55c_250mhz"
set_part {xcu55c-fsvh2892-2L-e}
create_clock -period 4.0 -name default
config_compile -pipeline_loops 0
csynth_design
exit

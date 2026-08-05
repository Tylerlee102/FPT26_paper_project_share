open_project -reset gdn_mxfp8_csim_hls
set_top gdn_mxfp8_top
set config_cflags "-Ihls/mxfp8/include -Ihls/include -std=c++14"
add_files -cflags $config_cflags hls/mxfp8/src/gdn_mxfp8_top.cpp
add_files -cflags $config_cflags hls/mxfp8/src/e4m3_arithmetic.cpp
add_files -cflags $config_cflags hls/src/block_exp_align.cpp
add_files -cflags $config_cflags hls/mxfp8/src/phase1_prepare.cpp
add_files -cflags $config_cflags hls/mxfp8/src/phase2_state_read.cpp
add_files -cflags $config_cflags hls/mxfp8/src/phase3_update.cpp
add_files -cflags $config_cflags hls/mxfp8/src/phase4_state_write.cpp
add_files -cflags $config_cflags hls/mxfp8/src/phase5_output.cpp
add_files -tb hls/mxfp8/tb/tb_gdn_mxfp8_top.cpp -cflags $config_cflags
open_solution -reset "u55c_250mhz"
set_part {xcu55c-fsvh2892-2L-e}
create_clock -period 4.0 -name default
csim_design
exit

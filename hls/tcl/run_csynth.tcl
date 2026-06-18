open_project gdn_mxfp4_hls
set_top gdn_top
set config_cflags "-Ihls/include"
if {[info exists ::env(GDN_P_K)]} {
  append config_cflags " -DGDN_P_K=$::env(GDN_P_K)"
}
if {[info exists ::env(GDN_P_V)]} {
  append config_cflags " -DGDN_P_V=$::env(GDN_P_V)"
}
if {[info exists ::env(GDN_BLOCK_SIZE)]} {
  append config_cflags " -DGDN_BLOCK_SIZE=$::env(GDN_BLOCK_SIZE)"
}
add_files -cflags $config_cflags hls/src/gdn_top.cpp
add_files -cflags $config_cflags hls/src/mac_e2m1.cpp
add_files -cflags $config_cflags hls/src/block_exp_align.cpp
add_files -cflags $config_cflags hls/src/phase1_prepare.cpp
add_files -cflags $config_cflags hls/src/phase2_state_read.cpp
add_files -cflags $config_cflags hls/src/phase3_update.cpp
add_files -cflags $config_cflags hls/src/phase4_state_write.cpp
add_files -cflags $config_cflags hls/src/phase5_output.cpp
open_solution -reset "u55c_250mhz"
set_part {xcu55c-fsvh2892-2L-e}
create_clock -period 4.0 -name default
csynth_design
exit

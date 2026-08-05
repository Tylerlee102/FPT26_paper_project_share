open_project -reset gdn_e2m0_arithmetic_hls
set_top e2m0_arithmetic_top
set config_cflags "-Ihls/include -Ihls/e2m0/include -std=c++14"
add_files -cflags $config_cflags hls/e2m0/src/e2m0_arithmetic.cpp
add_files -tb -cflags $config_cflags hls/e2m0/tb/tb_e2m0_arithmetic.cpp
open_solution -reset "u55c_250mhz"
set_part {xcu55c-fsvh2892-2L-e}
create_clock -period 4.0 -name default
set vector_path [file normalize "data/vectors/e2m0_arithmetic_v1.txt"]
if {![file exists $vector_path]} {
  error "missing E2M0 arithmetic vectors: $vector_path"
}
csim_design -clean -argv $vector_path
exit

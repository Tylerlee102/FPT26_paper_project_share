open_project -reset gdn_e2m0_trace_hls
set_top gdn_e2m0_top
set config_cflags "-Ihls/include -Ihls/e2m0/include -std=c++14"
add_files -cflags $config_cflags hls/e2m0/src/e2m0_arithmetic.cpp
add_files -cflags $config_cflags hls/e2m0/src/gdn_e2m0_top.cpp
add_files -tb -cflags $config_cflags hls/e2m0/tb/tb_gdn_e2m0_trace.cpp
open_solution -reset "u55c_250mhz"
set_part {xcu55c-fsvh2892-2L-e}
create_clock -period 4.0 -name default
if {[info exists ::env(E2M0_TRACE_PATH)] && $::env(E2M0_TRACE_PATH) ne ""} {
  set trace_path [file normalize $::env(E2M0_TRACE_PATH)]
} else {
  set trace_path [file normalize "data/vectors/e2m0_resident_trace8.bin"]
}
if {![file exists $trace_path]} {
  error "missing E2M0 resident trace: $trace_path"
}
csim_design -clean -argv $trace_path
exit

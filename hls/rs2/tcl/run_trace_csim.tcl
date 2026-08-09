open_project -reset gdn_rs2_trace_hls
set_top gdn_rs2_top
set config_cflags "-Ihls/include -Ihls/rs2/include -std=c++14"
add_files -cflags $config_cflags hls/rs2/src/rs2_arithmetic.cpp
add_files -cflags $config_cflags hls/rs2/src/gdn_rs2_top.cpp
add_files -tb -cflags $config_cflags hls/rs2/tb/tb_gdn_rs2_trace.cpp
open_solution -reset "u55c_250mhz"
set_part {xcu55c-fsvh2892-2L-e}
create_clock -period 4.0 -name default
if {[info exists ::env(RS2_TRACE_PATH)] && $::env(RS2_TRACE_PATH) ne ""} {
  set trace_path [file normalize $::env(RS2_TRACE_PATH)]
} else {
  set trace_path [file normalize "data/vectors/rs2_resident_trace64.bin"]
}
if {![file exists $trace_path]} {
  error "missing RS2 resident trace: $trace_path"
}
set trace_argv [format {"%s"} $trace_path]
csim_design -clean -argv $trace_argv
exit

open_project -reset gdn_rs2_trace_cosim_hls
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

set cosim_mingw ""
if {[info exists ::env(GDN_COSIM_MINGW)] &&
    [file isdirectory $::env(GDN_COSIM_MINGW)]} {
  set cosim_mingw $::env(GDN_COSIM_MINGW)
} elseif {[info exists ::env(XILINX_VITIS)]} {
  set install_root [file dirname $::env(XILINX_VITIS)]
  foreach mingw_version {10.0.0 6.2.0} {
    set mingw_dir [file join $install_root tps mingw $mingw_version win64.o nt bin]
    if {[file isdirectory $mingw_dir]} {
      set cosim_mingw $mingw_dir
      break
    }
  }
}
if {$cosim_mingw ne ""} {
  set ::env(PATH) "$cosim_mingw;$::env(PATH)"
  puts "RS2_TRACE_COSIM_RUNTIME=$cosim_mingw"
}

set trace_argv [format {"%s"} $trace_path]
csim_design -clean -argv $trace_argv
csynth_design
cosim_design -rtl verilog -tool xsim -argv $trace_argv
exit

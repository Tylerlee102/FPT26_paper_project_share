open_project -reset gdn_e2m0_trace_cosim_hls
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
  set trace_path [file normalize "data/vectors/e2m0_resident_trace64.bin"]
}
if {![file exists $trace_path]} {
  error "missing E2M0 resident trace: $trace_path"
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
  puts "E2M0_TRACE_COSIM_RUNTIME=$cosim_mingw"
}

csim_design -clean -argv $trace_path
csynth_design
cosim_design -rtl verilog -tool xsim -argv $trace_path
exit

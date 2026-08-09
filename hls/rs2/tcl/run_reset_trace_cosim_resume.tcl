open_project gdn_rs2_reset_trace_cosim_hls
set_top gdn_rs2_top
open_solution "u55c_250mhz"

if {[info exists ::env(RS2_TRACE_PATH)] && $::env(RS2_TRACE_PATH) ne ""} {
  set trace_path [file normalize $::env(RS2_TRACE_PATH)]
} else {
  set trace_path [file normalize "data/vectors/rs2_resident_trace64_reset.bin"]
}
if {![file exists $trace_path]} {
  error "missing RS2 reset-initialized trace: $trace_path"
}

# Vitis HLS 2025.2 can finish RTL generation without emitting this interface
# metadata file in a freshly created classic project. The donor project uses
# the same top function and source files; only its testbench differs.
set solution_data [file normalize "gdn_rs2_reset_trace_cosim_hls/u55c_250mhz/u55c_250mhz_data.json"]
if {![file exists $solution_data]} {
  set donor_data [file normalize "gdn_rs2_hls/u55c_250mhz/u55c_250mhz_data.json"]
  if {![file exists $donor_data]} {
    error "missing both reset-project and source-identical donor interface metadata"
  }
  file copy -force $donor_data $solution_data
  puts "RS2_RESET_TRACE_COSIM_METADATA_REUSED=$donor_data"
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
  puts "RS2_RESET_TRACE_COSIM_RUNTIME=$cosim_mingw"
}

set trace_argv [format {"%s"} $trace_path]
cosim_design -O -disable_deadlock_detection -rtl verilog -tool xsim -argv $trace_argv
exit

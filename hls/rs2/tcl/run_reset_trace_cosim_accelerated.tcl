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

set solution_data [file normalize "gdn_rs2_reset_trace_cosim_hls/u55c_250mhz/u55c_250mhz_data.json"]
if {![file exists $solution_data]} {
  set donor_data [file normalize "gdn_rs2_hls/u55c_250mhz/u55c_250mhz_data.json"]
  if {![file exists $donor_data]} {
    error "missing both reset-project and source-identical donor interface metadata"
  }
  file copy -force $donor_data $solution_data
  puts "RS2_ACCELERATED_COSIM_METADATA_REUSED=$donor_data"
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
  puts "RS2_ACCELERATED_COSIM_RUNTIME=$cosim_mingw"
}

set trace_argv [format {"%s"} $trace_path]
cosim_design -O -disable_deadlock_detection -trace_level none -rtl verilog -tool xsim -argv $trace_argv -setup

set sim_dir [file normalize "gdn_rs2_reset_trace_cosim_hls/u55c_250mhz/sim/verilog"]
set run_bat [file join $sim_dir run_xsim.bat]
set completion [file join $sim_dir rs2_accelerated_cosim_complete.txt]
if {[file exists $completion]} {
  file delete -force $completion
}
set handle [open $run_bat r]
set batch_text [read $handle]
close $handle
set replacement_count [regsub -all -line {^(call .*[/\\]xelab) } $batch_text {\1 --O3 --debug off --mt 8 } patched_batch]
if {$replacement_count != 1} {
  error "expected exactly one generated xelab command in $run_bat, found $replacement_count"
}
set handle [open $run_bat w]
puts -nonewline $handle $patched_batch
close $handle
puts "RS2_ACCELERATED_XELAB_PATCHED=$run_bat"

set old_dir [pwd]
cd $sim_dir
source [file join $sim_dir run_sim.tcl]
cd $old_dir

set xsim_log [file join $sim_dir xsim.log]
set postcheck_log [file normalize "gdn_rs2_reset_trace_cosim_hls/u55c_250mhz/sim/wrapc_pc/temp0.log"]
set handle [open $xsim_log r]
set xsim_text [read $handle]
close $handle
set handle [open $postcheck_log r]
set postcheck_text [read $handle]
close $handle
set pass_marker "PASS: 64 encoded reset-state tokens, exact outputs/counters, and final snapshot"
if {[string first "RTL Simulation : 66 / 66" $xsim_text] < 0} {
  error "accelerated XSim did not complete all 66 transactions"
}
if {[string first $pass_marker $postcheck_text] < 0} {
  error "accelerated HLS post-check did not emit the exact 64-token PASS marker"
}
if {[string first "Out of memory" $xsim_text] >= 0 ||
    [string first "Simulation engine not responding" $xsim_text] >= 0} {
  error "accelerated XSim log contains a simulator failure"
}

set handle [open $completion w]
puts $handle "RS2_ACCELERATED_HLS_XSIM_PASS"
puts $handle "transactions=66"
puts $handle "tokens=64"
puts $handle "xelab_options=--O3 --debug off --mt 8"
puts $handle "postcheck=$pass_marker"
close $handle
puts "RS2_ACCELERATED_HLS_XSIM_PASS tokens=64 transactions=66"
exit

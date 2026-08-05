open_project gdn_mxfp4_hls
set cosim_vectors 64
if {[info exists ::env(GDN_COSIM_VECTORS)]} {
  set cosim_vectors $::env(GDN_COSIM_VECTORS)
}
set config_cflags "-I../../hls/include -std=c++14 -DGDN_TB_VECTORS=${cosim_vectors}"
if {[info exists ::env(GDN_P_K)]} {
  append config_cflags " -DGDN_P_K=$::env(GDN_P_K)"
}
if {[info exists ::env(GDN_P_V)]} {
  append config_cflags " -DGDN_P_V=$::env(GDN_P_V)"
}
if {[info exists ::env(GDN_BLOCK_SIZE)]} {
  append config_cflags " -DGDN_BLOCK_SIZE=$::env(GDN_BLOCK_SIZE)"
}
append config_cflags " -Wno-unknown-pragmas"
set app_file "gdn_mxfp4_hls/hls.app"
if {[file exists $app_file]} {
  set fh [open $app_file r]
  set app_data [read $fh]
  close $fh
  set app_out ""
  foreach line [split $app_data "\n"] {
    if {[string first "tb_gdn_top.cpp" $line] >= 0} {
      regsub {cflags="[^"]*"} $line "cflags=\"$config_cflags\"" line
    }
    append app_out $line "\n"
  }
  set fh [open $app_file w]
  puts -nonewline $fh $app_out
  close $fh
}
open_solution "u55c_250mhz"
set trace_path "data/vectors/corrected_gdn_command_trace.bin"
if {[info exists ::env(GDN_COSIM_TRACE)]} {
  set trace_path $::env(GDN_COSIM_TRACE)
}
set trace_path [file normalize $trace_path]
if {![file exists $trace_path]} {
  error "missing corrected oracle trace: $trace_path"
}
set cosim_rtl "verilog"
if {[info exists ::env(GDN_COSIM_RTL)]} {
  set cosim_rtl [string tolower $::env(GDN_COSIM_RTL)]
}
if {$cosim_rtl ni {verilog vhdl}} {
  error "GDN_COSIM_RTL must be 'verilog' or 'vhdl', got '$cosim_rtl'"
}
cosim_design -rtl $cosim_rtl -tool xsim -argv $trace_path
exit

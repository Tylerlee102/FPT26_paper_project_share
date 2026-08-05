open_project gdn_e2m0_hls
set_top gdn_e2m0_top
set config_cflags "-Ihls/include -Ihls/e2m0/include -std=c++14"
add_files -tb -cflags $config_cflags hls/e2m0/tb/tb_gdn_e2m0_rtl_control.cpp
open_solution "u55c_250mhz"
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
  puts "E2M0_COSIM_RUNTIME=$cosim_mingw"
}
cosim_design -rtl verilog -tool xsim
exit

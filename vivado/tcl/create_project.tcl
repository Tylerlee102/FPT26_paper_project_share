proc add_vivado_tclstore_path {} {
  set candidates {}
  if {[info exists ::env(XILINX_VIVADO)]} {
    lappend candidates [file join $::env(XILINX_VIVADO) data XilinxTclStore]
  }
  lappend candidates "C:/AMDDesignTools/2025.2/Vivado/data/XilinxTclStore"

  foreach store $candidates {
    if {![file isdirectory $store]} {
      continue
    }
    foreach path [list $store [file join $store support] [file join $store support appinit]] {
      if {[file isdirectory $path] && [lsearch -exact $::auto_path $path] < 0} {
        lappend ::auto_path $path
      }
    }
    if {![catch {package require ::tclapp::support::appinit 1.2}]} {
      return
    }
  }
}

add_vivado_tclstore_path

set root_dir [file normalize [pwd]]
set project_dir [file normalize "build/vivado/gdn_mxfp4_vivado"]
set rtl_dir [file normalize "gdn_mxfp4_hls/u55c_250mhz/syn/verilog"]
set xdc_file [file normalize "vivado/constraints/timing.xdc"]

if {![file isdirectory $rtl_dir]} {
  error "Missing HLS RTL directory: $rtl_dir"
}

create_project -force gdn_mxfp4_vivado $project_dir -part xcu55c-fsvh2892-2L-e
set_property target_language Verilog [current_project]
set_property source_mgmt_mode None [current_project]

set rtl_files [glob -nocomplain -directory $rtl_dir *.v]
if {[llength $rtl_files] == 0} {
  error "No Verilog files found in $rtl_dir"
}

read_verilog $rtl_files
read_xdc $xdc_file
set_property top gdn_top [current_fileset]
update_compile_order -fileset sources_1

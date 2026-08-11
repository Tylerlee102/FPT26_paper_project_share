set root_dir [file normalize [pwd]]
set project_dir [file normalize "build/vivado/gdn_rs2_fold_write_address_fanout16_vivado"]
set rtl_dir [file normalize "build/experiments/rs2_fold_write_address_fanout16/rtl"]
set ooc_top_file [file normalize "build/vivado/rs2_fold_write_address_fanout16_ooc_rtl/gdn_rs2_top.v"]
set xdc_file [file normalize "vivado/constraints/timing.xdc"]
set ooc_xdc_file [file normalize "vivado/constraints/rs2_ooc.xdc"]

if {![file isdirectory $rtl_dir]} {
  error "Missing fold-write address-fanout RTL directory: $rtl_dir"
}
if {![file isfile $ooc_top_file]} {
  error "Missing fold-write address-fanout generated OOC top: $ooc_top_file"
}

create_project -force gdn_rs2_fold_write_address_fanout16_vivado $project_dir -part xcu55c-fsvh2892-2L-e
set_property target_language Verilog [current_project]
set_property source_mgmt_mode None [current_project]

set generated_rtl_files [glob -nocomplain -directory $rtl_dir *.v]
if {[llength $generated_rtl_files] == 0} {
  error "No fold-write address-fanout Verilog files found in $rtl_dir"
}

set support_rtl_files {}
foreach rtl_file $generated_rtl_files {
  if {[file tail $rtl_file] ne "gdn_rs2_top.v"} {
    lappend support_rtl_files $rtl_file
  }
}
read_verilog $support_rtl_files
read_verilog $ooc_top_file
set memory_files [glob -nocomplain -directory $rtl_dir *.dat]
if {[llength $memory_files] > 0} {
  add_files -norecurse $memory_files
}
read_xdc $xdc_file
read_xdc $ooc_xdc_file
set_property top gdn_rs2_top [current_fileset]
update_compile_order -fileset sources_1
set_param general.maxThreads 8

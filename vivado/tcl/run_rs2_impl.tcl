set_param general.maxThreads 8
set report_dir [file normalize "reports/vivado/corrected/rs2_current"]
set checkpoint_dir [file normalize "build/vivado/gdn_rs2_vivado"]
set synth_checkpoint [file join $checkpoint_dir rs2_post_synth.dcp]
file mkdir $report_dir
file mkdir $checkpoint_dir

if {[file exists $synth_checkpoint]} {
  open_checkpoint $synth_checkpoint
} else {
  source vivado/tcl/create_rs2_project.tcl
  synth_design -top gdn_rs2_top -part xcu55c-fsvh2892-2L-e -mode out_of_context
  write_checkpoint -force $synth_checkpoint
}

if {[llength [get_cells -quiet ooc_ap_clk_bufg]] != 1} {
  error "Synthesized checkpoint does not contain the generated OOC BUFGCE"
}

opt_design -directive ExploreWithRemap
place_design -directive ExtraNetDelay_high
phys_opt_design -directive AggressiveExplore
route_design -directive AggressiveExplore

report_utilization -file [file join $report_dir impl_util.rpt]
report_utilization -hierarchical -file [file join $report_dir impl_util_hierarchical.rpt]
report_clock_utilization -file [file join $report_dir impl_clock_util.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose \
  -file [file join $report_dir impl_timing.rpt]
report_drc -file [file join $report_dir impl_drc.rpt]
report_methodology -file [file join $report_dir impl_methodology.rpt]
report_power -file [file join $report_dir impl_power.rpt]
write_checkpoint -force [file join $checkpoint_dir rs2_post_impl.dcp]
exit

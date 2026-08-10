set report_dir [file normalize "reports/vivado/experiments/rs2_snapshot_write_unbanked_fsm_fanout16_20260810"]
set checkpoint_dir [file normalize "build/vivado/gdn_rs2_snapshot_write_unbanked_fsm_fanout16_vivado"]
set synth_checkpoint [file join $checkpoint_dir rs2_snapshot_write_unbanked_fsm_fanout16_post_synth.dcp]
file mkdir $report_dir
file mkdir $checkpoint_dir

source vivado/tcl/create_rs2_snapshot_write_unbanked_fsm_fanout_project.tcl
synth_design -top gdn_rs2_top -part xcu55c-fsvh2892-2L-e -mode out_of_context
write_checkpoint -force $synth_checkpoint

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
report_design_analysis -timing -logic_level_distribution \
  -file [file join $report_dir design_analysis.rpt]
report_timing -delay_type max -max_paths 100 -nworst 1 -path_type summary \
  -file [file join $report_dir worst_100_setup_paths.rpt]
write_checkpoint -force [file join $checkpoint_dir rs2_snapshot_write_unbanked_fsm_fanout16_post_impl.dcp]
exit

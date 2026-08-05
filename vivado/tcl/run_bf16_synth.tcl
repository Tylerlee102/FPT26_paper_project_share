set_param general.maxThreads 8
set report_dir [file normalize "reports/vivado/baselines/bf16"]
set checkpoint_dir [file normalize "build/vivado/gdn_bf16_vivado"]
file mkdir $report_dir
file mkdir $checkpoint_dir

source vivado/tcl/create_bf16_project.tcl

synth_design -top gdn_bf16_top -part xcu55c-fsvh2892-2L-e -mode out_of_context

report_utilization -hierarchical -file [file join $report_dir synth_util.rpt]
report_clock_utilization -file [file join $report_dir synth_clock_util.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose \
  -file [file join $report_dir synth_timing.rpt]
report_drc -file [file join $report_dir synth_drc.rpt]
write_checkpoint -force [file join $checkpoint_dir bf16_post_synth.dcp]
exit

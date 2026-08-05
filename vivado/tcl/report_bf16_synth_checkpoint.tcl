set_param general.maxThreads 8
set report_dir [file normalize "reports/vivado/baselines/bf16"]
set checkpoint [file normalize "build/vivado/gdn_bf16_vivado/bf16_post_synth.dcp"]
file mkdir $report_dir

if {![file isfile $checkpoint]} {
  error "Missing BF16 synthesis checkpoint: $checkpoint"
}

open_checkpoint $checkpoint
report_utilization -file [file join $report_dir synth_util.rpt]
report_utilization -hierarchical -file [file join $report_dir synth_util_hierarchical.rpt]
report_clock_utilization -file [file join $report_dir synth_clock_util.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose \
  -file [file join $report_dir synth_timing.rpt]
report_drc -file [file join $report_dir synth_drc.rpt]
exit

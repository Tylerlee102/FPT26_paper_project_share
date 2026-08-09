set_param general.maxThreads 8

set checkpoint [file normalize "build/vivado/gdn_rs2_vivado/rs2_post_impl.dcp"]
set report_dir [file normalize "reports/vivado/corrected/rs2_current/timing_analysis"]
file mkdir $report_dir

if {![file isfile $checkpoint]} {
  error "Missing selected RS2/R3 routed checkpoint: $checkpoint"
}

open_checkpoint $checkpoint
create_clock -period 4.000 -name ap_clk [get_ports ap_clk]
report_timing -delay_type max -max_paths 100 -nworst 1 -path_type summary \
  -file [file join $report_dir worst_100_setup_paths.rpt]
report_design_analysis -timing -logic_level_distribution \
  -file [file join $report_dir design_analysis.rpt]
exit

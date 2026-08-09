set_param general.maxThreads 8

set checkpoint [file normalize "build/vivado/gdn_rs2_vivado/rs2_post_impl.dcp"]
set output_checkpoint [file normalize "build/vivado/gdn_rs2_vivado/rs2_post_impl_slr_opt.dcp"]
set report_dir [file normalize "reports/vivado/corrected/rs2_current/postroute_slr_opt"]
file mkdir $report_dir

if {![file isfile $checkpoint]} {
  error "Missing selected RS2/R3 routed checkpoint: $checkpoint"
}

open_checkpoint $checkpoint
create_clock -period 4.000 -name ap_clk [get_ports ap_clk]
phys_opt_design -slr_crossing_opt
report_timing_summary -delay_type min_max -report_unconstrained \
  -check_timing_verbose -file [file join $report_dir timing_4p000ns.rpt]
report_utilization -file [file join $report_dir utilization.rpt]
report_drc -file [file join $report_dir drc.rpt]
write_checkpoint -force $output_checkpoint
exit

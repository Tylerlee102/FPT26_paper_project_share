set_param general.maxThreads 8
set report_dir [file normalize "reports/vivado/corrected/e2m0/postroute_sweep"]
set checkpoint [file normalize "build/vivado/gdn_e2m0_vivado/e2m0_post_impl.dcp"]
file mkdir $report_dir

if {![file isfile $checkpoint]} {
  error "Missing corrected-candidate routed checkpoint: $checkpoint"
}

open_checkpoint $checkpoint

foreach period_ns {4.000 5.000 5.500 5.550 5.600 6.000} {
  create_clock -period $period_ns -name ap_clk [get_ports ap_clk]
  set period_tag [string map {. p} $period_ns]
  report_timing_summary -delay_type min_max -report_unconstrained \
    -check_timing_verbose \
    -file [file join $report_dir timing_${period_tag}ns.rpt]
}

create_clock -period 5.600 -name ap_clk [get_ports ap_clk]
report_power -file [file join $report_dir power_5p600ns.rpt]
write_checkpoint -force [file join $report_dir e2m0_post_impl_5p600ns.dcp]
exit


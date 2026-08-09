set_param general.maxThreads 8
set report_dir [file normalize "reports/vivado/baselines/bf16/postroute_sweep"]
set checkpoint [file normalize "build/vivado/gdn_bf16_vivado/bf16_post_impl.dcp"]
file mkdir $report_dir

if {![file isfile $checkpoint]} {
  error "Missing BF16 routed checkpoint: $checkpoint"
}

open_checkpoint $checkpoint
set first_passing_period ""

foreach period_ns {4.000 6.000 7.000 7.125 7.250 7.500 8.000 9.000} {
  create_clock -period $period_ns -name ap_clk [get_ports ap_clk]
  set period_tag [string map {. p} $period_ns]
  report_timing_summary -delay_type min_max -report_unconstrained \
    -check_timing_verbose \
    -file [file join $report_dir timing_${period_tag}ns.rpt]
  set paths [get_timing_paths -delay_type max -max_paths 1]
  if {[llength $paths] == 1} {
    set slack [get_property SLACK [lindex $paths 0]]
    if {$slack >= 0.0 && $first_passing_period eq ""} {
      set first_passing_period $period_ns
    }
  }
}

if {$first_passing_period eq ""} {
  error "BF16 fixed-route sweep contains no passing setup point"
}

create_clock -period $first_passing_period -name ap_clk [get_ports ap_clk]
report_power -file [file join $report_dir power_first_passing.rpt]
set handle [open [file join $report_dir first_passing_period.txt] w]
puts $handle $first_passing_period
close $handle
exit

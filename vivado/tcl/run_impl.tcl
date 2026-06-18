set_param general.maxThreads 8
file mkdir reports/vivado

source vivado/tcl/create_project.tcl

synth_design -top gdn_top -part xcu55c-fsvh2892-2L-e -mode out_of_context
opt_design
place_design
phys_opt_design
route_design

report_utilization -file reports/vivado/impl_util.rpt
report_timing_summary -file reports/vivado/impl_timing.rpt
report_power -file reports/vivado/impl_power.rpt
write_checkpoint -force build/vivado/gdn_mxfp4_vivado/post_impl.dcp
exit

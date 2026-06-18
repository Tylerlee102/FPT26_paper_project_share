set_param general.maxThreads 8
file mkdir reports/vivado

source vivado/tcl/create_project.tcl

synth_design -top gdn_top -part xcu55c-fsvh2892-2L-e -mode out_of_context

report_utilization -file reports/vivado/synth_util.rpt
report_timing_summary -file reports/vivado/synth_timing.rpt
write_checkpoint -force build/vivado/gdn_mxfp4_vivado/post_synth.dcp
exit

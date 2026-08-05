proc insert_e2m0_ooc_clock_buffer {} {
  set clock_port [get_ports -quiet ap_clk]
  if {[llength $clock_port] != 1} {
    error "Expected one ap_clk port"
  }
  if {[llength [get_cells -quiet ooc_ap_clk_bufg]] != 0} {
    error "OOC clock buffer already exists"
  }

  set clock_load_nets [get_nets -quiet -of_objects $clock_port]
  if {[llength $clock_load_nets] != 1} {
    error "Expected ap_clk to drive one synthesized clock net"
  }
  set clock_load_net [lindex $clock_load_nets 0]

  create_cell -reference BUFGCE ooc_ap_clk_bufg
  create_cell -reference VCC ooc_ap_clk_vcc
  create_net ooc_ap_clk_input
  create_net ooc_ap_clk_enable

  disconnect_net -net $clock_load_net -objects $clock_port
  connect_net -hierarchical -net ooc_ap_clk_input \
    -objects [list $clock_port [get_pins ooc_ap_clk_bufg/I]]
  connect_net -hierarchical -net $clock_load_net \
    -objects [get_pins ooc_ap_clk_bufg/O]
  connect_net -hierarchical -net ooc_ap_clk_enable \
    -objects [list [get_pins ooc_ap_clk_vcc/P] [get_pins ooc_ap_clk_bufg/CE]]

  set_property LOC BUFGCE_X0Y0 [get_cells ooc_ap_clk_bufg]
}

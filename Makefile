PYTHON ?= python

.PHONY: setup golden calibrate qwen-capture qwen-status qwen-public-asset-audit hardware-availability vectors hls-csim hls-csynth decision-gate hls-cosim hls-e2m0-control-cosim hls-e2m0-trace-cosim hls-rs2-arithmetic-csim hls-rs2-csim hls-rs2-csynth hls-rs2-trace-csim hls-rs2-control-cosim hls-rs2-reset-trace-cosim hls-rs2-trace-cosim hls-rs2-direct-rtl hls-rs2-fast-direct-rtl hls-rs2-xsim-diagnostic hls-rs2-xsim-runtime-report hls-rs2-report vivado-synth vivado-impl vivado-e2m0-synth vivado-e2m0-impl vivado-e2m0-postroute-sweep vivado-e2m0-report vivado-rs2-synth vivado-rs2-impl vivado-rs2-postroute-sweep vivado-rs2-postroute-explore-opt vivado-rs2-report vivado-bf16-impl vivado-bf16-postroute-sweep vivado-mxfp8-impl vivado-mxfp8-postroute-sweep vivado-mxfp8-report phase5 sweep-plan vivado-sweep cosim-sweep benchmark benchmark-rs2-controlled paper-tables paper-figures corrected-paper-assets corrected-paper-audit corrected-paper-visual-audit corrected-paper-finalize corrected-paper-pdf working-draft working-draft-visual-audit table-previews graph-previews ieee-assets paper-previews phase6 paper-pack ci clean

setup:
	$(PYTHON) -m pip install -e ".[dev]"

golden:
	$(PYTHON) -m unittest discover -s tests

calibrate:
	$(PYTHON) -m golden.calibrate

qwen-capture:
	$(PYTHON) -m scripts.qwen_capture

qwen-status:
	$(PYTHON) -m scripts.qwen_status

qwen-public-asset-audit:
	$(PYTHON) -m scripts.qwen_public_asset_audit

hardware-availability:
	$(PYTHON) -m scripts.hardware_availability

vectors:
	$(PYTHON) -m golden.vectors --kind synthetic --count 16 --output-dir data/vectors

hls-csim:
	$(PYTHON) -m scripts.hls_flow csim
	$(PYTHON) -m scripts.csim_report

hls-csynth:
	$(PYTHON) -m scripts.hls_flow csynth
	$(PYTHON) -m scripts.hls_report

decision-gate:
	$(PYTHON) -m scripts.decision_gate

hls-cosim:
	$(PYTHON) -m scripts.hls_flow cosim
	$(PYTHON) -m scripts.cosim_report

hls-e2m0-control-cosim:
	$(PYTHON) -m scripts.hls_flow e2m0-control-cosim
	$(PYTHON) -m scripts.e2m0_control_cosim_report

hls-e2m0-trace-cosim:
	$(PYTHON) -m scripts.hls_flow e2m0-trace-cosim
	$(PYTHON) -m scripts.e2m0_trace_cosim_report

hls-rs2-arithmetic-csim:
	$(PYTHON) -m scripts.hls_flow rs2-arithmetic-csim

hls-rs2-csim:
	$(PYTHON) -m scripts.hls_flow rs2-csim

hls-rs2-csynth:
	$(PYTHON) -m scripts.hls_flow rs2-csynth

hls-rs2-trace-csim:
	$(PYTHON) -m scripts.hls_flow rs2-trace-csim

hls-rs2-control-cosim:
	$(PYTHON) -m scripts.hls_flow rs2-control-cosim

hls-rs2-reset-trace-cosim:
	$(PYTHON) -m scripts.generate_rs2_hls_trace --tokens 64 --initial-state zero --initial-command reset --output data/vectors/rs2_resident_trace64_reset.bin --manifest data/vectors/rs2_resident_trace64_reset_manifest.json
	$(PYTHON) -m scripts.hls_flow rs2-reset-trace-cosim

hls-rs2-trace-cosim:
	$(PYTHON) -m scripts.hls_flow rs2-trace-cosim

hls-rs2-direct-rtl:
	$(PYTHON) -m scripts.rs2_direct_rtl_flow

hls-rs2-fast-direct-rtl:
	$(PYTHON) -m scripts.rs2_fast_rtl_flow

hls-rs2-xsim-diagnostic:
	$(PYTHON) -m scripts.rs2_xsim_diagnostic

hls-rs2-xsim-runtime-report:
	$(PYTHON) -m scripts.rs2_xsim_runtime_report

hls-rs2-report:
	$(PYTHON) -m scripts.rs2_hls_report

vivado-synth:
	$(PYTHON) -m scripts.vivado_flow synth

vivado-impl:
	$(PYTHON) -m scripts.vivado_flow impl
	$(PYTHON) -m scripts.vivado_report

vivado-e2m0-synth:
	$(PYTHON) -m scripts.vivado_flow e2m0-synth

vivado-e2m0-impl:
	$(PYTHON) -m scripts.vivado_flow e2m0-impl

vivado-e2m0-postroute-sweep:
	$(PYTHON) -m scripts.vivado_flow e2m0-postroute-sweep
	$(PYTHON) -m scripts.e2m0_vivado_report

vivado-e2m0-report:
	$(PYTHON) -m scripts.e2m0_vivado_report

vivado-rs2-synth:
	$(PYTHON) -m scripts.vivado_flow rs2-synth

vivado-rs2-impl:
	$(PYTHON) -m scripts.vivado_flow rs2-impl

vivado-rs2-postroute-sweep:
	$(PYTHON) -m scripts.vivado_flow rs2-postroute-sweep
	$(PYTHON) -m scripts.rs2_vivado_report

vivado-rs2-postroute-explore-opt:
	$(PYTHON) -m scripts.vivado_flow rs2-postroute-explore-opt
	$(PYTHON) -m scripts.rs2_vivado_report

vivado-rs2-report:
	$(PYTHON) -m scripts.rs2_vivado_report

vivado-bf16-impl:
	$(PYTHON) -m scripts.vivado_flow bf16-impl

vivado-bf16-postroute-sweep:
	$(PYTHON) -m scripts.vivado_flow bf16-postroute-sweep

vivado-mxfp8-impl:
	$(PYTHON) -m scripts.vivado_flow mxfp8-impl
	$(PYTHON) -m scripts.vivado_flow mxfp8-postroute-sweep
	$(PYTHON) -m scripts.mxfp8_vivado_report

vivado-mxfp8-postroute-sweep:
	$(PYTHON) -m scripts.vivado_flow mxfp8-postroute-sweep
	$(PYTHON) -m scripts.mxfp8_vivado_report

vivado-mxfp8-report:
	$(PYTHON) -m scripts.mxfp8_vivado_report

phase5: golden calibrate vectors hls-csim hls-csynth hls-cosim vivado-synth vivado-impl

sweep-plan:
	$(PYTHON) -m scripts.sweep --plan

vivado-sweep:
	$(PYTHON) -m scripts.vivado_sweep --configs parallel_pk8_pv4_b32 parallel_pk32_pv16_b32 block_b16_pk16_pv8 block_b16_pk32_pv16

cosim-sweep:
	$(PYTHON) -m scripts.cosim_sweep

benchmark:
	$(PYTHON) -m scripts.benchmark

benchmark-rs2-controlled:
	$(PYTHON) -m scripts.long_sequence_stability --tokens 8192 --seed 0xFB72 --split development --trace-family high_retention --token-csv reports/benchmark/corrected/rs2_controlled/high_retention_random_baselines_tokens.csv --checkpoint-csv reports/benchmark/corrected/rs2_controlled/high_retention_random_baselines_checkpoints.csv --report reports/benchmark/corrected/rs2_controlled/high_retention_random_baselines.md --manifest reports/benchmark/corrected/rs2_controlled/high_retention_random_baselines_manifest.json
	$(PYTHON) -m scripts.aggregate_rs2_encoded_candidate --require-extended
	$(PYTHON) -m scripts.build_rs2_controlled_comparison
	$(PYTHON) -m scripts.plot_long_sequence_stability --input reports/benchmark/corrected/rs2_controlled/controlled_long_trace_tokens.csv --evidence-manifest reports/benchmark/corrected/rs2_controlled/controlled_long_trace_manifest.json --encoded-input reports/benchmark/corrected/rs2_controlled/no_separate_encoded_input.csv --encoded-evidence-manifest reports/benchmark/corrected/rs2_controlled/no_separate_encoded_manifest.json
	$(PYTHON) -m scripts.corrected_long_trace_panel

paper-tables:
	$(PYTHON) -m scripts.paper_tables

paper-figures:
	$(PYTHON) -m scripts.paper_figures

corrected-paper-assets:
	$(PYTHON) -m scripts.rs2_interface_accounting
	$(PYTHON) -m scripts.corrected_datapath_figure
	$(PYTHON) -m scripts.corrected_long_trace_panel
	$(PYTHON) -m scripts.rs2_paper_assets

corrected-paper-audit: corrected-paper-assets
	$(PYTHON) -m scripts.build_corrected_paper

corrected-paper-visual-audit:
	$(PYTHON) -m scripts.record_paper_visual_audit

corrected-paper-finalize:
	$(PYTHON) -m scripts.finalize_corrected_paper

corrected-paper-pdf: corrected-paper-finalize

working-draft:
	$(PYTHON) -m scripts.build_working_draft

working-draft-visual-audit:
	$(PYTHON) -m scripts.record_working_draft_visual_audit

table-previews:
	$(PYTHON) -m scripts.paper_table_previews

graph-previews:
	$(PYTHON) -m scripts.paper_graph_previews

ieee-assets:
	$(PYTHON) -m scripts.ieee_assets

paper-previews: table-previews graph-previews ieee-assets

phase6: sweep-plan benchmark paper-tables paper-figures

paper-pack:
	$(PYTHON) -m scripts.paper_pack

ci:
	$(PYTHON) -m pytest
	$(PYTHON) -m scripts.final_completion_gate

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in map(pathlib.Path, ['build', '.pytest_cache', 'reports/test_tmp', 'tmp/pdfs'])]"

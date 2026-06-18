PYTHON ?= python

.PHONY: setup golden calibrate qwen-capture qwen-status vectors hls-csim hls-csynth decision-gate hls-cosim vivado-synth vivado-impl phase5 sweep-plan vivado-sweep cosim-sweep benchmark paper-tables paper-figures table-previews graph-previews ieee-assets paper-previews phase6 paper-pack ci clean

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

vivado-synth:
	$(PYTHON) -m scripts.vivado_flow synth

vivado-impl:
	$(PYTHON) -m scripts.vivado_flow impl
	$(PYTHON) -m scripts.vivado_report

phase5: golden calibrate vectors hls-csim hls-csynth hls-cosim vivado-synth vivado-impl

sweep-plan:
	$(PYTHON) -m scripts.sweep --plan

vivado-sweep:
	$(PYTHON) -m scripts.vivado_sweep --configs parallel_pk8_pv4_b32 parallel_pk32_pv16_b32 block_b16_pk16_pv8 block_b16_pk32_pv16

cosim-sweep:
	$(PYTHON) -m scripts.cosim_sweep

benchmark:
	$(PYTHON) -m scripts.benchmark

paper-tables:
	$(PYTHON) -m scripts.paper_tables

paper-figures:
	$(PYTHON) -m scripts.paper_figures

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

ci: phase5 phase6

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in map(pathlib.Path, ['build', '.pytest_cache', 'reports/cosim', 'reports/csynth'])]"

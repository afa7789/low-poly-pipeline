# lowpoly-pipeline: low-poly unit/building model generation + animation tool for Castle Fight.
# CF_GAME = game checkout (read: data tables; write: install step only). CF_PIPELINE_OUT = output folder (default ./output).
PY ?= python3.14
CF_GAME ?=

.PHONY: build run clean lint test link install

link:
	CF_GAME=$(CF_GAME) scripts/link_game.sh
	scripts/link_output.sh

build: link

run:
	@echo "stages: tools/blender/spec_pipeline.py, roster_batch.py, hand_review.sh <id> <family>; install: make install CF_GAME=<game>"

test:
	$(PY) -m unittest discover -s tests/tools -p "test_*.py"
	$(PY) -m unittest discover -s tests/tools/blender

lint:
	uvx ruff check --select C901 --config 'lint.mccabe.max-complexity = 10' --extend-exclude tools/blender/vendor tools tests

# copy the hand GLBs (+ palettes) and output GLBs the game still points at into $(CF_GAME)/assets/units/<id>/
install:
	$(PY) tools/hand_models_install.py $(if $(CF_GAME),--game $(CF_GAME)) --write

clean:
	find tools tests -name __pycache__ -type d -prune -exec rm -rf {} +

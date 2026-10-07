PY ?= .venv/bin/python

.PHONY: setup test data feasibility forecast sim replay reproduce api web lock

setup:
	uv venv --python 3.12 .venv
	uv pip install --python $(PY) -e ".[dev,api,forecast,sim]" matplotlib

test:
	$(PY) -m pytest

data:
	$(PY) -m transact3.cli build-data --config configs/phase1_synthetic.yaml

feasibility:
	$(PY) -m transact3.cli feasibility --out docs/data_feasibility_report.md

forecast:
	$(PY) -m transact3.cli forecast --config configs/forecast.yaml

# Paper 1: simulator experiments (about 25 minutes, mostly PPO training)
sim:
	$(PY) -m transact3.cli run-sim --config configs/sim.yaml

# Paper 2 replay and the Paper 1 empirical-stablecoin robustness rerun
replay:
	$(PY) -m transact3.cli run-replay --config configs/replay.yaml --sim-config configs/sim.yaml

# Regenerates every dataset, forecast, table and figure from configs and seeds.
reproduce: data forecast sim replay feasibility

api:
	$(PY) -m uvicorn transact3.api.main:app --port 8000

web:
	cd web && npm run dev

lock:
	uv pip freeze --python $(PY) | grep -v "^-e" > requirements.lock

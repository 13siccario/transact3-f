# Research pipeline + API. Build: docker build -t transact3 .   Run: docker run --rm -p 8000:8000 transact3
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 make && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps -e .
COPY configs ./configs
COPY Makefile ./
ENV PY=python
# Build the datasets, forecasts and tables once at image build so the API has something to serve.
RUN make data forecast && python -m transact3.cli run-sim --config configs/sim.yaml || true
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "transact3.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

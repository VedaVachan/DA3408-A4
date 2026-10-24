# AIOps Assignment 4 — Application Monitoring

I built a CPU-only Streamlit app that generates image captions using Salesforce BLIP. It supports single-image and bulk ZIP uploads, with monitoring through Prometheus, node_exporter, Grafana and Alertmanager.

## Project Structure

| Files / folder | Purpose |
|---|---|
| `app.py`, `captioner.py`, `uploads.py` | Interface, caption generation and upload validation |
| `metrics.py` | Prometheus metrics |
| `download_model.py` | Download and cache the model |
| `compose*.yml`, `prometheus.yml` | Monitoring services and scrape configuration |
| `alerts.yml`, `alertmanager.yml`, `alert_receiver.py` | Alert rules and notifications |
| `grafana/` | Dashboard JSON and data-source configuration |
| `tests/` | Automated tests |
| `docs/` | Design, calculations and AI attribution |
| `evidence/` | Screenshots and caption results |

## Setup

Requires Ubuntu/Linux, Python 3.12, Docker and Docker Compose. Run all commands from the repository folder.

```bash
/usr/bin/python3 -m venv .venv
source .venv/bin/activate

python -m pip --isolated install --no-cache-dir \
  --index-url https://pypi.org/simple -r requirements.txt

python -m pip --isolated install --no-cache-dir --no-deps \
  -r requirements-cpu.txt

python -m pip check
python download_model.py
```

Internet is needed for initial downloads. Caption generation runs locally on CPU.

## Run

**Terminal 1 — Monitoring:**

```bash
docker compose -f compose.yml -f compose.grafana.yml \
  -f compose.alerting.yml up -d
```

**Terminal 2 — Application:**

```bash
source .venv/bin/activate

HF_HUB_OFFLINE=1 python -m streamlit run app.py \
  --server.address 127.0.0.1 --server.port 8501
```

**Terminal 3 — Alert receiver:**

```bash
source .venv/bin/activate
python alert_receiver.py
```

## Open and Use

Open these addresses inside Ubuntu:

| Service | URL |
|---|---|
| Application | http://127.0.0.1:8501 |
| Prometheus targets | http://127.0.0.1:9090/targets |
| Grafana | http://127.0.0.1:3000 |
| Application metrics | http://127.0.0.1:8001/metrics |
| Alertmanager | http://127.0.0.1:9093 |

Select **Single image** or **Bulk ZIP**, upload your file and click **Generate captions**. Results can be downloaded as CSV. ZIP uploads support up to **30 images**.

Opening the app page starts the metrics endpoint. The model loads on the first caption request.

For a fresh Grafana installation, log in with `admin/admin` and change the password. Import `grafana/dashboard.json`, select **Last 15 minutes** and set refresh to **5s**.

## Verification

```bash
python -m pytest tests -q
```

Verified on my VM:

- **24 automated tests passed.**
- One single image and **27 bulk images** processed successfully.
- All four Prometheus targets were UP.
- Bulk throughput and CPU activity appeared in Grafana.
- Downtime firing and recovery notifications reached the receiver.

Captioner unit tests use mocks; real inference was tested separately.

The app uses Counter, Gauge, Histogram and Summary metrics. Client labels use 16 session-derived buckets, which do not identify unique users. Calculations and AI attribution are documented in `docs/`.

## Stop

Press **Ctrl+C** in the application and receiver terminals, then run:

```bash
docker compose -f compose.yml -f compose.grafana.yml \
  -f compose.alerting.yml down
```
